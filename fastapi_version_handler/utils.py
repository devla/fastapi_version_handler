import bisect
import re
from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from packaging import version as versionpkg


def validate_version(version: str) -> None:
    """Validate the version header format."""
    if not version:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Version header is missing",
        )

    if not (is_valid_version(version) or is_valid_date(version)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid version format",
        )


def is_valid_version(version: str) -> bool:
    """Check if the version string has a valid format."""
    if version in ("v0.0.0", "0.0.0"):
        return False

    pattern = r"^(v)?\d+\.\d+\.\d+$"  # Allow optional 'v' prefix
    return re.match(pattern, version) is not None


def is_valid_date(date_string: str) -> bool:
    """Check if the date string has a valid 'YYYY-MM-DD' format."""
    components = date_string.split("-")
    if len(components) != 3:
        return False
    year, month, day = components
    if not (
        year.isdigit() and len(year) == 4 and month.isdigit() and len(month) == 2 and day.isdigit() and len(day) == 2
    ):
        return False
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def normalize_version(version: str) -> str:
    """Normalize the version string to include the 'v' prefix."""
    if is_valid_version(version) and not version.startswith("v"):
        version = "v" + version
    return version


def find_closest_version(target_version: str, available_versions: List[str]) -> str:
    """Find the closest version to the target version."""
    if not is_valid_version(target_version):
        raise ValueError("Invalid version format")

    try:
        target_version = normalize_version(target_version)
        available_versions = [normalize_version(v) for v in available_versions]
        return max(v for v in available_versions if versionpkg.parse(v) <= versionpkg.parse(target_version))
    except ValueError as err:
        if available_versions:
            return available_versions[0]
        raise ValueError("No available versions found") from err


def find_closest_date(target_date: str, available_dates: List[str]) -> str:
    if not is_valid_date(target_date):
        raise ValueError("Invalid date format")

    if target_date in available_dates:
        return target_date

    available_dates = sorted(available_dates)
    index = bisect.bisect_left(available_dates, target_date)

    if index == 0:  # If the target date is earlier than the first available date
        closest_date = available_dates[0]
    elif index == len(
        available_dates,
    ):  # If the target date is later than the last available date
        closest_date = available_dates[-1]
    else:  # If the target date falls between two available dates
        closest_date = available_dates[index - 1]

    return closest_date
