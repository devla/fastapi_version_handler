from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.routing import APIRouter
from fastapi.templating import Jinja2Templates

from fastapi_version_handler.dependencies import _version_dependency
from fastapi_version_handler.middleware import VersionValidationMiddleware
from fastapi_version_handler.routers import VersionAwareAPIRouter
from fastapi_version_handler.utils import (
    is_valid_version,
    normalize_version,
    validate_version,
)

CURR_DIR = Path(__file__).resolve()


class BaseVersionHandler(FastAPI):
    """
    Base class for handling versioned APIs with FastAPI.

    Attributes:
        OPENAPI_URL (str): The URL path for the OpenAPI JSON file.
        DOCS_URL (str): The URL path for the Swagger UI documentation.
        REDOC_URL (str): The URL path for the ReDoc documentation.
        TEMPLATES_DIRECTORY (Path): The directory path for template files.
        requested_version (ContextVar[str] | None): Context variable for storing the requested API version.
        returned_version (ContextVar[str] | None): Context variable for storing the returned API version.

    Args:
        requested_version (ContextVar[str] | None): Context variable for storing the requested API version.
        returned_version (ContextVar[str] | None): Context variable for storing the returned API version.
        version_header_name (str): The name of the API version header.
        show_dashboard (bool): Whether to show the version dashboard.
        group_versions (bool): Whether to show the grouped dashboard.
        **kwargs: Additional arguments to pass to FastAPI.

    Example:
        handler = BaseVersionHandler("X-API-Version")
        handler.include_router(router)

    """

    OPENAPI_URL = "/openapi.json"
    DOCS_URL = "/docs"
    REDOC_URL = "/redoc"
    TEMPLATES_DIRECTORY = CURR_DIR.parent / "templates"

    templates = Jinja2Templates(directory=TEMPLATES_DIRECTORY)

    def __init__(
        self,
        requested_version: ContextVar[str] | None = None,
        returned_version: ContextVar[str] | None = None,
        version_header_name: str = "X-API-VERSION",
        show_dashboard: bool = True,
        group_versions: bool = False,
        **kwargs: Any,
    ):
        """
        Initialize the BaseVersionHandler.

        Args:
            requested_version (ContextVar[str] | None): Context variable for storing the requested API version.
            returned_version (ContextVar[str] | None): Context variable for storing the returned API version.
            version_header_name (str): The name of the API version header.
            show_dashboard (bool): Whether to show the version dashboard.
            group_versions (bool): Whether to show the grouped dashboard.
            **kwargs: Additional arguments to pass to FastAPI.
        """
        super().__init__(**kwargs)

        self.num = 1

        self.router: VersionAwareAPIRouter = VersionAwareAPIRouter(
            requested_version=requested_version,
            returned_version=returned_version,
            version_header_name=version_header_name,
        )

        self.show_dashboard = show_dashboard
        self.group_versions = group_versions
        self.swaggers: Dict[str, Any] = {}

        # Add default unversioned routes to the swagger
        # openapi, docs, and redoc.
        router = APIRouter()
        router.add_route(
            path=self.OPENAPI_URL,
            endpoint=self.openapi_jsons,
            include_in_schema=False,
        )
        router.add_route(
            path=self.DOCS_URL,
            endpoint=self.swagger_dashboard,
            include_in_schema=False,
        )
        router.add_route(
            path=self.REDOC_URL,
            endpoint=self.redoc_dashboard,
            include_in_schema=False,
        )

        self.include_router(router)

    async def openapi_jsons(self, req: Request) -> JSONResponse:
        """
        Returns the OpenAPI JSON file of a specific version.

        Args:
            req (Request): The incoming request.

        Returns:
            JSONResponse: The OpenAPI JSON response.
        """

        version = req.query_params.get("version")
        openapi_of_a_version = self.swaggers.get(version)
        if not openapi_of_a_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OpenApi file of with version `{version}` not found",
            )

        return JSONResponse(openapi_of_a_version)

    async def swagger_dashboard(self, req: Request) -> Response:
        """
        Returns the Swagger UI dashboard.

        Args:
            req (Request): The incoming request.

        Returns:
            Response: The Swagger UI response.
        """

        version = self._get_version(req)

        if version:
            return get_swagger_ui_html(
                openapi_url=f"{self.openapi_url}?version={version}",
                title="Swagger UI",
            )

        return self._get_dashboard_template(req, self.docs_url)

    async def redoc_dashboard(self, req: Request) -> HTMLResponse:
        """
        Returns the ReDoc dashboard.

        Args:
            req (Request): The incoming request.

        Returns:
            HTMLResponse: The ReDoc response.
        """

        version = self._get_version(req)

        if version:
            openapi_url = req.scope.get("root_path", "").rstrip("/") + f"{self.openapi_url}?version={version}"
            return get_redoc_html(
                openapi_url=openapi_url,
                title=f"{self.title} - ReDoc",
            )

        return self._get_dashboard_template(req, self.redoc_url)

    def _get_version(self, req: Request) -> str:
        """
        Returns the version from the query params, and handles the case where the dashboard is not shown.

        Args:
            req (Request): The incoming request.

        Returns:
            str: The version string.
        """

        version = req.query_params.get("version")

        if not version and not self.show_dashboard:
            first_key = next(iter(self.router.versioned_routers))
            return self.router._get_min_version_or_date(
                is_date=not is_valid_version(first_key),
            )

        return version

    def enrich_swagger(self) -> None:
        """
        Enriches the swagger with the versioned and unversioned routes.

        Returns:
            None
        """

        kwargs = {
            "title": self.title,
            "openapi_version": self.openapi_version,
            "description": self.description,
            "terms_of_service": self.terms_of_service,
            "contact": self.contact,
            "license_info": self.license_info,
            "tags": self.openapi_tags,
            "servers": self.servers,
        }

        # Add the unversioned routes to the swagger
        unversioned_routers_openapi = get_openapi(
            routes=self.router.unversioned_routers,
            version="unversioned",
            **kwargs,
        )
        if unversioned_routers_openapi["paths"]:
            self.swaggers["unversioned"] = unversioned_routers_openapi

        # Add the versioned routes to the swaggers
        for version, routes in self.router.versioned_routers.items():
            if version not in self.swaggers:
                openapi = get_openapi(
                    routes=routes,
                    version=version,
                    **kwargs,
                )
                self.swaggers[version] = openapi


class HeaderBasedVersionHandler(BaseVersionHandler):
    """
    Handler for versioned APIs based on header information.
    Inherits from BaseVersionHandler.

    Args:
        **kwargs: Additional arguments for the BaseVersionHandler constructor.

    Example:
        handler = HeaderBasedVersionHandler("X-API-Version")
        handler.include_router(router)

    """

    def __init__(self, **kwargs: Any):
        """
        Initialize the HeaderBasedVersionHandler.

        Args:
            **kwargs: Additional arguments for the BaseVersionHandler constructor.
        """
        super().__init__(**kwargs)

        self.add_middleware(VersionValidationMiddleware, _app=self)

    def include_router(
        self,
        router: APIRouter,
        *,
        version: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ) -> None:
        """
        Overrides the original include_router method.

        Args:
            router (APIRouter): The router to include.
            version (str, optional): The version header value. Defaults to None.
            **kwargs: Additional arguments for the include_router method.

        Returns:
            None
        """

        if version is not None:
            validate_version(version)

            kwargs.setdefault("dependencies", []).append(
                Depends(
                    _version_dependency(self.router.version_header_name, version),
                ),
            )

            super().include_router(router, **kwargs)

            added_routes: list = []
            added_routes.extend(self.routes[len(self.routes) - len(router.routes) :])

            for route in added_routes:
                self.router.versioned_routers.setdefault(
                    normalize_version(version),
                    [],
                ).append(route)
        else:
            super().include_router(router, include_in_schema=False, **kwargs)
            self.router.unversioned_routers.extend(router.routes)

        self.enrich_swagger()

    def _get_dashboard_template(self, req: Request, url: str = ""):
        """
        Returns the dashboard template.

        Args:
            req (Request): The incoming request.
            url (str, optional): The URL path. Defaults to "".

        Returns:
            Response: The dashboard template response.
        """

        base_url = str(req.base_url).rstrip("/")
        sorted_routes = self.router.group_and_sort_routes()

        # Group versions by major version
        grouped_versions = {} if self.group_versions else {"versioned": []}
        for version in sorted_routes.get("sorted_version_routes"):
            if self.group_versions:
                major_version = version.split(".")[0]
                if major_version not in grouped_versions:
                    grouped_versions[major_version] = []
                grouped_versions[major_version].append(
                    (version, f"{base_url}{url}?version={version}"),
                )
            else:
                grouped_versions["versioned"].append(
                    (version, f"{base_url}{url}?version={version}"),
                )

        # Group dates versions by year
        for version in sorted_routes.get("sorted_date_routes"):
            if self.group_versions:
                year = datetime.strptime(version, "%Y-%m-%d").year
                if year not in grouped_versions:
                    grouped_versions[year] = []
                grouped_versions[year].append(
                    (version, f"{base_url}{url}?version={version}"),
                )
            else:
                grouped_versions["versioned"].append(
                    (version, f"{base_url}{url}?version={version}"),
                )

        # Unsorted routes missing.
        grouped_versions["unversioned"] = []
        grouped_versions["unversioned"].append(
            ("unversioned", f"{base_url}{url}?version=unversioned"),
        )

        # Pass the grouped versions to the template
        return self.templates.TemplateResponse(
            "dashboard.html",
            {
                "request": req,
                "grouped_versions": grouped_versions,
            },
        )
