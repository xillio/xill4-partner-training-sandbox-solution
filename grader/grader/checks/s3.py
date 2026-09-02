"""S3 checks -- for scenarios whose target is object storage (MinIO locally, S3 in Azure/AWS).

boto3 is imported lazily so the grader stays usable, and its tests stay fast, in
scenarios that never touch object storage.
"""

from __future__ import annotations

from typing import Any

from grader.checks import Outcome, check, compare_number
from grader.context import Context

_MAX_REPORTED = 10


def _client(ctx: Context):
    import boto3  # noqa: PLC0415 -- optional dependency, only needed by S3 scenarios

    return boto3.client(
        "s3",
        endpoint_url=ctx.vars.get("S3_ENDPOINT") or None,
        aws_access_key_id=ctx.vars.get("S3_ACCESS_KEY") or None,
        aws_secret_access_key=ctx.vars.get("S3_SECRET_KEY") or None,
        region_name=ctx.vars.get("S3_REGION", "us-east-1"),
    )


def _list_keys(ctx: Context, bucket: str, prefix: str) -> list[str]:
    paginator = _client(ctx).get_paginator("list_objects_v2")
    return [
        item["Key"]
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix)
        for item in page.get("Contents", [])
    ]


@check("s3.object_count")
def object_count(params: dict[str, Any], ctx: Context) -> Outcome:
    """Count objects under a prefix. Params: bucket, prefix, equals|min|max."""
    bucket = ctx.expand(params["bucket"])
    prefix = ctx.expand(params.get("prefix", ""))
    try:
        keys = _list_keys(ctx, bucket, prefix)
    except ImportError:
        return Outcome(False, "boto3 is not installed in the grader image", {"bucket": bucket})
    except Exception as exc:
        return Outcome(False, f"could not list s3://{bucket}/{prefix}: {exc}", {"bucket": bucket})

    outcome = compare_number(len(keys), params, f"objects under s3://{bucket}/{prefix}", ctx)
    outcome.evidence["sample"] = keys[:_MAX_REPORTED]
    return outcome
