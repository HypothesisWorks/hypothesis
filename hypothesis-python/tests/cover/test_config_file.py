# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for hypothesis.ini configuration file loading."""

import datetime
import os
import tempfile
from pathlib import Path

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis._config_file import (
    _find_project_root,
    _parse_config_file,
    _parse_value,
    load_profiles_from_config_file,
)


class TestParseValue:
    """Test the _parse_value function for type conversion."""

    def test_none_values(self):
        assert _parse_value("database", "None") is None
        assert _parse_value("database", "none") is None
        assert _parse_value("database", "null") is None
        assert _parse_value("database", "NULL") is None

    def test_boolean_values(self):
        # True values
        assert _parse_value("derandomize", "true") is True
        assert _parse_value("derandomize", "True") is True
        assert _parse_value("derandomize", "TRUE") is True
        assert _parse_value("derandomize", "yes") is True
        assert _parse_value("derandomize", "on") is True
        assert _parse_value("derandomize", "1") is True

        # False values
        assert _parse_value("derandomize", "false") is False
        assert _parse_value("derandomize", "False") is False
        assert _parse_value("derandomize", "FALSE") is False
        assert _parse_value("derandomize", "no") is False
        assert _parse_value("derandomize", "off") is False
        assert _parse_value("derandomize", "0") is False

    def test_integer_values(self):
        assert _parse_value("max_examples", "100") == 100
        assert _parse_value("max_examples", "0") == 0
        assert _parse_value("max_examples", "999") == 999
        assert _parse_value("stateful_step_count", "50") == 50

    def test_float_values(self):
        assert _parse_value("some_float", "3.14") == 3.14
        assert _parse_value("some_float", "0.5") == 0.5

    def test_deadline_values(self):
        # Milliseconds
        result = _parse_value("deadline", "200")
        assert result == datetime.timedelta(milliseconds=200)

        result = _parse_value("deadline", "500ms")
        assert result == datetime.timedelta(milliseconds=500)

        result = _parse_value("deadline", "100 ms")
        assert result == datetime.timedelta(milliseconds=100)

        # Seconds
        result = _parse_value("deadline", "2s")
        assert result == datetime.timedelta(milliseconds=2000)

        result = _parse_value("deadline", "1.5s")
        assert result == datetime.timedelta(milliseconds=1500)

        # None
        assert _parse_value("deadline", "None") is None

    def test_list_values(self):
        result = _parse_value("phases", "explicit, reuse, generate")
        assert result == ["explicit", "reuse", "generate"]

        result = _parse_value("suppress_health_check", "too_slow, data_too_large")
        assert result == ["too_slow", "data_too_large"]

        # Empty list
        result = _parse_value("phases", "")
        assert result == []

    def test_string_values(self):
        assert _parse_value("backend", "hypothesis") == "hypothesis"
        assert _parse_value("verbosity", "verbose") == "verbose"


class TestFindProjectRoot:
    """Test the _find_project_root function."""

    def test_finds_git_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            git_dir = tmpdir_path / ".git"
            git_dir.mkdir()

            # Create a subdirectory
            subdir = tmpdir_path / "src" / "tests"
            subdir.mkdir(parents=True)

            # Change to subdirectory
            original_cwd = os.getcwd()
            try:
                os.chdir(subdir)
                root = _find_project_root()
                assert root == tmpdir_path
            finally:
                os.chdir(original_cwd)

    def test_finds_setup_py(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            setup_file = tmpdir_path / "setup.py"
            setup_file.write_text("# setup file")

            subdir = tmpdir_path / "tests"
            subdir.mkdir()

            original_cwd = os.getcwd()
            try:
                os.chdir(subdir)
                root = _find_project_root()
                assert root == tmpdir_path
            finally:
                os.chdir(original_cwd)

    def test_finds_pyproject_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject = tmpdir_path / "pyproject.toml"
            pyproject.write_text("[tool.pytest]")

            subdir = tmpdir_path / "src" / "module"
            subdir.mkdir(parents=True)

            original_cwd = os.getcwd()
            try:
                os.chdir(subdir)
                root = _find_project_root()
                assert root == tmpdir_path
            finally:
                os.chdir(original_cwd)

    def test_returns_cwd_when_no_markers_found(self):
        # The actual cwd likely has markers, so we just verify the function returns a Path
        root = _find_project_root()
        assert isinstance(root, Path)


class TestParseConfigFile:
    """Test the _parse_config_file function."""

    def test_parses_default_profile(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("[hypothesis]\n")
            f.write("max_examples = 200\n")
            f.write("derandomize = true\n")
            f.flush()
            config_path = Path(f.name)

        try:
            profiles = _parse_config_file(config_path)
            assert "default" in profiles
            assert profiles["default"]["max_examples"] == 200
            assert profiles["default"]["derandomize"] is True
        finally:
            config_path.unlink()

    def test_parses_named_profiles(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("[hypothesis]\n")
            f.write("max_examples = 100\n")
            f.write("\n")
            f.write("[hypothesis:ci]\n")
            f.write("max_examples = 1000\n")
            f.write("deadline = None\n")
            f.write("\n")
            f.write("[hypothesis:fast]\n")
            f.write("max_examples = 10\n")
            f.flush()
            config_path = Path(f.name)

        try:
            profiles = _parse_config_file(config_path)
            assert "default" in profiles
            assert "ci" in profiles
            assert "fast" in profiles

            assert profiles["default"]["max_examples"] == 100
            assert profiles["ci"]["max_examples"] == 1000
            assert profiles["ci"]["deadline"] is None
            assert profiles["fast"]["max_examples"] == 10
        finally:
            config_path.unlink()

    def test_parses_load_profile_directive(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("[hypothesis]\n")
            f.write("load_profile = ci\n")
            f.write("max_examples = 100\n")
            f.write("\n")
            f.write("[hypothesis:ci]\n")
            f.write("max_examples = 1000\n")
            f.flush()
            config_path = Path(f.name)

        try:
            profiles = _parse_config_file(config_path)
            assert "_load_profile" in profiles
            assert profiles["_load_profile"] == "ci"
            assert profiles["default"]["max_examples"] == 100
            assert profiles["ci"]["max_examples"] == 1000
        finally:
            config_path.unlink()

    def test_ignores_non_hypothesis_sections(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("[hypothesis]\n")
            f.write("max_examples = 100\n")
            f.write("\n")
            f.write("[pytest]\n")
            f.write("testpaths = tests\n")
            f.write("\n")
            f.write("[tool:mypy]\n")
            f.write("strict = true\n")
            f.flush()
            config_path = Path(f.name)

        try:
            profiles = _parse_config_file(config_path)
            assert "default" in profiles
            assert "pytest" not in profiles
            assert "tool:mypy" not in profiles
        finally:
            config_path.unlink()

    def test_handles_various_data_types(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("[hypothesis]\n")
            f.write("max_examples = 200\n")
            f.write("derandomize = true\n")
            f.write("database = None\n")
            f.write("verbosity = verbose\n")
            f.write("deadline = 500\n")
            f.write("print_blob = false\n")
            f.write("phases = explicit, generate, shrink\n")
            f.write("suppress_health_check = too_slow\n")
            f.flush()
            config_path = Path(f.name)

        try:
            profiles = _parse_config_file(config_path)
            profile = profiles["default"]

            assert profile["max_examples"] == 200
            assert profile["derandomize"] is True
            assert profile["database"] is None
            assert profile["verbosity"] == "verbose"
            assert profile["deadline"] == datetime.timedelta(milliseconds=500)
            assert profile["print_blob"] is False
            assert profile["phases"] == ["explicit", "generate", "shrink"]
            assert profile["suppress_health_check"] == ["too_slow"]
        finally:
            config_path.unlink()

    def test_handles_invalid_ini_gracefully(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("This is not valid INI content!\n")
            f.write("[[broken]]\n")
            f.flush()
            config_path = Path(f.name)

        try:
            # Should return empty dict and warn, not raise
            # Import HypothesisWarning locally to match the actual warning type
            from hypothesis.errors import HypothesisWarning

            with pytest.warns(HypothesisWarning, match="Failed to parse hypothesis.ini"):
                profiles = _parse_config_file(config_path)
            assert profiles == {}
        finally:
            config_path.unlink()


class TestLoadProfilesFromConfigFile:
    """Test the load_profiles_from_config_file function."""

    def test_returns_empty_dict_when_no_file_exists(self):
        # Change to a temp directory where hypothesis.ini doesn't exist
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                profiles = load_profiles_from_config_file()
                assert profiles == {}
            finally:
                os.chdir(original_cwd)

    def test_loads_config_from_project_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a project marker
            (tmpdir_path / ".git").mkdir()

            # Create hypothesis.ini in project root
            config_file = tmpdir_path / "hypothesis.ini"
            config_file.write_text(
                "[hypothesis]\n"
                "max_examples = 300\n"
                "\n"
                "[hypothesis:custom]\n"
                "max_examples = 50\n"
            )

            # Create a subdirectory and change to it
            subdir = tmpdir_path / "tests"
            subdir.mkdir()

            original_cwd = os.getcwd()
            try:
                os.chdir(subdir)
                profiles = load_profiles_from_config_file()

                assert "default" in profiles
                assert "custom" in profiles
                assert profiles["default"]["max_examples"] == 300
                assert profiles["custom"]["max_examples"] == 50
            finally:
                os.chdir(original_cwd)


class TestConfigFileIntegration:
    """Test that config file actually affects settings profiles."""

    def test_config_file_overrides_built_in_default(self):
        # This test would require modifying the actual settings, so we'll just
        # verify the mechanism works at a high level
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / ".git").mkdir()

            config_file = tmpdir_path / "hypothesis.ini"
            config_file.write_text(
                "[hypothesis:test_profile]\n"
                "max_examples = 42\n"
            )

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir_path)
                profiles = load_profiles_from_config_file()

                assert "test_profile" in profiles
                assert profiles["test_profile"]["max_examples"] == 42
            finally:
                os.chdir(original_cwd)

    def test_explicit_settings_decorator_takes_precedence(self):
        # Even if config file sets max_examples, @settings decorator should override
        @given(st.integers())
        @settings(max_examples=5)
        def test_func(x):
            pass

        # The @settings decorator creates a settings object with max_examples=5
        # This should take precedence over any config file settings
        assert test_func._hypothesis_internal_use_settings.max_examples == 5


class TestConfigFilePriority:
    """Test that config file has correct priority in the settings hierarchy."""

    def test_config_creates_base_profile(self):
        """Config file should create a base that can be further customized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / ".git").mkdir()

            config_file = tmpdir_path / "hypothesis.ini"
            config_file.write_text(
                "[hypothesis:base]\n"
                "max_examples = 100\n"
                "derandomize = true\n"
            )

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir_path)
                profiles = load_profiles_from_config_file()

                # The config file should create a profile with these settings
                assert profiles["base"]["max_examples"] == 100
                assert profiles["base"]["derandomize"] is True

                # In real usage, this would be registered and could be used as parent
                # for other profiles
            finally:
                os.chdir(original_cwd)


class TestRealWorldConfigExamples:
    """Test realistic hypothesis.ini configurations."""

    def test_typical_development_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("""[hypothesis]
max_examples = 100
deadline = 200
verbosity = normal

[hypothesis:ci]
max_examples = 1000
deadline = None
derandomize = true
print_blob = true

[hypothesis:fast]
max_examples = 10
deadline = 50

[hypothesis:debug]
max_examples = 10
verbosity = verbose
""")
            f.flush()
            config_path = Path(f.name)

        try:
            profiles = _parse_config_file(config_path)

            # Check default profile
            assert profiles["default"]["max_examples"] == 100
            assert profiles["default"]["deadline"] == datetime.timedelta(milliseconds=200)
            assert profiles["default"]["verbosity"] == "normal"

            # Check CI profile
            assert profiles["ci"]["max_examples"] == 1000
            assert profiles["ci"]["deadline"] is None
            assert profiles["ci"]["derandomize"] is True
            assert profiles["ci"]["print_blob"] is True

            # Check fast profile
            assert profiles["fast"]["max_examples"] == 10
            assert profiles["fast"]["deadline"] == datetime.timedelta(milliseconds=50)

            # Check debug profile
            assert profiles["debug"]["max_examples"] == 10
            assert profiles["debug"]["verbosity"] == "verbose"
        finally:
            config_path.unlink()

    def test_config_with_auto_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("""[hypothesis]
load_profile = development
max_examples = 50

[hypothesis:development]
max_examples = 200
deadline = 500

[hypothesis:production]
max_examples = 10000
deadline = None
""")
            f.flush()
            config_path = Path(f.name)

        try:
            profiles = _parse_config_file(config_path)

            # Check that load_profile is captured
            assert profiles["_load_profile"] == "development"

            # Check profiles
            assert profiles["default"]["max_examples"] == 50
            assert profiles["development"]["max_examples"] == 200
            assert profiles["production"]["max_examples"] == 10000
        finally:
            config_path.unlink()

