"""Zone status API routes.

zone_aggregated_metrics 테이블(Aggregator가 RPC로 채움)을 RiskCalculator/
StatusClassifier로 가공해 zone별 상태를 노출하는 통합 레이어.
"""

import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from cado.db.supabase_client import get_supabase_client
from cado.scoring.risk_calculator import RiskCalculator
from cado.scoring.status_classifier import StatusClassifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/zones", tags=["zones"])

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _load_zone_ids() -> list[str]:
    """config.yaml의 zones 목록(zone_1~zone_10)을 로드한다."""
    with open(_CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    return config.get("zones") or []


def _fetch_latest_zone_metrics() -> dict[str, dict]:
    """zone_aggregated_metrics에서 zone_id별 최신 row만 골라 반환한다."""
    client = get_supabase_client()
    response = (
        client.table("zone_aggregated_metrics")
        .select("*")
        .order("aggregated_at", desc=True)
        .execute()
    )

    latest: dict[str, dict] = {}
    for row in response.data or []:
        zone_id = row.get("zone_id")
        if zone_id and zone_id not in latest:
            latest[zone_id] = row
    return latest


def _compute_zone_scores(latest_metrics: dict[str, dict]) -> dict[str, dict]:
    """데이터가 있는 zone에 한해 risk score + status_level을 계산한다."""
    calculator = RiskCalculator()
    classifier = StatusClassifier()

    all_zones = [
        {"zone_id": zone_id, "avg_cpu_usage": metrics.get("avg_cpu_usage")}
        for zone_id, metrics in latest_metrics.items()
    ]
    imbalance_scores = calculator.calculate_imbalance(all_zones)

    results: dict[str, dict] = {}
    for zone_id, metrics in latest_metrics.items():
        scores = calculator.calculate(
            metrics, zone_imbalance_score=imbalance_scores.get(zone_id, 0.0)
        )
        scores["status_level"] = classifier.classify(scores)
        results[zone_id] = scores
    return results


@router.get("")
def list_zones():
    """10개 zone 목록과 각 zone의 최신 status_level을 반환한다.

    아직 집계 데이터가 없는 zone은 status_level을 null로 표시한다.
    """
    zone_ids = _load_zone_ids()
    latest_metrics = _fetch_latest_zone_metrics()
    scores = _compute_zone_scores(latest_metrics)

    return [
        {
            "zone_id": zone_id,
            "status_level": scores.get(zone_id, {}).get("status_level"),
        }
        for zone_id in zone_ids
    ]


@router.get("/{zone_id}/status")
def get_zone_status(zone_id: str):
    """단일 zone의 heat_risk_score, cooling_stress_score, zone_imbalance_score,
    status_level을 반환한다.

    zone_id가 알려진 10개 zone에 속하지 않거나, 유효한 zone이지만 아직
    집계 데이터가 없는 경우 모두 404를 반환한다.
    """
    zone_ids = _load_zone_ids()
    if zone_id not in zone_ids:
        raise HTTPException(status_code=404, detail=f"Unknown zone_id: {zone_id}")

    latest_metrics = _fetch_latest_zone_metrics()
    if zone_id not in latest_metrics:
        raise HTTPException(
            status_code=404, detail=f"No aggregated metrics found for zone: {zone_id}"
        )

    scores = _compute_zone_scores(latest_metrics)
    zone_scores = scores[zone_id]

    return {
        "zone_id": zone_id,
        "heat_risk_score": zone_scores["heat_risk_score"],
        "cooling_stress_score": zone_scores["cooling_stress_score"],
        "zone_imbalance_score": zone_scores["zone_imbalance_score"],
        "status_level": zone_scores["status_level"],
    }
