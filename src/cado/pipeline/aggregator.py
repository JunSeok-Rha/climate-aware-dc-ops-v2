"""Aggregator module for aggregating zone metrics via Supabase RPC."""

import logging

from cado.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class AggregationError(Exception):
    """Raised when zone metrics aggregation fails."""

    pass


class Aggregator:
    """Aggregates raw metrics into zone-level hourly metrics via Supabase RPC."""

    def __init__(self):
        """Initialize Aggregator with Supabase client."""
        self.client = get_supabase_client()

    def aggregate(self) -> None:
        """
        Aggregate raw metrics into zone_aggregated_metrics table.

        Calls the Supabase RPC function 'aggregate_zone_metrics' which performs
        hourly GROUP BY aggregation and inserts results into zone_aggregated_metrics.

        Raises:
            AggregationError: If the RPC call fails or returns an error response.
        """
        try:
            logger.info("Starting zone metrics aggregation via RPC")
            response = self.client.rpc("aggregate_zone_metrics").execute()

            # Check for errors in response
            if hasattr(response, "error") and response.error is not None:
                raise AggregationError(
                    f"Supabase RPC 'aggregate_zone_metrics' failed: {response.error}"
                )

            logger.info("Zone metrics aggregation completed successfully")

        except Exception as e:
            logger.error(f"Failed to aggregate zone metrics: {e}")
            raise AggregationError(f"Aggregation failed: {e}") from e
