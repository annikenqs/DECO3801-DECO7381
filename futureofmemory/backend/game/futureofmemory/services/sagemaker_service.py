import os, json, time, uuid, typing, boto3, botocore
from urllib.parse import urlparse

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
ENDPOINT_NAME = os.getenv("SM_ENDPOINT_NAME", "neuro-rag-async")
BUCKET = os.getenv("SM_S3_BUCKET", "")
INPUT_PREFIX = os.getenv("SM_INPUT_PREFIX", f"async-inputs/{ENDPOINT_NAME}")
OUTPUT_PREFIX = os.getenv("SM_OUTPUT_PREFIX", f"async-outputs/{ENDPOINT_NAME}")
TIMEOUT_S = int(os.getenv("SM_TIMEOUT_SECONDS", "420"))

_boto = boto3.Session(region_name=AWS_REGION)
_s3 = _boto.client("s3")
_rt = _boto.client("sagemaker-runtime")
_sm = _boto.client("sagemaker") 

def _default_bucket():
    acct = _sts.get_caller_identity()["Account"]
    return f"sagemaker-{AWS_REGION}-{acct}"

def _ensure_bucket():
    return BUCKET or _default_bucket()

def invoke_async_tgi(
    prompt: str,
    max_new_tokens: int = 200,
    temperature: float = 0.7,
    extra_params: typing.Optional[dict] = None,
    timeout_s: int = TIMEOUT_S,
):
    """Invoke SageMaker async TGI endpoint and return text."""
    req = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            **(extra_params or {}),
        },
    }

    bucket = _ensure_bucket()
    rid = str(uuid.uuid4())
    in_key = f"{INPUT_PREFIX}/{rid}.json"

    _s3.put_object(
        Bucket=bucket,
        Key=in_key,
        Body=json.dumps(req).encode("utf-8"),
        ContentType="application/json",
    )

    resp = _rt.invoke_endpoint_async(
        EndpointName=ENDPOINT_NAME,
        InputLocation=f"s3://{bucket}/{in_key}",
        ContentType="application/json",
    )

    out_uri = resp["OutputLocation"]
    _, _, rest = out_uri.partition("s3://")
    out_bucket, _, out_key = rest.partition("/")

    t0 = time.time()
    backoff = 1.0
    while True:
        try:
            obj = _s3.get_object(Bucket=out_bucket, Key=out_key)
            data = json.loads(obj["Body"].read())
            if isinstance(data, list) and data and "generated_text" in data[0]:
                return data[0]["generated_text"]
            return data
        except _s3.exceptions.NoSuchKey:
            pass
        except botocore.exceptions.ClientError as e:
            if e.response.get("Error", {}).get("Code") != "NoSuchKey":
                raise
        if time.time() - t0 > timeout_s:
            raise TimeoutError(f"Result not ready after {timeout_s}s: {out_uri}")
        time.sleep(backoff)
        backoff = min(backoff * 1.5, 4.0)

def start_async_job(prompt: str,
                    max_new_tokens: int = 200,
                    temperature: float = 0.7,
                    extra_params: typing.Optional[dict] = None) -> str:
    """Return the OutputLocation immediately (do not block)."""
    req = {"inputs": prompt, "parameters": {
        "max_new_tokens": max_new_tokens,
        "temperature": temperature, **(extra_params or {})
    }}
    rid = str(uuid.uuid4())
    in_key = f"{INPUT_PREFIX}/{rid}.json"

    bucket = BUCKET or _default_bucket()
    _s3.put_object(
        Bucket=bucket, Key=in_key,
        Body=json.dumps(req).encode("utf-8"),
        ContentType="application/json",
    )
    resp = _rt.invoke_endpoint_async(
        EndpointName=ENDPOINT_NAME,
        InputLocation=f"s3://{bucket}/{in_key}",
        ContentType="application/json",
        InferenceId=rid,
    )
    return resp["OutputLocation"]

def _parse_s3(uri: str):
    p = urlparse(uri)
    return p.netloc, p.path.lstrip("/")

def _failure_bucket_prefix(endpoint_name: str):
    d = _sm.describe_endpoint(EndpointName=endpoint_name)
    out = (d.get("AsyncInferenceConfig") or {}).get("OutputConfig") or {}
    failure_uri = out.get("S3FailurePath")
    if not failure_uri:
        return None, None
    b, k = _parse_s3(failure_uri)
    return b, k.rstrip("/")

def poll_async_output(output_location: str, timeout_s: int = TIMEOUT_S, endpoint_name: str = ENDPOINT_NAME):
    """Poll success key; if not found, also check the endpoint's S3FailurePath for a failure object."""
    out_bucket, out_key = _parse_s3(output_location)
    basename = out_key.rsplit("/", 1)[-1]

    fail_bucket, fail_prefix = _failure_bucket_prefix(endpoint_name)
    fail_key = f"{fail_prefix}/{basename}" if (fail_bucket and fail_prefix) else None

    t0, backoff = time.time(), 1.0
    while True:
        try:
            obj = _s3.get_object(Bucket=out_bucket, Key=out_key)
            raw = obj["Body"].read()
            try:
                data = json.loads(raw)
            except Exception:
                return raw.decode("utf-8", errors="replace")
            if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
                return data[0]["generated_text"]
            if isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"]
            return json.dumps(data)
        except _s3.exceptions.NoSuchKey:
            pass
        except botocore.exceptions.ClientError as e:
            if e.response.get("Error", {}).get("Code") != "NoSuchKey":
                raise

        # 2) failure path
        if fail_bucket and fail_key:
            try:
                fobj = _s3.get_object(Bucket=fail_bucket, Key=fail_key)
                ftxt = fobj["Body"].read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Async inference FAILED: s3://{fail_bucket}/{fail_key}\n{ftxt}"
                )
            except _s3.exceptions.NoSuchKey:
                pass
            except botocore.exceptions.ClientError as e:
                if e.response.get("Error", {}).get("Code") != "NoSuchKey":
                    raise

        # 3) timeout
        if time.time() - t0 > timeout_s:
            raise TimeoutError(
                f"Result not ready after {timeout_s}s "
                f"(success s3://{out_bucket}/{out_key}"
                + (f", failure s3://{fail_bucket}/{fail_key}" if fail_bucket and fail_key else "")
                + ")"
            )

        time.sleep(backoff)
        backoff = min(backoff * 1.5, 4.0)