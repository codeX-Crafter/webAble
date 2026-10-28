import asyncio
import ipaddress
import socket
from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit, urlunsplit


class UnsafeURL(ValueError):
    """Raised when a URL cannot be safely scanned."""


_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".test", ".invalid")
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "client_secret",
    "key",
    "password",
    "secret",
    "session",
    "token",
}


def sanitize_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode(
        [
            (key, "[redacted]" if key.lower() in _SENSITIVE_QUERY_KEYS else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
    )
    hostname = parts.hostname or ""
    if ":" in hostname:
        hostname = f"[{hostname}]"
    try:
        port = parts.port
    except ValueError:
        port = None
    netloc = f"{hostname}:{port}" if port is not None else hostname
    return urlunsplit(
        SplitResult(parts.scheme, netloc, parts.path, query, "")
    )


class PublicURLSafetyValidator:
    async def validate(self, url: str) -> str:
        try:
            parts = urlsplit(url)
            port = parts.port
        except ValueError as error:
            raise UnsafeURL("The URL is malformed.") from error
        scheme = parts.scheme.lower()
        if scheme not in {"http", "https"} or not parts.hostname:
            raise UnsafeURL("Only absolute HTTP and HTTPS URLs are allowed.")
        if parts.username is not None or parts.password is not None:
            raise UnsafeURL("URLs containing embedded credentials are not allowed.")
        if port is not None and not 1 <= port <= 65535:
            raise UnsafeURL("The URL contains an invalid port.")

        hostname = parts.hostname.rstrip(".").lower()
        if (
            hostname == "localhost"
            or hostname.endswith(_BLOCKED_SUFFIXES)
            or "." not in hostname and not _is_ip_address(hostname)
        ):
            raise UnsafeURL("The URL points to a local or internal hostname.")

        addresses = await _resolve_addresses(hostname)
        if not addresses:
            raise UnsafeURL("The URL hostname did not resolve to an IP address.")
        if any(not _is_public_address(address) for address in addresses):
            raise UnsafeURL("The URL resolves to a prohibited network destination.")
        return url


def _is_ip_address(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def _is_public_address(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return parsed.is_global


async def _resolve_addresses(hostname: str) -> set[str]:
    try:
        results = await asyncio.to_thread(
            socket.getaddrinfo, hostname, None, type=socket.SOCK_STREAM
        )
    except OSError as error:
        raise UnsafeURL("The URL hostname could not be resolved.") from error
    return {result[4][0] for result in results}
