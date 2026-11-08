import httpx

MAX_PROVIDER_BODY_BYTES = 64 * 1024


async def read_provider_body(response: httpx.Response) -> bytes:
    """Read a streamed auth response with bounded memory and no decompression."""
    if response.headers.get("content-encoding", "identity").strip().lower() != "identity":
        raise httpx.RequestError("Unsupported authentication provider response encoding")

    declared_length = response.headers.get("content-length")
    if declared_length is not None:
        try:
            size = int(declared_length)
        except ValueError:
            raise httpx.RequestError("Invalid authentication provider response size") from None
        if size < 0 or size > MAX_PROVIDER_BODY_BYTES:
            raise httpx.RequestError("Authentication provider response size limit exceeded")

    body = bytearray()
    # Check each chunk even when Content-Length is absent or inaccurate.
    async for chunk in response.aiter_bytes():
        if len(body) + len(chunk) > MAX_PROVIDER_BODY_BYTES:
            raise httpx.RequestError("Authentication provider response size limit exceeded")
        body.extend(chunk)
    return bytes(body)
