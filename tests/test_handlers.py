from fastapi_version_handler.handlers import HeaderBasedVersionHandler


# Test default instance
def test_default_instance():
    app = HeaderBasedVersionHandler()
    assert app.show_dashboard is True
    assert app.router.version_header_name == "X-API-VERSION".lower()


# Test instance with disabled dashboard
def test_instance_with_disabled_dashboard():
    app = HeaderBasedVersionHandler(show_dashboard=False)
    assert app.show_dashboard is False


# Test instance with custom header name
def test_instance_with_custom_header_name():
    app = HeaderBasedVersionHandler(version_header_name="CUSTOM-X-API-Version")
    assert app.router.version_header_name == "CUSTOM-X-API-Version".lower()


# Test instance with other FastAPI arguments
def test_instance_with_other_fastapi_arguments():
    app = HeaderBasedVersionHandler(
        title="My FastAPI App",
        description="My FastAPI App Description",
        # @TODO: Add more fields
    )
    assert app.title == "My FastAPI App"
    assert app.description == "My FastAPI App Description"


# @TODO: Add more tests
