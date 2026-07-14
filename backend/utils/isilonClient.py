# -*- coding: utf-8 -*-
"""Isilon OneFS REST API client — pure requests, no SDK dependency.

Auth     : Session-based (POST /session/1/session).
           Session cookies are cached only when storage.isilon_session_cache is true.
           On startup, GET /session/1/session is used to verify the cached
           session; if expired (401/403) a fresh login is performed.

Endpoints:
  - Cluster statfs : GET /platform/1/cluster/statfs
  - Storage pools  : GET /platform/16/storagepool/storagepools
  - Quotas         : GET /platform/1/quota/quotas       (paginated via resume)
  - NFS exports    : GET /platform/2/protocols/nfs/exports (paginated via resume)
"""
import json
import os
import requests
from typing import List, Dict, Optional
from appConfig import base_config

# Optional cache file: <project root>/.isilon_cache/cache.json
_PROJECT_ROOT = str(base_config.app_root_path)
_CACHE_DIR = os.path.join(_PROJECT_ROOT, ".isilon_cache")
_CACHE_FILE = os.path.join(_CACHE_DIR, "cache.json")


class IsilonClient:
    """Thin REST client for Isilon OneFS PAPI.

    Session cookies are persisted only when storage.isilon_session_cache is true.

    Startup logic:
      1. Load cached cookies for this host/user.
      2. Validate via GET /session/1/session.
         - 200  → reuse session.
         - 401/403 → clear cache entry, perform fresh login.
      3. After a successful (re-)login, persist cookies back to cache.

    During normal API calls, 401/403 also triggers a single re-login.
    """

    def __init__(self, hostname: str, username: str, password: str,
                 port: int = 8080, logger=None, tls_verify=True):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.logger = logger
        self.base_url = f"https://{hostname}:{port}/platform"
        self._session_url = f"https://{hostname}:{port}/session/1/session"
        self.api_version: str = "1"  # updated by _probe()
        self._session_cache_enabled = base_config.get("storage.isilon_session_cache", False)

        # Cache key unique per host/port/user
        self._cache_key = f"{hostname}:{port}:{username}"

        self.session = requests.Session()
        self.session.verify = tls_verify
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        # Try cached session first; fall back to fresh login
        if not self._load_cached_session():
            self._login()

        self._probe()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(msg)

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _read_cache(self) -> Dict:
        """Read the full cache file; return empty dict on any error."""
        if not self._session_cache_enabled:
            return {}
        try:
            with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_cache(self, data: Dict):
        """Write the full cache dict to disk."""
        if not self._session_cache_enabled:
            return
        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            self._log('warning', f"[IsilonClient] Could not write cache: {exc}")

    def _save_session_cache(self):
        """Persist current session cookies + CSRF token for this host/user."""
        if not self._session_cache_enabled:
            return
        cache = self._read_cache()
        cache[self._cache_key] = {
            'cookies': dict(self.session.cookies),
            'csrf': self.session.headers.get('X-CSRF-Token', ''),
        }
        self._write_cache(cache)
        self._log('info', f"[IsilonClient] Session cached → {_CACHE_FILE} [{self._cache_key}]")

    def _clear_cache_entry(self):
        """Remove the cache entry for this host/user."""
        if not self._session_cache_enabled:
            return
        cache = self._read_cache()
        if self._cache_key in cache:
            del cache[self._cache_key]
            self._write_cache(cache)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _apply_cookies(self, entry: Dict):
        """Restore cookies and CSRF header from a cache entry."""
        for name, value in entry.get('cookies', {}).items():
            self.session.cookies.set(name, value)
        csrf = entry.get('csrf', '')
        if csrf:
            self.session.headers['X-CSRF-Token'] = csrf
            self.session.headers['Referer'] = f"https://{self.hostname}:{self.port}/"

    def _load_cached_session(self) -> bool:
        """Load cached cookies and validate via GET /session/1/session.

        Returns True if the cached session is still valid, False otherwise.
        """
        if not self._session_cache_enabled:
            return False
        cache = self._read_cache()
        entry = cache.get(self._cache_key)
        if not entry:
            return False

        self._apply_cookies(entry)

        # Validate: GET /session/1/session
        try:
            resp = self.session.get(self._session_url, timeout=15)
            if resp.status_code == 200:
                info = resp.json()
                self._log('info',
                          f"[IsilonClient] Reused cached session ✓ "
                          f"(services={info.get('services')}, "
                          f"timeout_absolute={info.get('timeout_absolute')}s)")
                return True
            self._log('info',
                      f"[IsilonClient] Cached session invalid "
                      f"(HTTP {resp.status_code}), will re-login")
        except Exception as exc:
            self._log('warning', f"[IsilonClient] Session validation error: {exc}")

        # Stale — clean up before fresh login
        self.session.cookies.clear()
        self.session.headers.pop('X-CSRF-Token', None)
        self.session.headers.pop('Referer', None)
        self._clear_cache_entry()
        return False

    def _login(self) -> bool:
        """POST /session/1/session, store cookies, persist to cache.

        Returns True on success, False on failure (logs error, does not raise).
        """
        payload = {
            'username': self.username,
            'password': self.password,
            'services': ['platform'],
        }
        try:
            resp = self.session.post(self._session_url, json=payload, timeout=30)
            self._log('info',
                      f"[IsilonClient] Login HTTP {resp.status_code} ← {self._session_url}")
            if not resp.ok:
                try:
                    msg = resp.json().get('message', resp.text)
                except Exception:
                    msg = resp.text
                self._log('error',
                          f"[IsilonClient] Login failed ({resp.status_code}): {msg}")
                return False

            csrf = self.session.cookies.get('isicsrf', '')
            if csrf:
                self.session.headers['X-CSRF-Token'] = csrf
                self.session.headers['Referer'] = f"https://{self.hostname}:{self.port}/"

            data = resp.json()
            self._log('info',
                      f"[IsilonClient] Login OK — services={data.get('services')}, "
                      f"timeout_absolute={data.get('timeout_absolute')}s")
            self._save_session_cache()
            return True
        except Exception as exc:
            self._log('error', f"[IsilonClient] Login error: {exc}")
            return False

    def _probe(self) -> bool:
        """Fetch cluster config to confirm connectivity and extract OneFS version.

        Returns True on success, False on failure (logs error, does not raise).
        """
        url = f"{self.base_url}/1/cluster/config"
        try:
            resp = self.session.get(url, timeout=30)
            if not resp.ok:
                self._log('error',
                          f"[IsilonClient] Probe failed ({resp.status_code}) ← {url}")
                return False
            data = resp.json()
            onefs_ver = data.get('onefs_version', {}).get('release', 'unknown')
            self.api_version = onefs_ver.split('.')[0] if onefs_ver != 'unknown' else '1'
            self._log('info',
                      f"[IsilonClient] Connected to {self.hostname}:{self.port} "
                      f"— OneFS {onefs_ver}")
            return True
        except Exception as exc:
            self._log('error', f"[IsilonClient] Probe error: {exc}")
            return False

    # ------------------------------------------------------------------
    # Generic GET with auto re-login
    # ------------------------------------------------------------------

    def _get(self, path: str, params: Dict = None) -> Optional[Dict]:
        """GET endpoint, return parsed JSON or None on error.

        On 401/403 performs a single re-login then retries.
        """
        url = f"{self.base_url}{path}"
        for attempt in range(2):
            try:
                resp = self.session.get(url, params=params, timeout=60)
                if resp.status_code in (401, 403) and attempt == 0:
                    self._log('warning',
                              f"[IsilonClient] Session expired "
                              f"({resp.status_code}), re-logging in…")
                    self._clear_cache_entry()
                    self._login()
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.HTTPError as exc:
                self._log('error', f"[IsilonClient] GET {path} failed: {exc}")
                raise
            except Exception as exc:
                self._log('error', f"[IsilonClient] GET {path} error: {exc}")
                raise
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_cluster_stats(self) -> Optional[Dict]:
        """Return cluster filesystem statistics (POSIX statfs fields)."""
        return self._get('/1/cluster/statfs')

    def get_storage_pools(self) -> List[Dict]:
        """Return OneFS 9.11 top-level storage pools."""
        data = self._get(
            '/16/storagepool/storagepools',
            params={'toplevels': 'true'},
        )
        pools = data.get('storagepools') if isinstance(data, dict) else None
        if not isinstance(pools, list):
            raise ValueError("Invalid OneFS storagepools response")
        return pools

    def get_quotas(self, resolve_names: bool = True,
                   quota_type: Optional[str] = None,
                   recurse_path_children: bool = False) -> List[Dict]:
        """Return all quotas, following resume-based pagination."""
        result: List[Dict] = []
        params = {
            'limit': 1000,
            'resolve_names': str(resolve_names).lower(),
            'recurse_path_children': str(recurse_path_children).lower(),
        }
        if quota_type:
            params['type'] = quota_type

        resume = None
        while True:
            data = self._get('/1/quota/quotas',
                             params={'resume': resume} if resume else params)
            if data is None:
                break
            result.extend(data.get('quotas', []) or [])
            resume = data.get('resume')
            if not resume:
                break

        return result

    def get_exports(self) -> List[Dict]:
        """Return all NFS exports, following resume-based pagination."""
        result: List[Dict] = []
        resume = None

        while True:
            data = self._get('/2/protocols/nfs/exports',
                             params={'resume': resume} if resume
                             else {'limit': 1000})
            if data is None:
                break
            result.extend(data.get('exports', []) or [])
            resume = data.get('resume')
            if not resume:
                break

        return result

    def close(self):
        """Release the uncached OneFS session and close HTTP resources."""
        if not self.session:
            return

        try:
            if not self._session_cache_enabled:
                self.session.delete(self._session_url, timeout=15)
        except requests.RequestException as exc:
            self._log(
                "warning",
                f"[IsilonClient] Logout error: {type(exc).__name__}",
            )
        finally:
            self.session.close()
