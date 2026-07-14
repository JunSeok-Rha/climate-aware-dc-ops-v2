"""Tests for StatusClassifier."""

import pytest

from cado.scoring.status_classifier import (
    StatusClassifier,
    score_to_band,
    imbalance_to_band,
)


class TestBandHelpers:
    """Test suite for band helper functions."""

    def test_score_to_band_low(self):
        """Test score_to_band with LOW band values."""
        assert score_to_band(0) == "LOW"
        assert score_to_band(15) == "LOW"
        assert score_to_band(29.9) == "LOW"

    def test_score_to_band_medium(self):
        """Test score_to_band with MEDIUM band values."""
        assert score_to_band(30) == "MEDIUM"
        assert score_to_band(40) == "MEDIUM"
        assert score_to_band(54.9) == "MEDIUM"

    def test_score_to_band_high(self):
        """Test score_to_band with HIGH band values."""
        assert score_to_band(55) == "HIGH"
        assert score_to_band(65) == "HIGH"
        assert score_to_band(74.9) == "HIGH"

    def test_score_to_band_extreme(self):
        """Test score_to_band with EXTREME band values."""
        assert score_to_band(75) == "EXTREME"
        assert score_to_band(85) == "EXTREME"
        assert score_to_band(100) == "EXTREME"

    def test_imbalance_to_band_none(self):
        """Test imbalance_to_band with NONE band values."""
        assert imbalance_to_band(0) == "NONE"
        assert imbalance_to_band(10) == "NONE"
        assert imbalance_to_band(19.9) == "NONE"

    def test_imbalance_to_band_moderate(self):
        """Test imbalance_to_band with MODERATE band values."""
        assert imbalance_to_band(20) == "MODERATE"
        assert imbalance_to_band(35) == "MODERATE"
        assert imbalance_to_band(49.9) == "MODERATE"

    def test_imbalance_to_band_severe(self):
        """Test imbalance_to_band with SEVERE band values."""
        assert imbalance_to_band(50) == "SEVERE"
        assert imbalance_to_band(75) == "SEVERE"
        assert imbalance_to_band(100) == "SEVERE"


class TestStatusClassifier:
    """Test suite for StatusClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create StatusClassifier instance."""
        return StatusClassifier()

    def test_rule_01_critical_heat_extreme_cool_high(self, classifier):
        """
        Rule 1: CRITICAL - heat=EXTREME AND cool>=HIGH.
        heat=80 (EXTREME), cool=60 (HIGH), imbalance=0 (NONE)
        """
        scores = {
            "heat_risk_score": 80.0,
            "cooling_stress_score": 60.0,
            "zone_imbalance_score": 0.0,
        }
        assert classifier.classify(scores) == "CRITICAL"

    def test_rule_02_critical_cool_extreme_heat_high(self, classifier):
        """
        Rule 2: CRITICAL - cool=EXTREME AND heat>=HIGH.
        heat=60 (HIGH), cool=80 (EXTREME), imbalance=0 (NONE)
        """
        scores = {
            "heat_risk_score": 60.0,
            "cooling_stress_score": 80.0,
            "zone_imbalance_score": 0.0,
        }
        assert classifier.classify(scores) == "CRITICAL"

    def test_rule_03_critical_both_high_imbalance_severe(self, classifier):
        """
        Rule 3: CRITICAL - heat>=HIGH AND cool>=HIGH AND imbalance=SEVERE.
        heat=60 (HIGH), cool=60 (HIGH), imbalance=55 (SEVERE)
        """
        scores = {
            "heat_risk_score": 60.0,
            "cooling_stress_score": 60.0,
            "zone_imbalance_score": 55.0,
        }
        assert classifier.classify(scores) == "CRITICAL"

    def test_rule_04_warning_heat_extreme_standalone(self, classifier):
        """
        Rule 4: WARNING - heat=EXTREME (standalone).
        heat=80 (EXTREME), cool=10 (LOW), imbalance=0 (NONE)
        Should not match rules 1-3.
        """
        scores = {
            "heat_risk_score": 80.0,
            "cooling_stress_score": 10.0,
            "zone_imbalance_score": 0.0,
        }
        assert classifier.classify(scores) == "WARNING"

    def test_rule_05_warning_cool_extreme_standalone(self, classifier):
        """
        Rule 5: WARNING - cool=EXTREME (standalone).
        heat=10 (LOW), cool=80 (EXTREME), imbalance=0 (NONE)
        Should not match rules 1-4.
        """
        scores = {
            "heat_risk_score": 10.0,
            "cooling_stress_score": 80.0,
            "zone_imbalance_score": 0.0,
        }
        assert classifier.classify(scores) == "WARNING"

    def test_rule_06_warning_both_high(self, classifier):
        """
        Rule 6: WARNING - heat>=HIGH AND cool>=HIGH.
        heat=60 (HIGH), cool=60 (HIGH), imbalance=10 (NONE - not SEVERE)
        Should not match rules 1-5 (rule 3 requires SEVERE imbalance).
        """
        scores = {
            "heat_risk_score": 60.0,
            "cooling_stress_score": 60.0,
            "zone_imbalance_score": 10.0,
        }
        assert classifier.classify(scores) == "WARNING"

    def test_rule_07_warning_imbalance_severe_standalone(self, classifier):
        """
        Rule 7: WARNING - imbalance=SEVERE (standalone).
        heat=10 (LOW), cool=10 (LOW), imbalance=55 (SEVERE)
        Should not match rules 1-6.
        """
        scores = {
            "heat_risk_score": 10.0,
            "cooling_stress_score": 10.0,
            "zone_imbalance_score": 55.0,
        }
        assert classifier.classify(scores) == "WARNING"

    def test_rule_08_elevated_heat_high_standalone(self, classifier):
        """
        Rule 8: ELEVATED - heat=HIGH (standalone).
        heat=60 (HIGH), cool=10 (LOW), imbalance=0 (NONE)
        Should not match rules 1-7.
        """
        scores = {
            "heat_risk_score": 60.0,
            "cooling_stress_score": 10.0,
            "zone_imbalance_score": 0.0,
        }
        assert classifier.classify(scores) == "ELEVATED"

    def test_rule_09_elevated_cool_high_standalone(self, classifier):
        """
        Rule 9: ELEVATED - cool=HIGH (standalone).
        heat=10 (LOW), cool=60 (HIGH), imbalance=0 (NONE)
        Should not match rules 1-8.
        """
        scores = {
            "heat_risk_score": 10.0,
            "cooling_stress_score": 60.0,
            "zone_imbalance_score": 0.0,
        }
        assert classifier.classify(scores) == "ELEVATED"

    def test_rule_10_elevated_both_medium(self, classifier):
        """
        Rule 10: ELEVATED - heat=MEDIUM AND cool=MEDIUM.
        heat=40 (MEDIUM), cool=40 (MEDIUM), imbalance=0 (NONE)
        Should not match rules 1-9.
        """
        scores = {
            "heat_risk_score": 40.0,
            "cooling_stress_score": 40.0,
            "zone_imbalance_score": 0.0,
        }
        assert classifier.classify(scores) == "ELEVATED"

    def test_rule_11_advisory_heat_medium_cool_low(self, classifier):
        """
        Rule 11: ADVISORY - heat=MEDIUM AND cool=LOW AND imbalance<SEVERE.
        heat=40 (MEDIUM), cool=10 (LOW), imbalance=10 (NONE - not SEVERE)
        Should not match rules 1-10.
        """
        scores = {
            "heat_risk_score": 40.0,
            "cooling_stress_score": 10.0,
            "zone_imbalance_score": 10.0,
        }
        assert classifier.classify(scores) == "ADVISORY"

    def test_rule_12_advisory_cool_medium_heat_low(self, classifier):
        """
        Rule 12: ADVISORY - cool=MEDIUM AND heat=LOW AND imbalance<SEVERE.
        heat=10 (LOW), cool=40 (MEDIUM), imbalance=10 (NONE - not SEVERE)
        Should not match rules 1-11.
        """
        scores = {
            "heat_risk_score": 10.0,
            "cooling_stress_score": 40.0,
            "zone_imbalance_score": 10.0,
        }
        assert classifier.classify(scores) == "ADVISORY"

    def test_rule_13_normal_fallback(self, classifier):
        """
        Rule 13: NORMAL - default fallback.
        heat=10 (LOW), cool=10 (LOW), imbalance=10 (NONE)
        Should not match any rules 1-12.
        """
        scores = {
            "heat_risk_score": 10.0,
            "cooling_stress_score": 10.0,
            "zone_imbalance_score": 10.0,
        }
        assert classifier.classify(scores) == "NORMAL"
