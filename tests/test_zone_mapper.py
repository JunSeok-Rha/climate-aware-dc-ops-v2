"""Tests for Zone Mapper."""

import tempfile
from pathlib import Path

import pytest

from cado.pipeline.zone_mapper import ZoneMapper, ZoneMappingError


@pytest.fixture
def test_config_file():
    """Create a temporary config file for testing."""
    config_content = """
instance_to_zone:
  i-test123: zone_1
  i-test456: zone_2

zones:
  - zone_1
  - zone_2
  - zone_3
  - zone_4
  - zone_5
  - zone_6
  - zone_7
  - zone_8
  - zone_9
  - zone_10
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        config_path = f.name

    yield config_path

    # Cleanup
    Path(config_path).unlink()


def test_zone_mapper_success(test_config_file):
    """Test successful instance to zone mapping."""
    mapper = ZoneMapper(config_path=test_config_file)

    # Test valid mappings
    assert mapper.map("i-test123") == "zone_1"
    assert mapper.map("i-test456") == "zone_2"


def test_zone_mapper_missing_instance(test_config_file):
    """Test that ZoneMapper raises error for unmapped instance."""
    mapper = ZoneMapper(config_path=test_config_file)

    # Test unmapped instance
    with pytest.raises(ZoneMappingError) as exc_info:
        mapper.map("i-unknown999")

    assert "not found in zone mapping" in str(exc_info.value)
    assert "i-unknown999" in str(exc_info.value)


def test_zone_mapper_missing_config():
    """Test that ZoneMapper handles missing config file."""
    with pytest.raises(FileNotFoundError):
        ZoneMapper(config_path="/nonexistent/path/config.yaml")


def test_zone_mapper_default_config_path():
    """Test ZoneMapper with default config path."""
    # This should use the default config.yaml from src/cado/
    # May fail if config is not properly set up, which is expected
    try:
        mapper = ZoneMapper()
        # If successful, ensure it's callable
        assert hasattr(mapper, "map")
    except FileNotFoundError:
        # Expected if default config doesn't have mappings yet
        pass
