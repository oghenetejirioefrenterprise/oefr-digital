"""Grok via the xAI API — live X (Twitter) search/analysis + drafting.

The grok *CLI* (the local `grok` binary, model `grok-build`) is a coding agent
and has NO X-search tool — so the old subprocess approach returned empty. The
official live-X-search path is the xAI **Agent Tools API**: POST
``/v1/responses`` with ``tools:[{type:"x_search"}]``. We authenticate with the
OAuth token grok stores at ``~/.grok/auth.json`` (the same login the CLI uses) —
no separate API key needed. ``search``/``analyze`` use ``x_search``; ``draft``
is plain generation. Public function signatures are unchanged.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

_API_URL = "https://api.x.ai/v1/responses"
_MODEL = "grok-4-fast"
_TIMEOUT = 90
_AUTH_PATH = Path.home() / ".grok" / "auth.json"

# Refresh the OAuth token when it has this little time left (grok normally keeps
# it fresh on its own use; this is the proactive fallback for when it hasn't).
_REFRESH_MARGIN_S = 120
_DEFAULT_ISSUER = "https://auth.x.ai"


def _load_auth() -> dict | None:
    try:
        return json.loads(_AUTH_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _find_entry(data: dict) -> tuple[str | None, dict | None]:
    """The auth entry holding the access token (`key`) + a refresh_token."""
    for k, v in data.items():
        if isinstance(v, dict) and v.get("key") and v.get("refresh_token"):
            return k, v
    # Fall back to any entry with a key (no refresh available).
    for k, v in data.items():
        if isinstance(v, dict) and v.get("key"):
            return k, v
    return None, None


def _expires_soon(entry: dict) -> bool:
    exp = entry.get("expires_at")
    if not exp:
        return False  # unknown expiry — let the API validate
    try:
        e = dt.datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
    except ValueError:
        return False
    return dt.datetime.now(dt.timezone.utc) >= e - dt.timedelta(seconds=_REFRESH_MARGIN_S)


def _refresh(entry: dict) -> dict | None:
    """Exchange the refresh_token for a fresh token set at the OIDC endpoint."""
    client_id = entry.get("oidc_client_id")
    refresh_token = entry.get("refresh_token")
    if not (client_id and refresh_token):
        return None
    issuer = str(entry.get("oidc_issuer") or _DEFAULT_ISSUER).rstrip("/")
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{issuer}/oauth2/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            tok = json.loads(resp.read().decode("utf-8"))
        return tok if tok.get("access_token") else None
    except Exception as e:
        log.warning("grok OAuth refresh failed: %s", e)
        return None


def _persist(data: dict, dict_key: str, entry: dict, tok: dict) -> None:
    """Write the refreshed token set back to auth.json (atomic, 0600, locked)."""
    from trinity._io import atomic_write_text, file_lock

    entry["key"] = tok["access_token"]
    if tok.get("refresh_token"):
        entry["refresh_token"] = tok["refresh_token"]
    if tok.get("expires_in"):
        new_exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=int(tok["expires_in"]))
        entry["expires_at"] = new_exp.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
    data[dict_key] = entry
    try:
        with file_lock(_AUTH_PATH):
            atomic_write_text(_AUTH_PATH, json.dumps(data, indent=1), fsync=False)
            os.chmod(_AUTH_PATH, 0o600)
    except Exception as e:  # pragma: no cover - defensive
        log.warning("could not persist refreshed grok token: %s", e)


def _oauth_token() -> str | None:
    """Return a valid xAI OAuth access token, refreshing proactively if it is
    about to expire. Read fresh each call so a token grok refreshed is picked up.
    """
    data = _load_auth()
    if not data:
        return None
    dict_key, entry = _find_entry(data)
    if entry is None:
        return None
    if not _expires_soon(entry):
        return entry.get("key")

    # Near expiry: re-read under lock (grok or another worker may have just
    # refreshed it) and refresh only if still needed.
    from trinity._io import file_lock
    with file_lock(_AUTH_PATH):
        data = _load_auth() or data
        dict_key, entry = _find_entry(data)
        if entry is None:
            return None
        if not _expires_soon(entry):
            return entry.get("key")
        tok = _refresh(entry)
    if tok:
        _persist(data, dict_key, entry, tok)
        return tok["access_token"]
    # Refresh failed — return the (possibly stale) token; the API call will
    # either still succeed or return a graceful Error string.
    return entry.get("key")


def _extract_text(data: dict) -> str:
    """Pull the assistant's output_text out of a /v1/responses payload."""
    texts: list[str] = []

    def walk(o: object) -> None:
        if isinstance(o, dict):
            if o.get("type") == "output_text" and isinstance(o.get("text"), str):
                texts.append(o["text"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data.get("output", data))
    return "\n".join(t for t in texts if t).strip()


def _call(prompt: str, x_search: bool = True) -> str:
    """Call the xAI Responses API and return the assistant text (or an Error: string)."""
    token = _oauth_token()
    if not token:
        return "Error: no grok OAuth token found (run `grok login`)"

    body: dict = {"model": _MODEL, "input": prompt}
    if x_search:
        body["tools"] = [{"type": "x_search"}]

    req = urllib.request.Request(
        _API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        log.warning("xAI API HTTP %s: %s", e.code, detail)
        return f"Error: xAI API returned HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return f"Error: xAI API call failed: {e}"
    except Exception as e:  # pragma: no cover - defensive
        return f"Error: xAI API unexpected failure: {type(e).__name__}: {e}"

    return _extract_text(data) or "(no result)"


def search(query: str, limit: int = 10) -> str:
    """Search X for posts matching *query* via the xAI x_search tool."""
    prompt = (
        f"Search X (Twitter) for: {query}\n\n"
        f"Return up to {limit} recent, relevant posts. For each post include the "
        f"author @handle, the text, the date, and the post URL."
    )
    return _call(prompt, x_search=True)


def draft(topic: str, context: str = "", tone: str = "professional") -> str:
    """Generate a tweet draft (no X search needed)."""
    prompt = (
        f"Draft a tweet (max 280 characters) about: {topic}\n"
        f"Tone: {tone}. Make it specific with real numbers or facts — no vague "
        f"claims. No hashtags unless they add real value. Do not include links "
        f"in the tweet text."
    )
    if context:
        prompt += f"\nAdditional context: {context}"
    return _call(prompt, x_search=False)


def analyze(query: str) -> str:
    """Analyze X sentiment and engagement patterns via the xAI x_search tool."""
    prompt = (
        f"Search X (Twitter) for activity around: {query}\n\n"
        f"Cover: overall sentiment (positive/negative/neutral), engagement level, "
        f"key themes, notable accounts discussing it, and any trending angles. "
        f"Cite specific posts with @handles and URLs."
    )
    return _call(prompt, x_search=True)
