"""Vendored ZTE MC889 API client for Home Assistant.

Self-contained client with no external dependencies beyond ``requests``.
See https://github.com/bernhardberger/zte-mc889-api for the standalone library.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ── Exceptions ──────────────────────────────────────────────────────────────


class ZteError(Exception):
    """Base exception for ZTE API errors."""


class ZteAuthError(ZteError):
    """Login/authentication failure."""


class ZteLockoutError(ZteError):
    """Modem locked out — power cycle to reset."""


# ── Helpers ─────────────────────────────────────────────────────────────────


def _sha256_upper(text: str) -> str:
    """SHA256 hash, uppercase hex — matches the modem's JS SHA256()."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def signal_quality(field_name: str, value: str) -> str:
    """Return quality label (excellent/good/fair/poor) for signal metrics."""
    try:
        v = float(value)
    except (ValueError, TypeError):
        return ""
    if field_name in ("Z5g_rsrp", "lte_rsrp"):
        if v > -80: return "excellent"
        if v > -90: return "good"
        if v > -100: return "fair"
        return "poor"
    if field_name in ("Z5g_SINR", "lte_snr"):
        if v > 20: return "excellent"
        if v > 13: return "good"
        if v > 0: return "fair"
        return "poor"
    if field_name in ("Z5g_rsrq", "lte_rsrq"):
        if v > -10: return "excellent"
        if v > -15: return "good"
        if v > -20: return "fair"
        return "poor"
    return ""


# ── Session ─────────────────────────────────────────────────────────────────


@dataclass
class Session:
    cookie: str
    ad_token: str
    created: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({
            "cookie": self.cookie, "ad_token": self.ad_token, "created": self.created,
        })

    @classmethod
    def from_json(cls, text: str) -> Session:
        d = json.loads(text)
        return cls(cookie=d["cookie"], ad_token=d["ad_token"], created=d.get("created", 0))


# ── Client ──────────────────────────────────────────────────────────────────


class ZteClient:
    """ZTE MC889 API client with SHA256 auth, session caching, and auto-re-login."""

    def __init__(
        self,
        host: str = "192.168.254.1",
        password: str | None = None,
        password_file: str | None = None,
        session_file: str = "/tmp/.zte-mc889-session",
        proto: str = "https",
        timeout: int = 10,
    ):
        self.host = host
        self.base_url = f"{proto}://{host}"
        self.get_url = f"{self.base_url}/goform/goform_get_cmd_process"
        self.set_url = f"{self.base_url}/goform/goform_set_cmd_process"
        self.referer = f"{self.base_url}/index.html"
        self.timeout = timeout
        self.session_file = Path(session_file)
        self._session: Session | None = None

        self._password = password or os.environ.get("ZTE_PASSWORD")
        if not self._password and password_file:
            pf = Path(password_file)
            if pf.exists():
                self._password = pf.read_text().strip()
        if not self._password:
            raise ZteError("No password provided")

        self._http = requests.Session()
        self._http.verify = False
        self._http.headers.update({"Referer": self.referer})
        self._load_session()

    def _api_get_raw(self, params: dict[str, str]) -> dict[str, Any]:
        r = self._http.get(self.get_url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _api_post_raw(self, data: dict[str, str]) -> dict[str, Any]:
        r = self._http.post(
            self.set_url, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def _save_session(self) -> None:
        if self._session:
            self.session_file.write_text(self._session.to_json())
            try:
                self.session_file.chmod(0o600)
            except OSError:
                pass

    def _load_session(self) -> None:
        if self.session_file.exists():
            try:
                self._session = Session.from_json(self.session_file.read_text())
                self._http.cookies.set("stok", self._session.cookie)
            except (json.JSONDecodeError, KeyError):
                self._session = None

    def _clear_session(self) -> None:
        self._session = None
        self._http.cookies.clear()
        self.session_file.unlink(missing_ok=True)

    def login(self) -> Session:
        """Full login handshake: LD nonce -> SHA256 double-hash -> stok cookie -> AD token."""
        self._clear_session()
        pass_hash = _sha256_upper(self._password)

        ld_data = self._api_get_raw({"isTest": "false", "cmd": "LD"})
        ld = ld_data.get("LD", "")
        login_hash = _sha256_upper(pass_hash + ld)

        result = self._api_post_raw({
            "isTest": "false", "goformId": "LOGIN", "password": login_hash,
        })

        code = result.get("result", "?")
        if code in ("0", "4"):
            pass
        elif code == "3" or code == "1":
            raise ZteAuthError("Login failed — bad credentials")
        elif code == "2":
            raise ZteAuthError("Login failed — duplicate session")
        elif code == "5":
            raise ZteLockoutError("LOCKED OUT — power cycle modem to reset")
        else:
            raise ZteAuthError(f"Login failed — result code: {code}")

        cookie = self._http.cookies.get("stok")
        if not cookie:
            raise ZteError("Login succeeded but no session cookie returned")

        rd_data = self._api_get_raw({"isTest": "false", "cmd": "RD"})
        ad = _sha256_upper(rd_data.get("RD", ""))

        self._session = Session(cookie=cookie, ad_token=ad)
        self._save_session()
        return self._session

    def _ensure_session(self) -> Session:
        if self._session:
            try:
                check = self._api_get_raw({
                    "isTest": "false", "cmd": "loginfo", "AD": self._session.ad_token,
                })
                if check.get("loginfo") == "ok":
                    return self._session
            except Exception:
                pass
        return self.login()

    def logout(self) -> dict[str, Any]:
        session = self._ensure_session()
        result = self._api_post_raw({
            "isTest": "false", "goformId": "LOGOUT", "AD": session.ad_token,
        })
        self._clear_session()
        return result

    def get(self, fields: list[str]) -> dict[str, Any]:
        """Fetch one or more fields from the modem."""
        session = self._ensure_session()
        data = self._api_get_raw({
            "isTest": "false", "multi_data": "1",
            "cmd": ",".join(fields), "AD": session.ad_token,
        })
        # Modem returns {"result": "failure"} when a field is unsupported
        if data.get("result") == "failure":
            raise ZteError(f"Modem rejected query (unsupported field?): {','.join(fields)}")
        # Retry on expired session (all values empty)
        if len(fields) > 1 and all(v == "" for v in data.values()):
            self.login()
            data = self._api_get_raw({
                "isTest": "false", "multi_data": "1",
                "cmd": ",".join(fields), "AD": self._session.ad_token,
            })
            if data.get("result") == "failure":
                raise ZteError(f"Modem rejected query after re-login: {','.join(fields)}")
        return data

    def set(self, goform_id: str, **params: str) -> dict[str, Any]:
        """Execute a SET command on the modem."""
        session = self._ensure_session()
        return self._api_post_raw({
            "isTest": "false", "goformId": goform_id, "AD": session.ad_token,
            **params,
        })
