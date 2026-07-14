"""Tests for RiskCalculator."""

import pytest
from pathlib import Path

from cado.scoring.risk_calculator import RiskCalculator, RiskCalculationError


class TestRiskCalculator:
    """Test suite for RiskCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create RiskCalculator instance with default config."""
        # Use default config path (src/cado/config.yaml)
        return RiskCalculator()

    def test_normal_input(self, calculator):
        """Test with normal mid-range values."""
        zone_metrics = {
            "avg_cpu_usage": 50.0,
            "avg_memory_usage": 50.0,
            "avg_workload_intensity": 50.0,
            "temperature": 50.0,
            "humidity": 50.0,
        }

        result = calculator.calculate(zone_metrics)

        # All scores should be in 0-100 range
        assert 0 <= result["heat_risk_score"] <= 100
        assert 0 <= result["cooling_stress_score"] <= 100
        assert 0 <= result["zone_imbalance_score"] <= 100

        # With mid-range values and non-zero weights, scores should be positive
        assert result["heat_risk_score"] > 0
        assert result["cooling_stress_score"] > 0
        # Imbalance should be 0 since all three metrics are equal (50)
        assert result["zone_imbalance_score"] == 0

    def test_all_zeros(self, calculator):
        """Test with all zero input values."""
        zone_metrics = {
            "avg_cpu_usage": 0.0,
            "avg_memory_usage": 0.0,
            "avg_workload_intensity": 0.0,
            "temperature": 0.0,
            "humidity": 0.0,
        }

        result = calculator.calculate(zone_metrics)

        # All scores should be 0 or very close to 0
        assert result["heat_risk_score"] == 0
        assert result["cooling_stress_score"] == 0
        assert result["zone_imbalance_score"] == 0

    def test_all_max_values(self, calculator):
        """Test with all maximum (100) input values."""
        zone_metrics = {
            "avg_cpu_usage": 100.0,
            "avg_memory_usage": 100.0,
            "avg_workload_intensity": 100.0,
            "temperature": 100.0,
            "humidity": 100.0,
        }

        result = calculator.calculate(zone_metrics)

        # Scores should be at or near 100 (weighted sum of 100s should be 100)
        assert result["heat_risk_score"] == 100
        assert result["cooling_stress_score"] == 100
        # Imbalance should be 0 since all three metrics are equal (100)
        assert result["zone_imbalance_score"] == 0

    def test_missing_temperature_humidity(self, calculator):
        """Test NULL-safe behavior when temperature/humidity are missing."""
        zone_metrics = {
            "avg_cpu_usage": 60.0,
            "avg_memory_usage": 40.0,
            "avg_workload_intensity": 50.0,
            # temperature and humidity are intentionally missing
        }

        # Should not raise an exception
        result = calculator.calculate(zone_metrics)

        # All scores should still be in valid range
        assert 0 <= result["heat_risk_score"] <= 100
        assert 0 <= result["cooling_stress_score"] <= 100
        assert 0 <= result["zone_imbalance_score"] <= 100

        # Scores should be positive (based on cpu/memory/workload only)
        assert result["heat_risk_score"] > 0
        assert result["cooling_stress_score"] > 0
        # Imbalance should be > 0 since metrics differ (60, 40, 50)
        assert result["zone_imbalance_score"] > 0

    def test_none_values_treated_as_zero(self, calculator):
        """Test that None values are treated as 0."""
        zone_metrics = {
            "avg_cpu_usage": 50.0,
            "avg_memory_usage": 50.0,
            "avg_workload_intensity": 50.0,
            "temperature": None,  # Explicitly None
            "humidity": None,  # Explicitly None
        }

        result = calculator.calculate(zone_metrics)

        # Should calculate successfully without errors
        assert 0 <= result["heat_risk_score"] <= 100
        assert 0 <= result["cooling_stress_score"] <= 100
        assert result["zone_imbalance_score"] == 0  # All three metrics equal

    def test_imbalance_calculation(self, calculator):
        """Test zone imbalance score with varying metrics."""
        # Highly imbalanced: 0, 50, 100
        zone_metrics = {
            "avg_cpu_usage": 0.0,
            "avg_memory_usage": 50.0,
            "avg_workload_intensity": 100.0,
        }

        result = calculator.calculate(zone_metrics)

        # Should have maximum imbalance score
        # MAD of [0, 50, 100]: median=50, deviations=[50, 0, 50], MAD=50
        # Normalized: 50 * 2 = 100
        assert result["zone_imbalance_score"] == 100

        # Moderately imbalanced: 30, 50, 70
        zone_metrics_moderate = {
            "avg_cpu_usage": 30.0,
            "avg_memory_usage": 50.0,
            "avg_workload_intensity": 70.0,
        }

        result_moderate = calculator.calculate(zone_metrics_moderate)

        # Should have moderate imbalance
        # MAD of [30, 50, 70]: median=50, deviations=[20, 0, 20], MAD=20
        # Normalized: 20 * 2 = 40
        assert result_moderate["zone_imbalance_score"] == 40

    def test_missing_config_section_raises_error(self):
        """Test that missing risk_weights section raises error."""
        # Create a temporary config without risk_weights
        import tempfile
        import yaml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"zones": ["zone_1"]}, f)
            temp_config_path = f.name

        try:
            with pytest.raises(RiskCalculationError, match="risk_weights"):
                RiskCalculator(config_path=temp_config_path)
        finally:
            Path(temp_config_path).unlink()

    def test_clamping(self, calculator):
        """Test that scores are properly clamped to 0-100."""
        # Test with extreme values that might cause overflow
        zone_metrics = {
            "avg_cpu_usage": 200.0,  # Over 100
            "avg_memory_usage": 200.0,
            "avg_workload_intensity": 200.0,
            "temperature": 200.0,
            "humidity": 200.0,
        }

        result = calculator.calculate(zone_metrics)

        # All scores should be clamped to max 100
        assert result["heat_risk_score"] == 100
        assert result["cooling_stress_score"] == 100
        assert result["zone_imbalance_score"] <= 100
