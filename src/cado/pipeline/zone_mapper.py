"""Zone Mapper module for mapping instance IDs to zone IDs."""

import logging
from pathlib import Path
from typing import Dict

import yaml

logger = logging.getLogger(__name__)


class ZoneMappingError(Exception):
    """Raised when an instance_id cannot be mapped to a zone."""

    pass


class ZoneMapper:
    """Maps EC2 instance IDs to zone IDs based on config.yaml."""

    def __init__(self, config_path: str | Path | None = None):
        """
        Initialize ZoneMapper with configuration.

        Args:
            config_path: Path to config.yaml. If None, uses default location.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        else:
            config_path = Path(config_path)

        self._instance_to_zone: Dict[str, str] = {}
        self._load_config(config_path)

    def _load_config(self, config_path: Path) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            self._instance_to_zone = config.get("instance_to_zone") or {}
            logger.info(
                f"Loaded zone mapping configuration with {len(self._instance_to_zone)} mappings"
            )

        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse config YAML: {e}")
            raise

    def map(self, instance_id: str) -> str:
        """
        Map an instance ID to its corresponding zone ID.

        Args:
            instance_id: EC2 instance ID to map

        Returns:
            zone_id: Corresponding zone ID (e.g., "zone_1")

        Raises:
            ZoneMappingError: If instance_id is not found in the mapping
        """
        if instance_id not in self._instance_to_zone:
            raise ZoneMappingError(
                f"Instance ID '{instance_id}' not found in zone mapping. "
                f"Available instances: {list(self._instance_to_zone.keys())}"
            )

        zone_id = self._instance_to_zone[instance_id]
        logger.debug(f"Mapped instance {instance_id} to zone {zone_id}")
        return zone_id
