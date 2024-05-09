import inspect
from typing import Annotated, Any

from fastapi import Header


def _version_dependency(version_header_name: str, version: str):
    """
    Create a dependency function for extracting the API version header from the request.

    Args:
        version_header_name (str): The name of the API version header.
        version (str): The default version value to use if the header is not present in the request.

    Returns:
        Dependency function: A FastAPI dependency function that extracts the API version header from the request.

    Example:
        version_header = _version_dependency("X-API-Version", "1.0.0")

        @app.get("/")
        async def get_data(version: str = Depends(version_header)):
            return {"version": version}
    """

    def version_dependency(**kwargs: Any):
        """
        Extract the API version header from the request.

        Returns:
            str: The value of the API version header.
        """
        return next(iter(kwargs.values()))

    # Annotate the version parameter with Header to specify it's expected as a header
    version_dependency.__signature__ = inspect.Signature(
        parameters=[
            inspect.Parameter(
                version_header_name.replace("-", "_"),
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Annotated[str, Header(examples=[version])],
                default=version,
            ),
        ],
    )

    return version_dependency
