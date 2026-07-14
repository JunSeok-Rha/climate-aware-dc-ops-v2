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

    def calculate(self, zone_metrics: dict) -> dict:
        """
        Calculate risk scores for a single zone's aggregated metrics.

        Args:
            zone_metrics: Dict containing zone metrics with keys:
                - avg_cpu_usage: float (0-100)
                - avg_memory_usage: float (0-100)
                - avg_workload_intensity: float (0-100)
                - temperature: float (optional, defaults to 0 if missing)
                - humidity: float (optional, defaults to 0 if missing)

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
            - zone_imbalance_score: Currently approximated using MAD of cpu/memory/workload
              within the same row. This is a v1 interim measure; when multiple zones are
              active, this should be replaced with cross-zone MAD comparison.
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

        # Calculate zone_imbalance_score using MAD
        # v1 approximation: MAD of cpu/memory/workload within the same row
        zone_imbalance_score = self._calculate_mad_imbalance(cpu, memory, workload)

        # Clamp all scores to 0-100 range
        return {
            "heat_risk_score": self._clamp(heat_risk_score, 0, 100),
            "cooling_stress_score": self._clamp(cooling_stress_score, 0, 100),
            "zone_imbalance_score": self._clamp(zone_imbalance_score, 0, 100),
        }

    def _calculate_mad_imbalance(
        self, cpu: float, memory: float, workload: float
    ) -> float:
        """
        Calculate zone imbalance using Median Absolute Deviation.

        This is a v1 approximation that measures imbalance among cpu/memory/workload
        within a single zone row. When multiple zones are active, this should be
        replaced with cross-zone MAD comparison.

        Args:
            cpu: CPU usage (0-100)
            memory: Memory usage (0-100)
            workload: Workload intensity (0-100)

        Returns:
            Imbalance score (0-100), where higher values indicate more imbalance
        """
        values = sorted([cpu, memory, workload])
        median = values[1]  # Middle value of 3 sorted values

        # Calculate absolute deviations from median
        deviations = [abs(v - median) for v in values]
        mad = sorted(deviations)[1]  # Median of deviations (middle value)

        # Normalize MAD to 0-100 scale
        # Maximum theoretical MAD for values in 0-100 range is 50
        # (e.g., when values are 0, 0, 100: median=0, deviations=[0,0,100], MAD=0)
        # (e.g., when values are 0, 50, 100: median=50, deviations=[50,0,50], MAD=50)
        # We scale MAD by 2 to get 0-100 range
        imbalance_score = mad * 2

        return imbalance_score

    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value to specified range."""
        return max(min_val, min(max_val, value))
