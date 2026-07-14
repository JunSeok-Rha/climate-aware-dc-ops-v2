"""CloudWatch Collector module for fetching EC2 metrics."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

from cado.config import settings

logger = logging.getLogger(__name__)


class CloudWatchCollector:
    """Collects EC2 metrics from AWS CloudWatch."""

    def __init__(self):
        """Initialize CloudWatch collector with AWS credentials from settings."""
        self._aws_access_key_id = settings.aws_access_key_id
        self._aws_secret_access_key = settings.aws_secret_access_key
        self._aws_region = settings.aws_region
        self._instance_id = settings.cloudwatch_target_instance_id

        if not self._instance_id:
            logger.warning(
                "cloudwatch_target_instance_id is not set in settings. "
                "Collector will not be able to fetch metrics."
            )

        self._metrics_to_collect = ["CPUUtilization", "MemoryUtilization"]
        self._max_retries = 3
        self._period = 300  # 5 minutes in seconds

    def _create_client(self):
        """Create a boto3 CloudWatch client."""
        return boto3.client(
            "cloudwatch",
            aws_access_key_id=self._aws_access_key_id,
            aws_secret_access_key=self._aws_secret_access_key,
            region_name=self._aws_region,
        )

    async def _fetch_metric_with_retry(
        self, metric_name: str, client: Any
    ) -> List[Dict[str, Any]]:
        """
        Fetch a single metric with retry logic.

        Args:
            metric_name: Name of the CloudWatch metric (e.g., "CPUUtilization")
            client: boto3 CloudWatch client

        Returns:
            List of metric data points as dicts with instance_id, metric_name, value, observed_at
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=10)  # Look back 10 minutes

        for attempt in range(self._max_retries):
            try:
                logger.debug(
                    f"Fetching {metric_name} for instance {self._instance_id} "
                    f"(attempt {attempt + 1}/{self._max_retries})"
                )

                # Run boto3 call in thread pool to avoid blocking
                response = await asyncio.to_thread(
                    client.get_metric_data,
                    MetricDataQueries=[
                        {
                            "Id": "m1",
                            "MetricStat": {
                                "Metric": {
                                    "Namespace": "AWS/EC2",
                                    "MetricName": metric_name,
                                    "Dimensions": [
                                        {"Name": "InstanceId", "Value": self._instance_id}
                                    ],
                                },
                                "Period": self._period,
                                "Stat": "Average",
                            },
                        }
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                )

                results = []
                for metric_data_result in response.get("MetricDataResults", []):
                    timestamps = metric_data_result.get("Timestamps", [])
                    values = metric_data_result.get("Values", [])

                    for timestamp, value in zip(timestamps, values):
                        results.append(
                            {
                                "instance_id": self._instance_id,
                                "metric_name": metric_name,
                                "value": float(value),
                                "observed_at": timestamp,
                            }
                        )

                logger.info(
                    f"Successfully fetched {len(results)} data points for {metric_name}"
                )
                return results

            except ClientError as e:
                logger.warning(
                    f"Failed to fetch {metric_name} on attempt {attempt + 1}: {e}"
                )
                if attempt < self._max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.warning(
                        f"Failed to fetch {metric_name} after {self._max_retries} attempts. Skipping."
                    )
                    return []
            except Exception as e:
                logger.error(f"Unexpected error fetching {metric_name}: {e}")
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.warning(
                        f"Failed to fetch {metric_name} after {self._max_retries} attempts due to unexpected error. Skipping."
                    )
                    return []

        return []

    async def collect(self) -> List[Dict[str, Any]]:
        """
        Collect metrics from CloudWatch.

        Returns:
            List of raw_metrics rows as dicts with keys:
            - instance_id: str
            - metric_name: str
            - value: float
            - observed_at: datetime

        Note:
            If metrics fail to fetch after retries, they are skipped with a warning log.
            This method will not raise exceptions for individual metric failures.
        """
        if not self._instance_id:
            logger.error("Cannot collect metrics: instance_id not configured")
            return []

        logger.info(f"Starting metric collection for instance {self._instance_id}")

        client = self._create_client()
        all_results = []

        # Collect all metrics concurrently
        tasks = [
            self._fetch_metric_with_retry(metric_name, client)
            for metric_name in self._metrics_to_collect
        ]

        results_list = await asyncio.gather(*tasks)

        for results in results_list:
            all_results.extend(results)

        logger.info(
            f"Metric collection complete. Total data points collected: {len(all_results)}"
        )
        return all_results
