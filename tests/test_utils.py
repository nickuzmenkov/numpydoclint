"""Test utilities."""
import logging
import textwrap
from pathlib import Path

import pytest

from numpydoclint.utils import get_first, parse_bool, parse_pyproject_toml, parse_set, parse_setup_cfg
from tests.utils import get_log_records, get_name


@pytest.fixture
def caplog(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.DEBUG)
    return caplog


class TestGetFirst:
    """Test get first."""

    def test_empty_sequence(self):
        """Test empty sequence."""
        assert get_first(iterable=[]) is None

    def test_all_false(self):
        """Test sequence with all elements evaluating to False."""
        assert get_first(iterable=[None, False, [], "", {}, set(), 0]) is None

    def test_default(self):
        """Test that the default value is returned if all elements evaluate to False."""
        default = get_name()
        assert get_first(iterable=[], default=default) == default

    def test_success(self):
        """Test that the first value that evaluates to True is returned."""
        value = get_name()
        assert get_first(iterable=[None, False, [], value, "", {}, set(), 0]) == value


class TestParseSet:
    """Test parse set."""

    def test_empty_string(self):
        """Test parse empty string."""
        assert parse_set(str_or_list="") == set()

    def test_single_item(self):
        """Test parse string with a single item."""
        item = get_name()
        assert parse_set(str_or_list=item) == {item}

    def test_string_with_newlines(self):
        """Test parsing strings with newlines between the elements."""
        result = {"a", "b"}
        assert parse_set(str_or_list="a,\nb") == result
        assert parse_set(str_or_list="a\n,b") == result
        assert parse_set(str_or_list="a,\n\nb") == result
        assert parse_set(str_or_list="a\n\n,b") == result
        assert parse_set(str_or_list="a\n,\nb") == result

    def test_extra_whitespace(self):
        """Test parsing strings with extra whitespace between the elements."""
        result = {"a", "b"}
        assert parse_set(str_or_list="a ,b") == result
        assert parse_set(str_or_list="a, b") == result
        assert parse_set(str_or_list=" a,b") == result
        assert parse_set(str_or_list="a,b ") == result

    def test_empty_substrings(self):
        """Test parsing empty strings with separators.

        The result must still be empty set.
        """
        result = set()
        assert parse_set(str_or_list=" ") == result
        assert parse_set(str_or_list=",") == result
        assert parse_set(str_or_list=" ,") == result
        assert parse_set(str_or_list="\n") == result
        assert parse_set(str_or_list="\n,") == result
        assert parse_set(str_or_list="\n,") == result

    def test_parse_empty_list(self):
        """Test parsing empty list."""
        assert parse_set(str_or_list=[]) == set()

    def test_parse_list_with_items_with_extra_whitespace(self):
        """Test parsing list with elements that have extra whitespace."""
        result = {"a", "b"}
        assert parse_set(str_or_list=["a ", "b"]) == result
        assert parse_set(str_or_list=["a", " b"]) == result
        assert parse_set(str_or_list=[" a", "b"]) == result
        assert parse_set(str_or_list=["a", "b "]) == result

    def test_parse_list_with_empty_items(self):
        """Test parsing list with empty elements."""
        result = set()
        assert parse_set(str_or_list=[""]) == result
        assert parse_set(str_or_list=[" "]) == result
        assert parse_set(str_or_list=["", " "]) == result


class TestParseBool:
    """Test parse bool."""

    def test_empty_string(self):
        """Test parse empty string."""
        assert parse_bool("") is False

    def test_whitespace_string(self):
        """Test parse string containing only the whitespace."""
        assert parse_bool(" \n ") is False

    def test_bool(self):
        """Test parse boolean."""
        assert parse_bool(True) is True
        assert parse_bool(False) is False

    def test_false(self):
        """Test parse strings that evaluate to False."""
        assert parse_bool("False") is False
        assert parse_bool("false      ") is False
        assert parse_bool("\n    False") is False

    def test_true(self):
        """Test parse strings that evaluate to True."""
        assert parse_bool("True") is True
        assert parse_bool("true      ") is True
        assert parse_bool("\n    True") is True


class TestParseSetupCfg:
    """Test parse setup.cfg."""

    def test_non_existent(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test non-existent config."""
        config = parse_setup_cfg(config_dir=str(tmp_path))

        assert config
        assert all(x == "" for x in config.values())

        debug_records = get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_setup_cfg")
        assert len(debug_records) == 1
        assert "Config file 'setup.cfg' not found." in debug_records[0].message

    def test_no_section(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test config with no sections related to the linter."""
        Path(tmp_path, "setup.cfg").touch()
        config = parse_setup_cfg(config_dir=str(tmp_path))

        assert config
        assert all(x == "" for x in config.values())

        debug_records = get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_setup_cfg")
        assert len(debug_records) == 1
        assert debug_records[0].message == "Config file 'setup.cfg' exists but has no '[numpydoclint]' section."

    def test_malformed(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test malformed config."""
        with open(Path(tmp_path, "setup.cfg"), "w") as file:
            file.write("[malformed")

        config = parse_setup_cfg(config_dir=str(tmp_path))

        assert config
        assert all(x == "" for x in config.values())

        debug_records = get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_setup_cfg")
        assert len(debug_records) == 1
        assert "Config file 'setup.cfg' was not parsed due to exception" in debug_records[0].message

    def test_no_keys_in_section(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test config with an empty section related to the linter."""
        with open(Path(tmp_path, "setup.cfg"), "w") as file:
            file.write(f"[numpydoclint]")

        config = parse_setup_cfg(config_dir=str(tmp_path))

        assert config
        assert all(x == "" for x in config.values())
        assert not get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_setup_cfg")

    def test_some_keys_missing(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test parse configuration with some keys missing."""
        ignore_paths = [get_name() for _ in range(5)]

        with open(Path(tmp_path, "setup.cfg"), "w") as file:
            file.write(
                textwrap.dedent(
                    f"""
                    [numpydoclint]
                    ignore_paths = {ignore_paths}
                    """
                )
            )

        config = parse_setup_cfg(config_dir=str(tmp_path))

        assert config
        assert config["ignore_errors"] == ""
        assert config["ignore_paths"] == str(ignore_paths)
        assert config["ignore_hidden"] == ""
        assert config["filename_pattern"] == ""
        assert not get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_setup_cfg")

    def test_all_keys_present(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test parse configuration with all keys present."""
        ignore_errors = ",".join(get_name() for _ in range(5))
        ignore_paths = ",".join(get_name() for _ in range(5))
        ignore_hidden = "true"
        filename_pattern = get_name()

        with open(Path(tmp_path, "setup.cfg"), "w") as file:
            file.write(
                textwrap.dedent(
                    f"""
                    [numpydoclint]
                    ignore_errors = {ignore_errors}
                    ignore_paths = {ignore_paths}
                    ignore_hidden = {ignore_hidden}
                    filename_pattern = {filename_pattern}
                    """
                )
            )

        config = parse_setup_cfg(config_dir=str(tmp_path))

        assert config
        assert config["ignore_errors"] == ignore_errors
        assert config["ignore_paths"] == ignore_paths
        assert config["ignore_hidden"] == ignore_hidden
        assert config["filename_pattern"] == filename_pattern
        assert not get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_setup_cfg")


class TestParsePyprojectToml:
    """Test parse pyproject.toml."""

    def test_non_existent(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test non-existent config."""
        config = parse_pyproject_toml(config_dir=str(tmp_path))

        assert config
        assert all(x == "" for x in config.values())

        debug_records = get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_pyproject_toml")
        assert len(debug_records) == 1
        assert "Config file 'pyproject.toml' not found." in debug_records[0].message

    def test_no_section(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test config with no sections related to the linter."""
        Path(tmp_path, "pyproject.toml").touch()
        config = parse_pyproject_toml(config_dir=str(tmp_path))

        assert config
        assert all(x == "" for x in config.values())

        debug_records = get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_pyproject_toml")
        assert len(debug_records) == 1
        assert debug_records[0].message == "Config file 'pyproject.toml' exists but has no '[tool.numpydoclint]' section."

    def test_malformed(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test malformed config."""
        with open(Path(tmp_path, "pyproject.toml"), "w") as file:
            file.write("[tool.malformed")

        config = parse_pyproject_toml(config_dir=str(tmp_path))

        assert config
        assert all(x == "" for x in config.values())

        warning_records = get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_pyproject_toml")
        assert len(warning_records) == 1
        assert "Config file 'pyproject.toml' was not parsed due to exception" in warning_records[0].message

    def test_no_keys_in_section(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test config with an empty section related to the linter."""
        with open(Path(tmp_path, "pyproject.toml"), "w") as file:
            file.write(f"[tool.numpydoclint]")

        config = parse_pyproject_toml(config_dir=str(tmp_path))

        assert config
        assert all(x == "" for x in config.values())
        assert not get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_pyproject_toml")

    def test_some_keys_missing(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test parse configuration with some keys missing."""
        ignore_paths = [get_name() for _ in range(5)]

        with open(Path(tmp_path, "pyproject.toml"), "w") as file:
            file.write(
                textwrap.dedent(
                    f"""
                    [tool.numpydoclint]
                    ignore_paths = {ignore_paths}
                    """
                )
            )

        config = parse_pyproject_toml(config_dir=str(tmp_path))

        assert config
        assert config["ignore_errors"] == ""
        assert config["ignore_paths"] == ignore_paths
        assert config["ignore_hidden"] == ""
        assert config["filename_pattern"] == ""
        assert not get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_pyproject_toml")

    def test_all_keys_present(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Test parse configuration with all keys present."""
        ignore_errors = [get_name() for _ in range(5)]
        ignore_paths = [get_name() for _ in range(5)]
        filename_pattern = get_name()

        with open(Path(tmp_path, "pyproject.toml"), "w") as file:
            file.write(
                textwrap.dedent(
                    f"""
                    [tool.numpydoclint]
                    ignore_errors = {ignore_errors}
                    ignore_paths = {ignore_paths}
                    ignore_hidden = true
                    filename_pattern = "{filename_pattern}"
                    """
                )
            )

        config = parse_pyproject_toml(config_dir=str(tmp_path))

        assert config
        assert config["ignore_errors"] == ignore_errors
        assert config["ignore_paths"] == ignore_paths
        assert config["ignore_hidden"] is True
        assert config["filename_pattern"] == filename_pattern
        assert not get_log_records(caplog=caplog, level=logging.DEBUG, func_name="parse_pyproject_toml")
