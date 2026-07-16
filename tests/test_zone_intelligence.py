"""Tests for Zone Intelligence Agent.

Mock tests run by default with: uv run pytest tests/test_zone_intelligence.py -v
Integration tests (actual API calls) are marked with @pytest.mark.integration
and excluded by default via pyproject.toml's addopts = "-m 'not integration'".

To run integration tests explicitly:
uv run pytest tests/test_zone_intelligence.py -v -m integration -o addopts=""
"""

from unittest.mock import MagicMock, patch

import pytest

from cado.agents.zone_intelligence import analyze


# Mock unit tests
class TestZoneIntelligenceMock:
    """Mock-based unit tests that don't call actual Anthropic API."""

    def test_analyze_normal_response(self):
        """Test that analyze correctly parses a normal API response."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Zone 1은 정상 범위 내에서 운영 중이며, 모든 지표가 안정적입니다.")]

        with patch("cado.agents.zone_intelligence.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            recent_status = [
                {
                    "zone_id": "zone_1",
                    "evaluated_at": "2026-07-16T00:00:00Z",
                    "heat_risk_score": 25.0,
                    "cooling_stress_score": 30.0,
                    "zone_imbalance_score": 10.0,
                    "status_level": "NORMAL",
                }
            ]

            result = analyze("zone_1", recent_status)

            assert result == "Zone 1은 정상 범위 내에서 운영 중이며, 모든 지표가 안정적입니다."
            mock_client.messages.create.assert_called_once()

            # Verify model parameter
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-sonnet-5"
            assert call_kwargs["max_tokens"] == 150

    def test_analyze_elevated_status(self):
        """Test analyze with ELEVATED status level."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Zone 2는 냉각 부하가 증가하는 추세를 보이고 있습니다.")]

        with patch("cado.agents.zone_intelligence.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            recent_status = [
                {
                    "zone_id": "zone_2",
                    "evaluated_at": "2026-07-16T00:00:00Z",
                    "heat_risk_score": 45.0,
                    "cooling_stress_score": 60.0,
                    "zone_imbalance_score": 35.0,
                    "status_level": "ELEVATED",
                }
            ]

            result = analyze("zone_2", recent_status)

            assert result == "Zone 2는 냉각 부하가 증가하는 추세를 보이고 있습니다."

    def test_analyze_multiple_status_records(self):
        """Test analyze with multiple recent status records."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Zone 3은 지난 3회 측정 동안 일관되게 높은 부하를 기록했습니다.")]

        with patch("cado.agents.zone_intelligence.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            recent_status = [
                {
                    "zone_id": "zone_3",
                    "evaluated_at": "2026-07-16T02:00:00Z",
                    "heat_risk_score": 70.0,
                    "cooling_stress_score": 75.0,
                    "zone_imbalance_score": 50.0,
                    "status_level": "WARNING",
                },
                {
                    "zone_id": "zone_3",
                    "evaluated_at": "2026-07-16T01:00:00Z",
                    "heat_risk_score": 68.0,
                    "cooling_stress_score": 72.0,
                    "zone_imbalance_score": 48.0,
                    "status_level": "WARNING",
                },
                {
                    "zone_id": "zone_3",
                    "evaluated_at": "2026-07-16T00:00:00Z",
                    "heat_risk_score": 65.0,
                    "cooling_stress_score": 70.0,
                    "zone_imbalance_score": 45.0,
                    "status_level": "ELEVATED",
                },
            ]

            result = analyze("zone_3", recent_status)

            assert result == "Zone 3은 지난 3회 측정 동안 일관되게 높은 부하를 기록했습니다."
            # Verify all three status records were included in the prompt
            call_kwargs = mock_client.messages.create.call_args[1]
            prompt = call_kwargs["messages"][0]["content"]
            assert "WARNING" in prompt
            assert "ELEVATED" in prompt

    def test_analyze_api_failure_returns_fallback(self):
        """Test that API failures return the fallback string."""
        with patch("cado.agents.zone_intelligence.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client

            recent_status = [
                {
                    "zone_id": "zone_4",
                    "evaluated_at": "2026-07-16T00:00:00Z",
                    "heat_risk_score": 50.0,
                    "cooling_stress_score": 50.0,
                    "zone_imbalance_score": 50.0,
                    "status_level": "ELEVATED",
                }
            ]

            result = analyze("zone_4", recent_status)

            assert result == "분석 일시 불가"

    def test_analyze_empty_status_returns_fallback(self):
        """Test that empty status list returns fallback without API call."""
        with patch("cado.agents.zone_intelligence.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            result = analyze("zone_5", [])

            assert result == "분석 일시 불가"
            # Should not call API if status list is empty
            mock_client.messages.create.assert_not_called()

    def test_analyze_empty_response_content(self):
        """Test handling of empty response content from API."""
        mock_response = MagicMock()
        mock_response.content = []

        with patch("cado.agents.zone_intelligence.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            recent_status = [
                {
                    "zone_id": "zone_6",
                    "evaluated_at": "2026-07-16T00:00:00Z",
                    "heat_risk_score": 40.0,
                    "cooling_stress_score": 40.0,
                    "zone_imbalance_score": 20.0,
                    "status_level": "NORMAL",
                }
            ]

            result = analyze("zone_6", recent_status)

            assert result == "분석 일시 불가"


# Integration tests (actual API calls)
@pytest.mark.integration
class TestZoneIntelligenceIntegration:
    """Integration tests that make actual Anthropic API calls.

    These are excluded from default test runs.
    Run explicitly with: uv run pytest tests/test_zone_intelligence.py -v -m integration -o addopts=""
    """

    def test_analyze_real_api_call(self):
        """Test analyze with a real API call to Anthropic."""
        recent_status = [
            {
                "zone_id": "zone_1",
                "evaluated_at": "2026-07-16T00:00:00Z",
                "heat_risk_score": 25.0,
                "cooling_stress_score": 30.0,
                "zone_imbalance_score": 10.0,
                "status_level": "NORMAL",
            }
        ]

        result = analyze("zone_1", recent_status)

        # Should return actual text analysis, not the fallback
        assert result != "분석 일시 불가"
        assert isinstance(result, str)
        assert len(result) > 0

    def test_analyze_critical_status_real(self):
        """Test analyze with CRITICAL status using real API."""
        recent_status = [
            {
                "zone_id": "zone_2",
                "evaluated_at": "2026-07-16T00:00:00Z",
                "heat_risk_score": 85.0,
                "cooling_stress_score": 90.0,
                "zone_imbalance_score": 75.0,
                "status_level": "CRITICAL",
            }
        ]

        result = analyze("zone_2", recent_status)

        assert result != "분석 일시 불가"
        assert isinstance(result, str)
        assert len(result) > 0
