from typing import TYPE_CHECKING, Dict

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from fastapi_version_handler.utils import validate_version

if TYPE_CHECKING:
    from fastapi_version_handler.handlers import HeaderBasedVersionHandler
else:
    HeaderBasedVersionHandler = "HeaderBasedVersionHandler"  # Forward reference


class VersionValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating API version headers.

    This middleware validates the API version header for incoming requests,
    ensuring that the version format is correct. It can be applied to specific
    routes by excluding those routes from validation using the `include_in_schema=False`
    attribute.

    Args:
        app (ASGIApp): The ASGI application.
        _app (HeaderBasedVersionHandler): The instance of HeaderBasedVersionHandler.

    Attributes:
        _app (HeaderBasedVersionHandler): The instance of HeaderBasedVersionHandler.
        skipped_routes (Dict[str, bool]): A dictionary mapping route paths to
            boolean values indicating whether version validation should be skipped.

    """

    def __init__(self, app: ASGIApp, *, _app: HeaderBasedVersionHandler) -> None:
        super().__init__(app)
        self._app: HeaderBasedVersionHandler = _app
        self.skipped_routes: Dict[str, bool] = self._build_skipped_routes()

    async def dispatch(self, request: Request, call_next: callable) -> Response:
        """
        Dispatch method for processing incoming requests.

        This method validates the API version header for incoming requests,
        ensuring that the version format is correct. It skips validation for
        routes marked with `include_in_schema=False`.

        Args:
            request (Request): The incoming request.
            call_next (callable): The function to call to continue request processing.

        Returns:
            Response: The response generated by the downstream middleware or application.

        """
        try:
            if self._should_skip_validation(request.url.path):
                return await call_next(request)

            version: str = request.headers.get(self._app.router.version_header_name)
            validate_version(version)

            return await call_next(request)

        except HTTPException as e:
            return JSONResponse({"detail": e.detail}, status_code=e.status_code)

    def _build_skipped_routes(self) -> Dict[str, bool]:
        """
        Build a dictionary of skipped routes.

        This method builds a dictionary of skipped routes, where the keys
        are route paths and the values indicate whether version validation
        should be skipped for that route.

        Returns:
            Dict[str, bool]: A dictionary mapping route paths to boolean values.

        """
        return {route.path: not getattr(route, "include_in_schema", True) for route in self._app.routes}

    def _should_skip_validation(self, path: str) -> bool:
        """
        Check if validation should be skipped for a route.

        This method checks if version validation should be skipped for the
        specified route path.

        Args:
            path (str): The route path.

        Returns:
            bool: True if validation should be skipped, otherwise False.

        """
        return self.skipped_routes.get(path.rstrip("/"), False)
