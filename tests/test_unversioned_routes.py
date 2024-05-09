from fastapi import APIRouter
from fastapi.testclient import TestClient

from fastapi_version_handler.handlers import HeaderBasedVersionHandler

app = HeaderBasedVersionHandler()
router = APIRouter()
client = TestClient(app)


@router.get("/heroes")
async def get_heroes():
    return {"message": "Hello Heroes"}


app.include_router(router)


# Test unversioned openapi.json
def test_openapi_unversioned_routes():
    response = client.get("/openapi.json?version=unversioned")
    assert response.status_code == 200
    assert "openapi" in response.text


# Test invalid unversioned openapi.json
def test_openapi_unversioned_routes_with_invalid_version():
    response = client.get("/openapi.json?version=version")
    assert response.status_code == 404
    assert response.json() == {
        "detail": "OpenApi file of with version `version` not found",
    }


# @TODO: Add more tests
