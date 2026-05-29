"""Shared HTTP GET with retry/backoff for harvesters.

Harvesters historically reimplemented their own retry loops with inconsistent
HTTP clients (``requests`` vs ``urllib``) and no shared timeout/backoff policy.
This is the single ``requests``-based GET helper they should use.
"""
import time

import requests


class HttpRetryError(RuntimeError):
    """Raised when a GET exhausts all retries."""


def get_with_retry(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 30,
    retries: int = 3,
    backoff: float = 2.0,
    session: requests.Session | None = None,
) -> requests.Response:
    """GET *url* with retry on transient failures.

    Retries on connection/timeout errors and on HTTP 429 / 5xx, with linear
    backoff (``backoff * attempt`` seconds). Raises ``HttpRetryError`` (chained
    from the last underlying error) if every attempt fails. A successful 2xx/3xx
    (or any non-retryable 4xx, which is surfaced via ``raise_for_status``) is
    returned to the caller.
    """
    getter = session.get if session is not None else requests.get
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            resp = getter(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                last_exc = HttpRetryError(f"HTTP {resp.status_code} from {url}")
                if attempt < retries:
                    time.sleep(backoff * attempt)
                    continue
                raise last_exc
            resp.raise_for_status()
            return resp
        except requests.HTTPError:
            # Non-retryable 4xx (5xx/429 were handled above) — surface immediately.
            raise
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * attempt)
                continue
            raise HttpRetryError(f"GET {url} failed after {retries} attempts: {exc}") from exc

    # Unreachable, but keeps type-checkers happy.
    raise HttpRetryError(f"GET {url} failed") from last_exc
