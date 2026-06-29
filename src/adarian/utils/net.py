"""Network utility functions — internal address detection.

Replaces scattered hardcoded IP address checks with a single reusable helper.
"""

from urllib.parse import urlparse


def is_internal_url(url: str) -> bool:
    """Check if *url* points to a private/internal network address.

    Internal addresses should bypass the system HTTP proxy when accessed
    directly. This includes localhost, private IPs, and CGNAT ranges.

    Returns False for empty URLs, domain names, or malformed input,
    so that "no internal address detected" is the safe default.
    """
    if not url:
        return False
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False

    # localhost / loopback
    if host in ("localhost", "127.0.0.1", "::1"):
        return True

    # Private IP ranges (RFC 1918) + CGNAT (RFC 6598: 100.64.0.0/10)
    parts = host.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        first = int(parts[0])
        second = int(parts[1])
        if first == 10:
            return True                       # 10.0.0.0/8
        if first == 172 and 16 <= second <= 31:
            return True                       # 172.16.0.0/12
        if first == 192 and second == 168:
            return True                       # 192.168.0.0/16
        if first == 100 and 64 <= second <= 127:
            return True                       # 100.64.0.0/10 (CGNAT)

    return False
