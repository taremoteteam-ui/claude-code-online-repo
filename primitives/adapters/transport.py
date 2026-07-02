"""Injectable transports for source adapters.

Adapters never talk to the network or filesystem directly; they call
``transport.get_json(url, params, fixture_name)`` and honestly report the
transport's ``mode`` in their receipts and snapshot metadata:

- ``FixtureTransport`` (mode ``"fixture_offline"``) reads SYNTHETIC fixture
  files shaped like the real APIs. Every fixture file must carry
  ``"fixture_synthetic": true`` - the transport refuses files without it.
- ``LiveTransport`` (mode ``"live_network"``) performs a real HTTPS GET via
  stdlib urllib.

Stdlib only. No third-party dependencies.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class TransportError(Exception):
    """Raised when a transport cannot produce a usable JSON response."""


def _snapshot_id_for_bytes(raw: bytes) -> str:
    return "snap:" + hashlib.sha256(raw).hexdigest()[:16]


class FixtureTransport:
    """Offline transport backed by synthetic fixture files.

    Fixture files live under ``fixture_root`` and have the shape::

        {
          "fixture_synthetic": true,
          "recorded_shape": "<which real API this mimics>",
          "request": {"url_family": ..., "params": ...},
          "response": {...}
        }

    ``get_json`` returns ``(payload["response"], snapshot_id)`` where the
    snapshot id is "snap:" + the first 16 hex chars of the sha256 of the
    fixture file bytes, so identical fixture bytes always yield the same
    snapshot id.
    """

    mode = "fixture_offline"

    def __init__(self, fixture_root: str | Path):
        self.fixture_root = Path(fixture_root)

    def get_json(self, url: str, params: dict, fixture_name: str) -> tuple[dict, str]:
        path = self.fixture_root / fixture_name
        if not path.is_file():
            raise TransportError(f"fixture not found: {path}")
        raw = path.read_bytes()
        snapshot_id = _snapshot_id_for_bytes(raw)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise TransportError(f"fixture is not valid JSON: {path}: {exc}") from exc
        if payload.get("fixture_synthetic") is not True:
            raise TransportError(
                f"fixture missing required 'fixture_synthetic': true marker: {path}"
            )
        if "response" not in payload:
            raise TransportError(f"fixture missing 'response' key: {path}")
        return payload["response"], snapshot_id


class LiveTransport:
    """Live HTTPS transport using stdlib urllib.request.

    ``urllib.request.urlopen`` installs a default ``ProxyHandler`` that reads
    proxy settings (HTTPS_PROXY / HTTP_PROXY) from the environment, so this
    transport honors the environment proxy automatically without extra code.
    Raises TransportError on any non-200 response or network failure.
    """

    mode = "live_network"

    def __init__(self, timeout_seconds: float = 20.0):
        self.timeout_seconds = timeout_seconds

    def get_json(self, url: str, params: dict, fixture_name: str) -> tuple[dict, str]:
        full_url = url
        if params:
            sep = "&" if "?" in url else "?"
            full_url = url + sep + urllib.parse.urlencode(params)
        request = urllib.request.Request(
            full_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "place-discovery-source-adapter/0.1 (stdlib urllib)",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as resp:
                status = resp.status
                body = resp.read()
        except urllib.error.HTTPError as exc:
            raise TransportError(f"HTTP {exc.code} from {full_url}") from exc
        except urllib.error.URLError as exc:
            raise TransportError(f"network error for {full_url}: {exc.reason}") from exc
        except OSError as exc:
            raise TransportError(f"transport failure for {full_url}: {exc}") from exc
        if status != 200:
            raise TransportError(f"HTTP {status} from {full_url} (expected 200)")
        snapshot_id = _snapshot_id_for_bytes(body)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise TransportError(f"non-JSON body from {full_url}: {exc}") from exc
        return payload, snapshot_id
