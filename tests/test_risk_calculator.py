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
        # Imbalance defaults to 0 when not provided
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
        # Imbalance defaults to 0 when not provided
        assert result["zone_imbalance_score"] == 0

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

    def test_imbalance_score_parameter(self, calculator):
        """Test that zone_imbalance_score parameter is properly included in results."""
        zone_metrics = {
            "avg_cpu_usage": 50.0,
            "avg_memory_usage": 50.0,
            "avg_workload_intensity": 50.0,
        }

        # Test with custom imbalance score
        result = calculator.calculate(zone_metrics, zone_imbalance_score=75.0)
        assert result["zone_imbalance_score"] == 75.0

        # Test with default (0.0)
        result_default = calculator.calculate(zone_metrics)
        assert result_default["zone_imbalance_score"] == 0.0

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


class TestCalculateImbalance:
    """Test suite for calculate_imbalance cross-zone comparison."""

    @pytest.fixture
    def calculator(self):
        """Create RiskCalculator instance with default config."""
        return RiskCalculator()

    def test_single_zone_returns_zero(self, calculator):
        """Test that single zone returns 0 imbalance (no comparison possible)."""
        all_zones = [
            {"zone_id": "zone_1", "avg_cpu_usage": 75.0}
        ]

        result = calculator.calculate_imbalance(all_zones)

        assert result == {"zone_1": 0.0}

    def test_identical_cpu_usage_returns_zero(self, calculator):
        """Test that identical CPU usage across all zones returns all 0."""
        all_zones = [
            {"zone_id": "zone_1", "avg_cpu_usage": 50.0},
            {"zone_id": "zone_2", "avg_cpu_usage": 50.0},
            {"zone_id": "zone_3", "avg_cpu_usage": 50.0},
        ]

        result = calculator.calculate_imbalance(all_zones)

        # All zones should have 0 imbalance (no deviation)
        assert result["zone_1"] == 0.0
        assert result["zone_2"] == 0.0
        assert result["zone_3"] == 0.0

    def test_extreme_outlier_zone(self, calculator):
        """Test that zone with extreme CPU usage gets high imbalance score."""
        all_zones = [
            {"zone_id": "zone_1", "avg_cpu_usage": 30.0},
            {"zone_id": "zone_2", "avg_cpu_usage": 35.0},
            {"zone_id": "zone_3", "avg_cpu_usage": 95.0},  # Extreme outlier
        ]

        result = calculator.calculate_imbalance(all_zones)

        # zone_3 should have significantly higher imbalance score
        assert result["zone_3"] > result["zone_1"]
        assert result["zone_3"] > result["zone_2"]
        # Outlier should have a notably high score
        assert result["zone_3"] > 50.0
        # All scores should be in valid range
        assert 0 <= result["zone_1"] <= 100
        assert 0 <= result["zone_2"] <= 100
        assert 0 <= result["zone_3"] <= 100

    def test_symmetric_distribution(self, calculator):
        """Test symmetric CPU distribution around median."""
        all_zones = [
            {"zone_id": "zone_1", "avg_cpu_usage": 30.0},
            {"zone_id": "zone_2", "avg_cpu_usage": 50.0},  # Median
            {"zone_id": "zone_3", "avg_cpu_usage": 70.0},
        ]

        result = calculator.calculate_imbalance(all_zones)

        # zone_2 (at median) should have 0 imbalance
        assert result["zone_2"] == 0.0
        # zone_1 and zone_3 should have equal imbalance (symmetric deviation)
        assert result["zone_1"] == result["zone_3"]
        # Both should be positive
        assert result["zone_1"] > 0
        assert result["zone_3"] > 0

    def test_missing_zone_id(self, calculator):
        """Test handling of zones without zone_id."""
        all_zones = [
            {"zone_id": "zone_1", "avg_cpu_usage": 50.0},
            {"avg_cpu_usage": 60.0},  # Missing zone_id
            {"zone_id": "zone_3", "avg_cpu_usage": 70.0},
        ]

        result = calculator.calculate_imbalance(all_zones)

        # Should only return results for zones with zone_id
        assert "zone_1" in result
        assert "zone_3" in result
        assert len(result) == 2

    def test_missing_cpu_usage(self, calculator):
        """Test that missing avg_cpu_usage is treated as 0."""
        all_zones = [
            {"zone_id": "zone_1", "avg_cpu_usage": 50.0},
            {"zone_id": "zone_2"},  # Missing avg_cpu_usage
            {"zone_id": "zone_3", "avg_cpu_usage": 60.0},
        ]

        result = calculator.calculate_imbalance(all_zones)

        # Should calculate for all zones, treating missing as 0
        assert len(result) == 3
        assert "zone_1" in result
        assert "zone_2" in result
        assert "zone_3" in result
        # All scores should be in valid range
        for score in result.values():
            assert 0 <= score <= 100

    def test_empty_list(self, calculator):
        """Test that empty zone list returns empty dict."""
        all_zones = []

        result = calculator.calculate_imbalance(all_zones)

        assert result == {}
