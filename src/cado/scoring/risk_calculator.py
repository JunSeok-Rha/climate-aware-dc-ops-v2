"""Risk Calculator module for computing anomaly detection scores."""

import logging
from pathlib import Path
from typing import Dict

import yaml

logger = logging.getLogger(__name__)


class RiskCalculationError(Exception):
    """Raised when risk calculation fails."""

    pass


class RiskCalculator:
    """Calculates risk scores for zone-aggregated metrics."""

    def __init__(self, config_path: str | Path | None = None):
        """
        Initialize RiskCalculator with configuration.

        Args:
            config_path: Path to config.yaml. If None, uses default location.

        Raises:
            FileNotFoundError: If config file is not found.
            yaml.YAMLError: If config parsing fails.
            RiskCalculationError: If risk_weights configuration is missing.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        else:
            config_path = Path(config_path)

        self._weights: Dict = {}
        self._load_config(config_path)

    def _load_config(self, config_path: Path) -> None:
        """Load risk weights from YAML configuration."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            if "risk_weights" not in config:
                raise RiskCalculationError(
                    "Missing 'risk_weights' section in config.yaml"
                )

            self._weights = config["risk_weights"]

            # Validate required weight sections
            if "heat_risk" not in self._weights:
                raise RiskCalculationError(
                    "Missing 'heat_risk' section in risk_weights"
                )
            if "cooling_stress" not in self._weights:
                raise RiskCalculationError(
                    "Missing 'cooling_stress' section in risk_weights"
                )

            logger.info("Loaded risk scoring weights from configuration")

        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse config YAML: {e}")
            raise

    def calculate(self, zone_metrics: dict, zone_imbalance_score: float = 0.0) -> dict:
        """
        Calculate risk scores for a single zone's aggregated metrics.

        Args:
            zone_metrics: Dict containing zone metrics with keys:
                - avg_cpu_usage: float (0-100)
                - avg_memory_usage: float (0-100)
                - avg_workload_intensity: float (0-100)
                - temperature: float (optional, defaults to 0 if missing)
                - humidity: float (optional, defaults to 0 if missing)
            zone_imbalance_score: Pre-calculated zone imbalance score (0-100).
                Should be computed using calculate_imbalance() for cross-zone comparison.
                Defaults to 0.0 if not provided.

        Returns:
            Dict with computed scores:
                {
                    "heat_risk_score": float (0-100),
                    "cooling_stress_score": float (0-100),
                    "zone_imbalance_score": float (0-100)
                }

        Note:
            - All scores are clamped to 0-100 range
            - temperature/humidity are NULL-safe (default to 0 if missing)
            - zone_imbalance_score should be computed separately using calculate_imbalance()
              which performs cross-zone MAD comparison based on avg_cpu_usage
        """
        # Extract metrics with NULL-safe defaults
        cpu = zone_metrics.get("avg_cpu_usage") or 0
        memory = zone_metrics.get("avg_memory_usage") or 0
        workload = zone_metrics.get("avg_workload_intensity") or 0
        temperature = zone_metrics.get("temperature") or 0
        humidity = zone_metrics.get("humidity") or 0

        # Calculate heat_risk_score
        heat_weights = self._weights["heat_risk"]
        heat_risk_score = (
            temperature * heat_weights["temperature"]
            + cpu * heat_weights["cpu"]
            + workload * heat_weights["workload"]
        )

        # Calculate cooling_stress_score
        cooling_weights = self._weights["cooling_stress"]
        cooling_stress_score = (
            temperature * cooling_weights["temperature"]
            + humidity * cooling_weights["humidity"]
            + cpu * cooling_weights["cpu"]
            + memory * cooling_weights["memory"]
        )

        # Clamp all scores to 0-100 range
        return {
            "heat_risk_score": self._clamp(heat_risk_score, 0, 100),
            "cooling_stress_score": self._clamp(cooling_stress_score, 0, 100),
            "zone_imbalance_score": self._clamp(zone_imbalance_score, 0, 100),
        }

    def calculate_imbalance(self, all_zones: list[dict]) -> dict[str, float]:
        """
        Calculate zone imbalance scores via cross-zone MAD comparison.

        Compares each zone's avg_cpu_usage against the overall median to identify
        zones with anomalous workload distribution.

        Args:
            all_zones: List of zone metric dicts, each containing at least:
                - zone_id: str
                - avg_cpu_usage: float (0-100)

        Returns:
            Dict mapping zone_id to imbalance_score (0-100), where higher values
            indicate greater deviation from the median CPU usage across all zones.

        Note:
            - If only 1 zone exists, returns {zone_id: 0.0} (no comparison possible)
            - If all zones have identical avg_cpu_usage, returns all 0.0 (no deviation)
            - Normalization: MAD-based deviation scaled to 0-100 range
        """
        # Edge case: single zone has no cross-zone comparison
        if len(all_zones) <= 1:
            if len(all_zones) == 1:
                zone_id = all_zones[0].get("zone_id", "unknown")
                return {zone_id: 0.0}
            return {}

        # Extract CPU usage values and build zone_id mapping
        zone_cpu_map = {}
        for zone in all_zones:
            zone_id = zone.get("zone_id")
            cpu_usage = zone.get("avg_cpu_usage") or 0.0
            if zone_id:
                zone_cpu_map[zone_id] = cpu_usage

        cpu_values = list(zone_cpu_map.values())

        # Calculate median of all CPU values
        sorted_values = sorted(cpu_values)
        n = len(sorted_values)
        if n % 2 == 0:
            median = (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            median = sorted_values[n // 2]

        # Calculate absolute deviations from median
        deviations = [abs(cpu - median) for cpu in cpu_values]

        # Calculate MAD (median of absolute deviations)
        sorted_deviations = sorted(deviations)
        if n % 2 == 0:
            mad = (sorted_deviations[n // 2 - 1] + sorted_deviations[n // 2]) / 2
        else:
            mad = sorted_deviations[n // 2]

        # Edge case: all zones have identical CPU usage (MAD = 0)
        if mad == 0:
            return {zone_id: 0.0 for zone_id in zone_cpu_map.keys()}

        # Calculate normalized imbalance score for each zone
        result = {}
        for zone_id, cpu_usage in zone_cpu_map.items():
            deviation = abs(cpu_usage - median)
            # Normalize by MAD and scale to 0-100
            # A zone with deviation = MAD gets score of ~50
            # A zone with deviation = 2*MAD gets score of 100 (clamped)
            normalized_score = (deviation / mad) * 50
            result[zone_id] = self._clamp(normalized_score, 0, 100)

        return result

    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value to specified range."""
        return max(min_val, min(max_val, value))
