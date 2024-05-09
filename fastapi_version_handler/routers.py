from collections import OrderedDict
from contextvars import ContextVar
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Union

from fastapi.routing import APIRouter
from starlette.routing import BaseRoute
from starlette.types import Receive, Scope, Send

from fastapi_version_handler.utils import (
    find_closest_date,
    find_closest_version,
    is_valid_date,
    is_valid_version,
)


class VersionAwareAPIRouter(APIRouter):
    """
    Custom router for versioned APIs.

    Attributes:
        requested_version (ContextVar[str] | None): Context variable for storing the requested API version.
        returned_version (ContextVar[str] | None): Context variable for storing the returned API version.
        version_header_name (str): Name of the API version header.

    Args:
        requested_version (ContextVar[str] | None): Context variable for storing the requested API version.
        returned_version (ContextVar[str] | None): Context variable for storing the returned API version.
        version_header_name (str): Name of the API version header. Defaults to "X-API-VERSION".
        **kwargs: Additional keyword arguments to be passed to the parent class constructor.

    Example:
        router = VersionAwareAPIRouter("X-API-Version")
    """

    def __init__(
        self,
        requested_version: ContextVar[str] | None = None,
        returned_version: ContextVar[str] | None = None,
        version_header_name: str = "X-API-VERSION",
        **kwargs: Any,
    ):
        """
        Initialize the VersionAwareAPIRouter.

        Args:
            requested_version (ContextVar[str] | None): Context variable for storing the requested API version.
            returned_version (ContextVar[str] | None): Context variable for storing the returned API version.
            version_header_name (str): Name of the API version header. Defaults to "X-API-VERSION".
            **kwargs: Additional keyword arguments to be passed to the parent class constructor.
        """
        super().__init__(**kwargs)
        self.requested_version: ContextVar[str] = requested_version
        self.returned_version: ContextVar[str] = returned_version
        self.versioned_routers: Dict[str, List[BaseRoute]] = {}
        self.unversioned_routers: List[BaseRoute] = []
        self.version_header_name: str = version_header_name.lower()

    def __hash__(self):
        return hash(self.group_and_sort_routes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle incoming requests.

        Args:
            scope (Scope): The request scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.
        """
        header_version = self._get_header_version(scope)
        routes = self._get_routes_for_version(header_version)
        self.routes = routes
        await self.app(scope=scope, receive=receive, send=send)

    def _get_header_version(self, scope: Scope) -> str:
        """
        Get the API version from the request headers.

        Args:
            scope (Scope): The request scope.

        Returns:
            str: The API version extracted from the request headers.
        """
        header_version_bytes = dict(scope.get("headers", [])).get(
            self.version_header_name.encode(),
            b"",
        )
        return header_version_bytes.decode()

    def _get_routes_for_version(self, header_version: str) -> List[BaseRoute]:
        """
        Get the routes corresponding to the given API version.

        Args:
            header_version (str): The API version extracted from the request headers.

        Returns:
            List[BaseRoute]: The routes corresponding to the given API version.
        """
        if not header_version:
            return self.unversioned_routers

        return self.versioned_routers.get(
            header_version,
            self._pick_version(header_version),
        )

    def _pick_version(self, header_version: str) -> List[BaseRoute]:
        """
        Pick the appropriate version of routes based on the header version.

        Args:
            header_version (str): The API version extracted from the request headers.

        Returns:
            List[BaseRoute]: The routes corresponding to the selected API version.
        """
        # @TODO:
        # To address the sorting and handling of mixed versions, consider aligning it with a revised
        # versioning strategy. One approach could involve redefining the `header_version` format to
        # accommodate both the version and the date. For instance, adopting a format like
        # "v1.0.0|2024-04-29" would allow capturing both the version and the date information within
        # the header, enabling more effective sorting and routing logic. Combining both semantic and
        # date versioning can result in a final versioning format like '1.0.0 (2024-04-29)'.
        is_valid_date_version = is_valid_date(header_version)

        closest_version = (
            find_closest_date(
                header_version,
                list(self.group_and_sort_routes().get("sorted_date_routes")),
            )
            if is_valid_date_version
            else find_closest_version(
                header_version,
                list(self.group_and_sort_routes().get("sorted_version_routes")),
            )
        )

        # Sets the requested and returned versions in the context variables for debugging purposes.
        if self.requested_version:
            self.requested_version.set(header_version)
        if self.returned_version:
            self.returned_version.set(closest_version)

        return self.versioned_routers[closest_version]

    @lru_cache(maxsize=None)  # noqa: B019
    def group_and_sort_routes(self) -> Dict[str, Dict[str, List[BaseRoute]]]:
        """
        Group and sort versioned routes by date or version.

        Returns:
            Dict[str, Dict[str, List[BaseRoute]]]: A dictionary containing sorted versioned routes
            grouped by date or version.
        """
        sorted_date_routes: Dict[str, List[BaseRoute]] = {}
        sorted_version_routes: Dict[str, List[BaseRoute]] = {}

        for key, value in self.versioned_routers.items():
            if is_valid_date(key):
                sorted_date_routes[key] = value
            elif is_valid_version(key):
                sorted_version_routes[key] = value
            else:
                raise ValueError(
                    f"Key {key} is neither a valid date nor a valid version.",
                )

        sorted_date_routes = OrderedDict(sorted(sorted_date_routes.items()))
        sorted_version_routes = OrderedDict(sorted(sorted_version_routes.items()))

        return {
            "sorted_date_routes": sorted_date_routes,
            "sorted_version_routes": sorted_version_routes,
        }

    @lru_cache(maxsize=None)  # noqa: B019
    def _get_min_version_or_date(self, is_date: bool) -> Union[str, datetime]:
        """
        Get the minimum version or date from the sorted routes.

        Args:
            is_date (bool): Indicates whether to retrieve the minimum date (True) or version (False).

        Returns:
            Union[str, datetime]: The minimum version or date.
        """
        sorted_routes = self.group_and_sort_routes().get(
            "sorted_date_routes" if is_date else "sorted_version_routes",
        )
        return min(
            sorted_routes.keys(),
            default="" if is_date else datetime.max.isoformat(),
        )
