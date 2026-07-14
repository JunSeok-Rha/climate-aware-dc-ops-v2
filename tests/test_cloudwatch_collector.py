"""Tests for CloudWatch collector."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from cado.collectors.cloudwatch_collector import CloudWatchCollector


@pytest.fixture
def mock_settings():
    """Mock settings with test AWS credentials and instance ID."""
    with patch("cado.collectors.cloudwatch_collector.settings") as mock:
        mock.aws_access_key_id = "test_access_key"
        mock.aws_secret_access_key = "test_secret_key"
        mock.aws_region = "us-east-1"
        mock.cloudwatch_target_instance_id = "i-test123456"
        yield mock


@pytest.mark.asyncio
async def test_collect_success(mock_settings):
    """Test successful metric collection from CloudWatch."""
    with mock_aws():
        # Create CloudWatch client and put some test metrics
        client = boto3.client("cloudwatch", region_name="us-east-1")
        namespace = "AWS/EC2"
        instance_id = "i-test123456"

        # Put test metric data
        now = datetime.now(timezone.utc)
        for i in range(3):
            timestamp = now - timedelta(minutes=i * 5)
            client.put_metric_data(
                Namespace=namespace,
                MetricData=[
                    {
                        "MetricName": "CPUUtilization",
                        "Value": 50.0 + i,
                        "Timestamp": timestamp,
                        "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                    },
                    {
                        "MetricName": "MemoryUtilization",
                        "Value": 60.0 + i,
                        "Timestamp": timestamp,
                        "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                    },
                ],
            )

        # Collect metrics
        collector = CloudWatchCollector()
        results = await collector.collect()

        # Verify results
        assert isinstance(results, list)
        assert len(results) > 0

        # Check that we have results for both metrics
        cpu_results = [r for r in results if r["metric_name"] == "CPUUtilization"]
        memory_results = [r for r in results if r["metric_name"] == "MemoryUtilization"]

        assert len(cpu_results) > 0, "Should have CPUUtilization data points"
        assert len(memory_results) > 0, "Should have MemoryUtilization data points"

        # Verify data structure
        for result in results:
            assert "instance_id" in result
            assert "metric_name" in result
            assert "value" in result
            assert "observed_at" in result

            assert result["instance_id"] == instance_id
            assert result["metric_name"] in ["CPUUtilization", "MemoryUtilization"]
            assert isinstance(result["value"], float)
            assert isinstance(result["observed_at"], datetime)


@pytest.mark.asyncio
async def test_collect_with_retry_failure(mock_settings, caplog):
    """Test that collector retries on failure and eventually skips the metric."""
    caplog.set_level(logging.WARNING)

    collector = CloudWatchCollector()

    # Mock the boto3 client to raise errors
    with patch.object(collector, "_create_client") as mock_create_client:
        mock_client = MagicMock()
        mock_client.get_metric_data.side_effect = ClientError(
            {"Error": {"Code": "InternalServiceError", "Message": "Service unavailable"}},
            "get_metric_data",
        )
        mock_create_client.return_value = mock_client

        # Collect metrics (should fail and skip after retries)
        results = await collector.collect()

        # Should return empty list after all retries fail
        assert results == []

        # Verify retry attempts were made (3 attempts per metric * 2 metrics)
        assert mock_client.get_metric_data.call_count == 6  # 3 retries * 2 metrics

        # Check warning logs
        warning_logs = [
            record.message for record in caplog.records if record.levelname == "WARNING"
        ]
        assert len(warning_logs) > 0
        assert any("Skipping" in log for log in warning_logs)


@pytest.mark.asyncio
async def test_collect_no_instance_id():
    """Test that collector handles missing instance_id gracefully."""
    with mock_aws(), patch("cado.collectors.cloudwatch_collector.settings") as mock:
        mock.aws_access_key_id = "test_access_key"
        mock.aws_secret_access_key = "test_secret_key"
        mock.aws_region = "us-east-1"
        mock.cloudwatch_target_instance_id = None

        collector = CloudWatchCollector()
        results = await collector.collect()

        # Should return empty list when instance_id is not configured
        assert results == []


@pytest.mark.asyncio
async def test_collect_no_data_points(mock_settings):
    """Test collector behavior when CloudWatch returns no data points."""
    with mock_aws():
        # Don't put any metrics, so CloudWatch will return empty results
        collector = CloudWatchCollector()
        results = await collector.collect()

        # Should return empty list when no data is available
        assert results == []
