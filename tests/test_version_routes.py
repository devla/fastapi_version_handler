from fastapi import APIRouter
from fastapi.testclient import TestClient

from fastapi_version_handler.handlers import HeaderBasedVersionHandler
from fastapi_version_handler.utils import normalize_version

app = HeaderBasedVersionHandler()
router = APIRouter()
client = TestClient(app)

versions = [
    "v1.0.0",
    "v1.1.0",
    "v1.3.2",
    "v1.4.5",
    "v2.0.4",
    "2.2.5",  # Without 'v' prefix
    "2.3.0",
    "3.0.0",
]

invalid_versions = [
    "v2.",
    "v1.3.",
    "v1.4.5.1",
    "v2.0.4.1",
    "2.2.5.1",
    "2.3.0.1",
]


@router.get("/heroes")
async def get_heroes():
    return {"message": "Hello Heroes"}


for version in versions:
    app.include_router(
        router,
        version=version,
    )


# Test versioned openapi.json
def test_openapi_versioned_routes():
    for version in versions:
        response = client.get(f"/openapi.json?version={normalize_version(version)}")
        assert response.status_code == 200
        assert "openapi" in response.text


# Test invalid version
def test_openapi_versioned_routes_with_invalid_version():
    for version in invalid_versions:
        response = client.get(f"/openapi.json?version={version}")
        assert response.status_code == 404
        assert response.json() == {
            "detail": f"OpenApi file of with version `{version}` not found",
        }
