# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Configuration file loader for Hypothesis settings."""

import configparser
import datetime
import re
import warnings
from pathlib import Path
from typing import Any

from hypothesis.errors import HypothesisWarning

__all__ = ["load_profile_from_config_file"]


def _find_project_root() -> Path | None:
    """
    Find the project root by looking for common project markers.

    Searches upward from the current working directory for markers like:
    .git/, setup.py, pyproject.toml, etc.

    Returns None if no project root is found.
    """
    cwd = Path.cwd()

    # Common project root markers
    root_markers = [
        ".git",
        "setup.py",
        "setup.cfg",
        "pyproject.toml",
        "tox.ini",
        "pytest.ini",
    ]

    # Check current directory and all parents
    for directory in [cwd, *cwd.parents]:
        for marker in root_markers:
            if (directory / marker).exists():
                return directory

    # If no markers found, return cwd as fallback
    return cwd


def _parse_value(key: str, value: str) -> Any:
    """
    Convert a string value from INI file to appropriate Python type.

    Args:
        key: The setting name (used to infer type)
        value: The string value from the INI file

    Returns:
        The converted value in appropriate Python type
    """
    # Strip whitespace
    value = value.strip()

    # Handle None/null
    if value.lower() in ("none", "null"):
        return None

    # Handle booleans
    if value.lower() in ("true", "yes", "on", "1"):
        return True
    if value.lower() in ("false", "no", "off", "0"):
        return False

    # Handle durations (e.g., "200ms", "1s", "500")
    if key == "deadline":
        if value.lower() in ("none", "null"):
            return None
        # Try to parse duration strings
        duration_match = re.match(r"^(\d+(?:\.\d+)?)\s*(ms|s|sec|seconds?|milliseconds?)?$", value.lower())
        if duration_match:
            amount = float(duration_match.group(1))
            unit = duration_match.group(2) or ""
            if unit in ("ms", "milliseconds", "millisecond"):
                return datetime.timedelta(milliseconds=amount)
            elif unit in ("s", "sec", "seconds", "second"):
                return datetime.timedelta(seconds=amount)
            else:
                # Default to milliseconds if no unit specified (for backward compatibility)
                return datetime.timedelta(milliseconds=amount)
        # If we can't parse it, fall through to try as a number
        try:
            return datetime.timedelta(milliseconds=float(value))
        except ValueError:
            pass

    # Handle lists/tuples (comma-separated values)
    if key in ("phases", "suppress_health_check"):
        if not value:
            return []
        # Split by comma and strip whitespace
        items = [item.strip() for item in value.split(",")]
        return items

    # Try to parse as int
    try:
        return int(value)
    except ValueError:
        pass

    # Try to parse as float
    try:
        return float(value)
    except ValueError:
        pass

    # Return as string if nothing else works
    return value


def _parse_config_file(config_path: Path) -> dict[str, dict[str, Any] | str]:
    """
    Parse a hypothesis.ini configuration file.

    Args:
        config_path: Path to the hypothesis.ini file

    Returns:
        A dictionary mapping profile names to their settings dictionaries.
        The special key "_load_profile" may contain the name of the profile
        to auto-load.
    """
    parser = configparser.ConfigParser()

    try:
        parser.read(config_path)
    except configparser.Error as e:
        warnings.warn(
            f"Failed to parse hypothesis.ini at {config_path}: {e}",
            HypothesisWarning,
            stacklevel=3,
        )
        return {}

    profiles: dict[str, dict[str, Any] | str] = {}

    for section in parser.sections():
        # Section names are either [hypothesis] or [hypothesis:profile_name]
        if section == "hypothesis":
            profile_name = "default"
        elif section.startswith("hypothesis:"):
            profile_name = section[len("hypothesis:"):]
        else:
            # Ignore non-hypothesis sections
            continue

        settings_dict: dict[str, Any] = {}

        for key, value in parser.items(section):
            # Special key for auto-loading a profile
            if key == "load_profile":
                profiles["_load_profile"] = value
                continue

            # Convert the value to appropriate type
            settings_dict[key] = _parse_value(key, value)

        if settings_dict:
            profiles[profile_name] = settings_dict

    return profiles


def load_profiles_from_config_file() -> dict[str, dict[str, Any] | str]:
    """
    Load Hypothesis settings profiles from a hypothesis.ini file.

    Searches for hypothesis.ini at the project root (determined by looking
    for .git/, setup.py, pyproject.toml, etc.).

    Returns:
        A dictionary mapping profile names to their settings dictionaries.
        Returns an empty dict if no config file is found or if parsing fails.
    """
    project_root = _find_project_root()
    if project_root is None:
        return {}

    config_path = project_root / "hypothesis.ini"
    if not config_path.exists():
        return {}

    return _parse_config_file(config_path)

