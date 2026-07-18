# -*- coding: utf-8 -*-
"""Isilon OneFS REST API client — pure requests, no SDK dependency.

Auth     : Session-based (POST /session/1/session).
           Session cookies can be cached per cluster in a file or Redis.
           On startup, GET /session/1/session is used to verify the cached
           session; if expired (401/403) a fresh login is performed.

Endpoints:
  - Cluster statfs : GET /platform/1/cluster/statfs
  - Storage pools  : GET /platform/16/storagepool/storagepools
  - Quotas         : GET /platform/1/quota/quotas       (paginated via resume)
  - NFS exports    : GET /platform/2/protocols/nfs/exports (paginated via resume)
"""
import json
import hashlib
import os
import tempfile
import requests
import redis
from pathlib import Path
from typing import List, Dict, Optional
from appConfig import base_config
from utils.storageDeviceHttp import raise_for_device_status

# Optional cache file: <project root>/.isilon_cache/cache.json
_PROJECT_ROOT = str(base_config.app_root_path)
_CACHE_DIR = os.path.join(_PROJECT_ROOT, ".isilon_cache")
_CACHE_FILE = os.path.join(_CACHE_DIR, "cache.json")
_CACHE_MODES = {"none", "file", "redis"}


def _sum_counters(*counters: Optional[Dict]) -> Dict[str, float]:
    total = 0.0
    count = 0.0
    for counter in counters:
        if not isinstance(counter, dict):
            continue
        total += float(counter.get('sum') or 0)
        count += float(counter.get('count') or 0)
    return {'sum': total, 'count': count}


def _counter_average(counter: Optional[Dict], empty=None) -> Optional[float]:
    if not isinstance(counter, dict):
        return empty
    count = float(counter.get('count') or 0)
    return float(counter.get('sum') or 0) / count if count else empty


def _counter_sum(counter: Optional[Dict], empty=None) -> Optional[float]:
    if not isinstance(counter, dict) or counter.get('sum') is None:
        return empty
    return float(counter['sum'])


class IsilonClient:
    """Thin REST client for Isilon OneFS PAPI.

    Session cookies are persisted only when the cluster selects file or Redis cache.

    Startup logic:
      1. Load cached cookies for this host/user.
      2. Validate via GET /session/1/session.
         - 200  → reuse session.
         - 401/403 → clear cache entry, perform fresh login.
      3. After a successful (re-)login, persist cookies back to cache.

    During normal API calls, 401/403 also triggers a single re-login.
    """

    def __init__(self, hostname: str, username: str, password: str,
                 port: int = 8080, logger=None, protocol: str = "https",
                 tls_verify=True, session_cache_mode: str = "none",
                 session_cache_path: str | None = None):
        if protocol not in ("http", "https"):
            raise ValueError(f"Unsupported storage protocol: {protocol}")
        if session_cache_mode not in _CACHE_MODES:
            raise ValueError(f"Unsupported Isilon session cache mode: {session_cache_mode}")
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.logger = logger
        self.origin = f"{protocol}://{hostname}:{port}"
        self.base_url = f"{self.origin}/platform"
        self._session_url = f"{self.origin}/session/1/session"
        self.api_version: str = "1"  # updated by _probe()
        self._session_cache_mode = session_cache_mode
        self._session_cache_enabled = session_cache_mode != "none"
        self._cache_persisted = False

        cache_path = Path(session_cache_path or _CACHE_FILE)
        if not cache_path.is_absolute():
            cache_path = base_config.app_root_path / cache_path
        self._cache_file = cache_path.resolve()

        # Cache key unique per protocol/host/port/user
        self._cache_key = f"{protocol}:{hostname}:{port}:{username}"
        self._redis_key = (
            "diskpulse:isilon-session:"
            + hashlib.sha256(self._cache_key.encode("utf-8")).hexdigest()
        )
        self._redis_client = None
        if session_cache_mode == "redis":
            self._redis_client = redis.StrictRedis(
                host=base_config.get("redis.host"),
                port=base_config.get("redis.port", 6379),
                db=base_config.get("redis.session_db", 8),
                decode_responses=True,
            )

        self.session = requests.Session()
        self.session.verify = tls_verify if protocol == "https" else False
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
        """Read the configured session cache; return empty dict on errors."""
        if not self._session_cache_enabled:
            return {}
        try:
            if self._session_cache_mode == "redis":
                value = self._redis_client.get(self._redis_key)
                return {self._cache_key: json.loads(value)} if value else {}
            with self._cache_file.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, TypeError, json.JSONDecodeError, redis.RedisError) as exc:
            self._log('warning', f"[IsilonClient] Session cache read failed: {type(exc).__name__}")
            return {}

    def _write_cache(self, data: Dict, ttl: int = 14400) -> bool:
        """Persist the session cache using the configured backend."""
        if not self._session_cache_enabled:
            return False
        temporary_path = None
        try:
            if self._session_cache_mode == "redis":
                entry = data.get(self._cache_key)
                if entry is None:
                    self._redis_client.delete(self._redis_key)
                else:
                    self._redis_client.setex(
                        self._redis_key,
                        max(int(ttl), 1),
                        json.dumps(entry),
                    )
                return True

            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._cache_file.parent,
                delete=False,
            ) as file:
                json.dump(data, file, indent=2)
                temporary_path = Path(file.name)
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, self._cache_file)
            return True
        except Exception as exc:
            self._log('warning', f"[IsilonClient] Session cache write failed: {type(exc).__name__}")
            return False
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

    def _save_session_cache(self, ttl: int = 14400) -> bool:
        """Persist current session cookies + CSRF token for this host/user."""
        if not self._session_cache_enabled:
            return False
        cache = self._read_cache()
        cache[self._cache_key] = {
            'cookies': dict(self.session.cookies),
            'csrf': self.session.headers.get('X-CSRF-Token', ''),
        }
        self._cache_persisted = self._write_cache(cache, ttl)
        if self._cache_persisted:
            self._log('info', f"[IsilonClient] Session cached ({self._session_cache_mode})")
        return self._cache_persisted

    def _clear_cache_entry(self):
        """Remove the cache entry for this host/user."""
        if not self._session_cache_enabled:
            return
        cache = self._read_cache()
        if self._cache_key in cache:
            del cache[self._cache_key]
            self._write_cache(cache)
        self._cache_persisted = False

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
            self.session.headers['Referer'] = f"{self.origin}/"

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
                self._cache_persisted = True
                self._log('info',
                          f"[IsilonClient] Reused cached session ✓ "
                          f"(services={info.get('services')}, "
                          f"timeout_absolute={info.get('timeout_absolute')}s)")
                return True
            if resp.status_code not in (401, 403):
                raise_for_device_status(
                    resp,
                    logger=self,
                    context="[IsilonClient] Cached session validation failed",
                )
            try:
                raise_for_device_status(
                    resp,
                    logger=self,
                    context="[IsilonClient] Cached session expired",
                )
            except requests.HTTPError:
                pass
            self._log('info',
                      f"[IsilonClient] Cached session invalid "
                      f"(HTTP {resp.status_code}), will re-login")
        except requests.HTTPError:
            raise
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

        Returns True on success. Device and transport errors are re-raised unchanged.
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
            raise_for_device_status(
                resp,
                logger=self,
                context="[IsilonClient] Login failed",
            )

            csrf = self.session.cookies.get('isicsrf', '')
            if csrf:
                self.session.headers['X-CSRF-Token'] = csrf
                self.session.headers['Referer'] = f"{self.origin}/"

            data = resp.json()
            self._log('info',
                      f"[IsilonClient] Login OK — services={data.get('services')}, "
                      f"timeout_absolute={data.get('timeout_absolute')}s")
            self._save_session_cache(data.get('timeout_absolute') or 14400)
            return True
        except requests.HTTPError:
            raise
        except Exception as exc:
            self._log('error', f"[IsilonClient] Login error: {exc}")
            raise

    def _probe(self) -> bool:
        """Fetch cluster config to confirm connectivity and extract OneFS version.

        Returns True on success. Device and transport errors are re-raised unchanged.
        """
        url = f"{self.base_url}/1/cluster/config"
        try:
            resp = self.session.get(url, timeout=30)
            raise_for_device_status(
                resp,
                logger=self,
                context=f"[IsilonClient] Probe failed url={url}",
            )
            data = resp.json()
            onefs_ver = data.get('onefs_version', {}).get('release', 'unknown')
            self.discover_api_version()
            self._log('info',
                      f"[IsilonClient] Connected to {self.hostname}:{self.port} "
                      f"— OneFS {onefs_ver}")
            return True
        except requests.HTTPError:
            raise
        except Exception as exc:
            self._log('error', f"[IsilonClient] Probe error: {exc}")
            raise

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
                raise_for_device_status(
                    resp,
                    logger=self,
                    context=f"[IsilonClient] GET {path} failed",
                )
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

    def discover_api_version(self) -> str:
        """Discover the OneFS platform API version independently of OneFS release."""
        data = self._get('/latest')
        value = data.get('latest') if isinstance(data, dict) else None
        if isinstance(value, dict):
            value = value.get('version')
        if value is None:
            raise ValueError("Invalid OneFS platform latest response")
        self.api_version = str(value)
        return self.api_version

    def get_performance_statistics(self) -> List[Dict]:
        dataset_data = self._get(f'/{self.api_version}/performance/datasets')
        datasets = dataset_data.get('datasets') if isinstance(dataset_data, dict) else None
        if not isinstance(datasets, list):
            raise ValueError("Invalid OneFS performance datasets response")
        dataset = next(
            (
                item
                for item in datasets
                if isinstance(item, dict)
                and 'path' in [str(metric).lower() for metric in item.get('metrics', [])]
            ),
            None,
        )
        if dataset is None or dataset.get('id') is None or not dataset.get('statkey'):
            raise ValueError("OneFS path performance dataset is not configured")

        workload_data = self._get(
            f"/{self.api_version}/performance/datasets/{dataset['id']}/workloads"
        )
        workloads = workload_data.get('workloads') if isinstance(workload_data, dict) else None
        if not isinstance(workloads, list):
            raise ValueError("Invalid OneFS performance workloads response")
        paths = {
            str(item['id']): str(item.get('metric_values', {}).get('path'))
            for item in workloads
            if isinstance(item, dict)
            and item.get('id') is not None
            and item.get('metric_values', {}).get('path')
        }

        data = self._get(
            f'/{self.api_version}/statistics/current',
            params={'keys': dataset['statkey']},
        )
        stats = data.get('stats') if isinstance(data, dict) else None
        if not isinstance(stats, list):
            raise ValueError("Invalid OneFS path performance statistics response")

        rows = []
        for stat in stats:
            current = (
                (stat.get('value') or {})
                .get('dataset', {})
                .get('workloads', {})
                .get('workloads', [])
            )
            for workload in current:
                path = paths.get(str(workload.get('id')))
                record = workload.get('record') or {}
                if not path or not isinstance(record, dict):
                    continue
                read = _counter_average(record.get('latency_read'))
                write = _counter_average(record.get('latency_write'))
                total = _counter_average(
                    _sum_counters(
                        record.get('latency_read'),
                        record.get('latency_write'),
                        record.get('latency_other'),
                    ),
                    empty=0.0,
                )
                bytes_in = _counter_sum(record.get('bytes_in'))
                bytes_out = _counter_sum(record.get('bytes_out'))
                rows.append({
                    'key': f"{dataset['statkey']}.latency",
                    'workload': path,
                    'name': path,
                    'value': total,
                    'latency_read': read,
                    'latency_write': write,
                    'iops_total': _counter_sum(record.get('protocol_ops') or record.get('ops')),
                    'throughput_total': (
                        None
                        if bytes_in is None and bytes_out is None
                        else (bytes_in or 0) + (bytes_out or 0)
                    ),
                    'unit': 'microseconds',
                    'time': stat.get('time'),
                })
        return rows

    def get_event_group_occurrences(self) -> List[Dict]:
        data = self._get(f'/{self.api_version}/event/eventgroup-occurrences')
        events = data.get('eventgroups') if isinstance(data, dict) else None
        if not isinstance(events, list):
            raise ValueError("Invalid OneFS eventgroups response")
        return events

    def get_event_lists(self) -> List[Dict]:
        data = self._get(f'/{self.api_version}/event/eventlists')
        events = data.get('eventlists') if isinstance(data, dict) else None
        if not isinstance(events, list):
            raise ValueError("Invalid OneFS eventlists response")
        return events

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

    def _write_quota(self, method: str, url: str, payload: Dict) -> None:
        for attempt in range(2):
            response = getattr(self.session, method)(url, json=payload, timeout=60)
            if response.status_code in (401, 403) and attempt == 0:
                self._clear_cache_entry()
                self._login()
                continue
            raise_for_device_status(
                response,
                logger=self,
                context=f"[IsilonClient] {method.upper()} quota failed url={url}",
            )
            return
        raise RuntimeError("Isilon quota update authentication failed")

    @staticmethod
    def _matches_quota(quota: Dict, quota_type: str, path: str, username: str | None) -> bool:
        if quota.get("type") != quota_type or quota.get("path") != path:
            return False
        if quota_type != "user":
            return True
        persona = quota.get("persona") or {}
        return str(persona.get("name") or "") == str(username or "")

    def update_quota(
        self,
        *,
        quota_type: str,
        volume_name: str,
        qtree_name: str | None,
        path: str,
        username: str | None,
        hard_limit: float,
        soft_limit: float | None,
        soft_grace: int | None,
    ) -> Dict:
        quotas = self.get_quotas(quota_type=quota_type)
        existing = next(
            (
                quota for quota in quotas
                if self._matches_quota(quota, quota_type, path, username)
            ),
            None,
        )
        thresholds = {
            "hard": hard_limit,
            "soft": soft_limit,
            "soft_grace": soft_grace if soft_limit is not None else None,
        }
        payload = {"type": quota_type, "path": path, "thresholds": thresholds}
        if quota_type == "user":
            payload["persona"] = {"type": "user", "name": username}

        collection_url = f"{self.base_url}/{self.api_version}/quota/quotas"
        if existing is not None and not existing.get("linked", False):
            self._write_quota(
                "put",
                f"{collection_url}/{existing['id']}",
                {"thresholds": thresholds},
            )
        else:
            self._write_quota("post", collection_url, payload)

        current = next(
            (
                quota for quota in self.get_quotas(quota_type=quota_type)
                if self._matches_quota(quota, quota_type, path, username)
                and not quota.get("linked", False)
            ),
            None,
        )
        if current is None:
            raise RuntimeError("Isilon quota readback failed")
        response = self.session.get(f"{collection_url}/{current['id']}", timeout=60)
        raise_for_device_status(
            response,
            logger=self,
            context=f"[IsilonClient] GET quota readback failed url={collection_url}/{current['id']}",
        )
        data = response.json()
        quota = (data.get("quotas") or [data])[0]
        readback = quota.get("thresholds") or {}
        if (
            readback.get("hard") != hard_limit
            or readback.get("soft") != soft_limit
            or readback.get("soft_grace") != thresholds["soft_grace"]
        ):
            raise RuntimeError("Isilon quota readback mismatch")
        return {
            "hard_limit": readback.get("hard"),
            "soft_limit": readback.get("soft"),
            "soft_grace": readback.get("soft_grace"),
        }

    def read_quota(
        self,
        *,
        quota_type: str,
        volume_name: str,
        qtree_name: str | None,
        path: str,
        username: str | None,
    ) -> Dict:
        current = next(
            (
                quota for quota in self.get_quotas(quota_type=quota_type)
                if self._matches_quota(quota, quota_type, path, username)
                and not quota.get("linked", False)
            ),
            None,
        )
        if current is None:
            raise RuntimeError("Isilon quota readback failed")
        response = self.session.get(
            f"{self.base_url}/{self.api_version}/quota/quotas/{current['id']}", timeout=60,
        )
        raise_for_device_status(response, logger=self, context="[IsilonClient] GET quota readback failed")
        data = response.json()
        quota = (data.get("quotas") or [data])[0]
        thresholds = quota.get("thresholds") or {}
        return {
            "hard_limit": thresholds.get("hard"),
            "soft_limit": thresholds.get("soft"),
            "soft_grace": thresholds.get("soft_grace"),
        }

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
            cache_persisted = getattr(
                self,
                "_cache_persisted",
                getattr(self, "_session_cache_enabled", False),
            )
            if not cache_persisted:
                response = self.session.delete(self._session_url, timeout=15)
                raise_for_device_status(
                    response,
                    logger=self,
                    context="[IsilonClient] Logout failed",
                )
        except requests.RequestException as exc:
            self._log(
                "warning",
                f"[IsilonClient] Logout error: {type(exc).__name__}",
            )
        finally:
            self.session.close()
