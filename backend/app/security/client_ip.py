from fastapi import Request


def client_ip(request: Request, trusted_proxy_hops: int) -> str:
    """The caller's IP address, as used for rate limiting.

    Every proxy in front of the app *appends* the address it saw to `X-Forwarded-For`, so behind
    N trusted proxies the real client is the N-th entry from the right. Everything to the left of
    it is whatever the client chose to send: trusting the leftmost entry (what uvicorn does with
    `--forwarded-allow-ips='*'`) would let anyone dodge the login limiter with a fake header.
    Cloud Run's front end is one hop. Without a trusted proxy the socket peer is the client.
    """
    if trusted_proxy_hops > 0:
        hops = [
            hop.strip()
            for header in request.headers.getlist("x-forwarded-for")
            for hop in header.split(",")
            if hop.strip()
        ]
        if len(hops) >= trusted_proxy_hops:
            return hops[-trusted_proxy_hops]
    return request.client.host if request.client else "unknown"
