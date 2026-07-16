"""
Real AWS integration test for CloudWatchCollector.

This test requires valid AWS credentials in .env and a running EC2 instance.
It is marked with pytest.mark.integration and excluded from default test runs.

Three distinct failure modes are diagnosed:
1. AWS 자격증명 문제 (credentials problem) - fail immediately
2. 인스턴스 문제 (instance problem) - fail immediately
3. 메트릭 아직 없음 (no metrics yet) - skip as expected transient state
"""

from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from cado.collectors.cloudwatch_collector import CloudWatchCollector
from cado.config import settings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cloudwatch_collector_real_aws():
    """Integration test against real AWS CloudWatch API (no mocking)."""

    # 1. Check that target instance is configured
    if not settings.cloudwatch_target_instance_id:
        pytest.skip(
            "CLOUDWATCH_TARGET_INSTANCE_ID not set in .env - "
            "cannot run CloudWatch integration test"
        )

    target_instance = settings.cloudwatch_target_instance_id

    # 2. Verify AWS credentials are valid
    try:
        sts = boto3.client(
            "sts",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        caller_identity = sts.get_caller_identity()
        print(f"✓ AWS credentials valid (Account: {caller_identity['Account']})")
    except NoCredentialsError as e:
        pytest.fail(
            f"AWS 자격증명 문제 (credentials problem): "
            f"No AWS credentials found - {e}"
        )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code in {
            "InvalidClientTokenId",
            "AuthFailure",
            "AccessDenied",
            "SignatureDoesNotMatch",
        }:
            pytest.fail(
                f"AWS 자격증명 문제 (credentials problem): "
                f"Invalid or unauthorized credentials - {error_code}: {e}"
            )
        raise  # Re-raise if it's some other ClientError

    # 3. Verify target EC2 instance exists
    try:
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        response = ec2.describe_instances(InstanceIds=[target_instance])

        # Verify we got exactly one reservation with at least one instance
        reservations = response.get("Reservations", [])
        if not reservations or not reservations[0].get("Instances"):
            pytest.fail(
                f"인스턴스 문제 (instance problem): "
                f"Instance {target_instance} not found in describe_instances response"
            )

        instance_state = reservations[0]["Instances"][0]["State"]["Name"]
        print(f"✓ Target instance {target_instance} exists (state: {instance_state})")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code in {"InvalidInstanceID.NotFound", "InvalidInstanceID.Malformed"}:
            pytest.fail(
                f"인스턴스 문제 (instance problem): "
                f"Instance {target_instance} not found or invalid - {error_code}: {e}"
            )
        raise  # Re-raise if it's some other ClientError

    # 4. Call the collector
    collector = CloudWatchCollector()
    results = await collector.collect()

    # 5. Handle empty results as expected transient state
    if not results:
        pytest.skip(
            f"메트릭 아직 없음 (no metrics yet): CloudWatch returned no datapoints "
            f"for instance {target_instance}. This is expected for freshly created "
            f"or low-traffic instances as CloudWatch can take several minutes to "
            f"aggregate and expose metrics. This is not a collector bug."
        )

    # 6. Validate schema of returned data
    print(f"\n✓ Collected {len(results)} datapoint(s) from CloudWatch")

    cpu_count = 0
    mem_count = 0

    for i, datapoint in enumerate(results):
        # Check required keys
        assert "instance_id" in datapoint, f"Datapoint {i} missing 'instance_id'"
        assert "metric_name" in datapoint, f"Datapoint {i} missing 'metric_name'"
        assert "value" in datapoint, f"Datapoint {i} missing 'value'"
        assert "observed_at" in datapoint, f"Datapoint {i} missing 'observed_at'"

        # Validate instance_id matches configured target
        assert datapoint["instance_id"] == target_instance, (
            f"Datapoint {i} instance_id mismatch: "
            f"expected {target_instance}, got {datapoint['instance_id']}"
        )

        # Validate metric_name is one of the expected values
        metric_name = datapoint["metric_name"]
        assert metric_name in {"CPUUtilization", "MemoryUtilization"}, (
            f"Datapoint {i} unexpected metric_name: {metric_name}"
        )

        # Count metrics by type
        if metric_name == "CPUUtilization":
            cpu_count += 1
        else:
            mem_count += 1

        # Validate value is numeric
        value = datapoint["value"]
        assert isinstance(value, (int, float)), (
            f"Datapoint {i} value not numeric: {type(value)}"
        )

        # Validate observed_at is a UTC-aware datetime
        observed_at = datapoint["observed_at"]
        assert isinstance(observed_at, datetime), (
            f"Datapoint {i} observed_at not a datetime: {type(observed_at)}"
        )
        assert observed_at.tzinfo is not None, (
            f"Datapoint {i} observed_at is not timezone-aware"
        )
        assert observed_at.tzinfo.utcoffset(observed_at) is not None, (
            f"Datapoint {i} observed_at does not have UTC offset"
        )

    print(f"  - CPUUtilization: {cpu_count} datapoint(s)")
    print(f"  - MemoryUtilization: {mem_count} datapoint(s)")
    print(f"✓ All datapoints have valid schema")
