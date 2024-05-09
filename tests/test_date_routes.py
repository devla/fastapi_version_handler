from fastapi import APIRouter
from fastapi.testclient import TestClient

from fastapi_version_handler.handlers import HeaderBasedVersionHandler

app = HeaderBasedVersionHandler()
router = APIRouter()
client = TestClient(app)

dates = [
    "2024-01-05",
    "2024-02-10",
    "2024-03-16",
    "2024-04-25",
]

invalid_dates = [
    "2024-01-055",
    "2024-02",
    "20244-03-16",
    "2024-4-25",
]


@router.get("/heroes")
async def get_heroes():
    return {"message": "Hello Heroes"}


for date in dates:
    app.include_router(
        router,
        version=date,
    )


# Test versioned openapi.json
def test_openapi_date_routes():
    for date in dates:
        response = client.get(f"/openapi.json?version={date}")
        assert response.status_code == 200
        assert "openapi" in response.text


# Test invalid version
def test_openapi_date_routes_with_invalid_date():
    for date in invalid_dates:
        response = client.get(f"/openapi.json?version={date}")
        assert response.status_code == 404
        assert response.json() == {
            "detail": f"OpenApi file of with version `{date}` not found",
        }


# @TODO: Add more tests
