import pytest
from fastapi import HTTPException

from fastapi_version_handler.utils import (
    find_closest_date,
    find_closest_version,
    is_valid_date,
    is_valid_version,
    normalize_version,
    validate_version,
)


# Test validate_version
def test_validate_version_valid():
    assert validate_version("v1.0.0") is None
    assert validate_version("1.0.0") is None
    assert validate_version("2024-04-29") is None


def test_validate_version_invalid_format():
    with pytest.raises(HTTPException):
        validate_version("invalid")

    with pytest.raises(HTTPException):
        validate_version("v1.0.0.0")

    with pytest.raises(HTTPException):
        validate_version("v1.0")

    with pytest.raises(HTTPException):
        validate_version("1.0.0.0")

    with pytest.raises(HTTPException):
        validate_version("1.0")

    with pytest.raises(HTTPException):
        validate_version("2024-04-29T12:00:00")

    with pytest.raises(HTTPException):
        validate_version("2024-04")

    with pytest.raises(HTTPException):
        validate_version("24-04-29")


def test_validate_version_empty():
    with pytest.raises(HTTPException):
        validate_version("")


# Test is_valid_version
def test_is_valid_version_valid():
    assert is_valid_version("v1.0.0") is True
    assert is_valid_version("v1.1.0") is True
    assert is_valid_version("v1.1.1") is True
    assert is_valid_version("v0.0.1") is True
    assert is_valid_version("v0.1.1") is True
    assert is_valid_version("v0.1.0") is True

    assert is_valid_version("1.0.0") is True
    assert is_valid_version("1.1.0") is True
    assert is_valid_version("1.1.1") is True
    assert is_valid_version("0.0.1") is True
    assert is_valid_version("0.1.1") is True
    assert is_valid_version("0.1.0") is True


def test_is_valid_version_invalid_format():
    assert is_valid_version("0.0.0") is False
    assert is_valid_version("v0.0.0") is False
    assert is_valid_version("g1.0.0") is False
    assert is_valid_version("invalid") is False
    assert is_valid_version("") is False


# Test is_valid_date
def test_is_valid_date_valid():
    assert is_valid_date("2024-04-29") is True


def test_is_valid_date_invalid_format():
    assert is_valid_date("2024-04-29T12:00:00") is False
    assert is_valid_date("2024-4-29") is False
    assert is_valid_date("2024-4-3") is False
    assert is_valid_date("2024-04") is False
    assert is_valid_date("2024-4") is False
    assert is_valid_date("24-04-29") is False
    assert is_valid_date("invalid") is False
    assert is_valid_date("") is False


# Test normalize_version
def test_normalize_version():
    assert normalize_version("1.0.0") == "v1.0.0"
    assert normalize_version("v1.0.0") == "v1.0.0"


# Test find_closest_version
def test_find_closest_version_within_versions():
    available_versions = ["v1.0.0", "v1.1.0", "v1.2.0", "v1.2.1", "v1.2.2", "v1.2.4"]
    assert find_closest_version("v1.2.3", available_versions) == "v1.2.2"
    assert find_closest_version("v1.1.5", available_versions) == "v1.1.0"
    assert find_closest_version("v1.0.5", available_versions) == "v1.0.0"


def test_find_closest_version_greater_than_available():
    target_version = "v2.0.0"
    available_versions = ["v1.0.0", "v1.1.0", "v1.2.0"]
    assert find_closest_version(target_version, available_versions) == "v1.2.0"


def test_find_closest_version_less_than_available():
    target_version = "v1.0.0"
    available_versions = ["v1.1.0", "v1.2.0", "v1.3.0"]
    assert find_closest_version(target_version, available_versions) == "v1.1.0"


def test_find_closest_version_equal_to_available():
    target_version = "v1.1.0"
    available_versions = ["v1.0.0", "v1.1.0", "v1.2.0"]
    assert find_closest_version(target_version, available_versions) == "v1.1.0"


def test_find_closest_version_no_available_versions():
    target_version = "v1.0.0"
    available_versions = []
    with pytest.raises(ValueError, match="No available versions found"):
        find_closest_version(target_version, available_versions)


def test_find_closest_version_with_invalid_version():
    available_versions = ["v1.0.0", "v1.1.0", "v1.2.0"]
    with pytest.raises(ValueError, match="Invalid version format"):
        find_closest_version("invalid-version", available_versions)


# Test find_closest_date
def test_find_closest_date_exact_match():
    target_date = "2024-04-15"
    available_dates = ["2024-04-10", "2024-04-15", "2024-04-20"]
    assert find_closest_date(target_date, available_dates) == "2024-04-15"


def test_find_closest_date_between_dates():
    available_dates = ["2024-04-10", "2024-04-15", "2024-04-20"]
    assert find_closest_date("2024-04-17", available_dates) == "2024-04-15"
    assert find_closest_date("2024-04-12", available_dates) == "2024-04-10"

    available_dates = ["2024-02-10", "2024-03-16", "2024-01-05", "2024-04-25"]
    assert find_closest_date("2024-03-16", available_dates) == "2024-03-16"
    assert find_closest_date("2024-03-15", available_dates) == "2024-02-10"
    assert find_closest_date("2024-04-15", available_dates) == "2024-03-16"
    assert find_closest_date("2024-01-12", available_dates) == "2024-01-05"


def test_find_closest_date_before_first_date():
    target_date = "2024-04-05"
    available_dates = ["2024-04-10", "2024-04-15", "2024-04-20"]
    assert find_closest_date(target_date, available_dates) == "2024-04-10"


def test_find_closest_date_after_last_date():
    target_date = "2024-04-25"
    available_dates = ["2024-04-10", "2024-04-15", "2024-04-20"]
    assert find_closest_date(target_date, available_dates) == "2024-04-20"
    assert find_closest_date("2024-04-03", available_dates) == "2024-04-10"


def test_find_closest_date_with_invalid_date():
    target_date = "2024-4-3"
    available_dates = ["2024-04-10", "2024-04-15", "2024-04-20"]
    with pytest.raises(ValueError, match="Invalid date format"):
        find_closest_date(target_date, available_dates)
