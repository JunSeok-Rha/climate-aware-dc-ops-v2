"""Status Classification module for mapping risk scores to operational status levels."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class StatusClassificationError(Exception):
    """Raised when status classification fails."""

    pass


def score_to_band(score: float) -> str:
    """
    Map a risk score to its band classification.

    Args:
        score: Risk score value (0-100)

    Returns:
        Band classification: "LOW", "MEDIUM", "HIGH", or "EXTREME"
    """
    if score < 30:
        return "LOW"
    elif score < 55:
        return "MEDIUM"
    elif score < 75:
        return "HIGH"
    else:
        return "EXTREME"


def imbalance_to_band(score: float) -> str:
    """
    Map an imbalance score to its band classification.

    Args:
        score: Imbalance score value (0-100)

    Returns:
        Band classification: "NONE", "MODERATE", or "SEVERE"
    """
    if score < 20:
        return "NONE"
    elif score < 50:
        return "MODERATE"
    else:
        return "SEVERE"


class StatusClassifier:
    """Classifies risk scores into operational status levels."""

    def classify(self, scores: Dict[str, float]) -> str:
        """
        Classify risk scores into an operational status level.

        Args:
            scores: Dict containing risk scores with keys:
                - heat_risk_score: float (0-100)
                - cooling_stress_score: float (0-100)
                - zone_imbalance_score: float (0-100)

        Returns:
            Status level: One of "NORMAL", "ADVISORY", "ELEVATED", "WARNING", "CRITICAL"

        Note:
            Classification follows a priority-ordered rule set (CRITICAL → WARNING →
            ELEVATED → ADVISORY → NORMAL). The first matching rule determines the status.
        """
        # Extract scores
        heat_score = scores["heat_risk_score"]
        cool_score = scores["cooling_stress_score"]
        imbalance_score = scores["zone_imbalance_score"]

        # Map scores to bands
        heat_band = score_to_band(heat_score)
        cool_band = score_to_band(cool_score)
        imbalance_band = imbalance_to_band(imbalance_score)

        # Classification rules (priority-ordered, top to bottom)

        # Rule 1: CRITICAL - heat=EXTREME AND cool>=HIGH
        if heat_band == "EXTREME" and cool_band in ["HIGH", "EXTREME"]:
            return "CRITICAL"

        # Rule 2: CRITICAL - cool=EXTREME AND heat>=HIGH
        if cool_band == "EXTREME" and heat_band in ["HIGH", "EXTREME"]:
            return "CRITICAL"

        # Rule 3: CRITICAL - heat>=HIGH AND cool>=HIGH AND imbalance=SEVERE
        if heat_band in ["HIGH", "EXTREME"] and cool_band in ["HIGH", "EXTREME"] and imbalance_band == "SEVERE":
            return "CRITICAL"

        # Rule 4: WARNING - heat=EXTREME (standalone)
        if heat_band == "EXTREME":
            return "WARNING"

        # Rule 5: WARNING - cool=EXTREME (standalone)
        if cool_band == "EXTREME":
            return "WARNING"

        # Rule 6: WARNING - heat>=HIGH AND cool>=HIGH
        if heat_band in ["HIGH", "EXTREME"] and cool_band in ["HIGH", "EXTREME"]:
            return "WARNING"

        # Rule 7: WARNING - imbalance=SEVERE (standalone)
        if imbalance_band == "SEVERE":
            return "WARNING"

        # Rule 8: ELEVATED - heat=HIGH (standalone)
        if heat_band == "HIGH":
            return "ELEVATED"

        # Rule 9: ELEVATED - cool=HIGH (standalone)
        if cool_band == "HIGH":
            return "ELEVATED"

        # Rule 10: ELEVATED - heat=MEDIUM AND cool=MEDIUM
        if heat_band == "MEDIUM" and cool_band == "MEDIUM":
            return "ELEVATED"

        # Rule 11: ADVISORY - heat=MEDIUM AND cool=LOW AND imbalance<SEVERE
        if heat_band == "MEDIUM" and cool_band == "LOW" and imbalance_band != "SEVERE":
            return "ADVISORY"

        # Rule 12: ADVISORY - cool=MEDIUM AND heat=LOW AND imbalance<SEVERE
        if cool_band == "MEDIUM" and heat_band == "LOW" and imbalance_band != "SEVERE":
            return "ADVISORY"

        # Rule 13: NORMAL - default fallback
        return "NORMAL"
