# -*- coding: utf-8 -*-
import requests
import time
from typing import List, Dict, Optional

from utils.storageDeviceHttp import raise_for_device_status


class NetAppClient:
    """NetApp ONTAP REST API client (ONTAP 9.6+)."""

    def __init__(self, hostname: str, username: str, password: str, port: int = 443,
                 logger=None, protocol: str = "https", tls_verify=True):
        if protocol not in ("http", "https"):
            raise ValueError(f"Unsupported storage protocol: {protocol}")
        self.hostname = hostname
        self.port = port
        self.logger = logger
        self.origin = f"{protocol}://{hostname}:{port}"
        self.base_url = f"{self.origin}/api"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = tls_verify if protocol == "https" else False
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _get_all_records(self, endpoint: str, params: Dict = None) -> List[Dict]:
        """Fetch all records with automatic pagination."""
        params = params or {}
        params.setdefault('max_records', 1000)
        records = []
        url = f"{self.base_url}/{endpoint}"

        while url:
            try:
                response = self.session.get(url, params=params, timeout=60)
                raise_for_device_status(
                    response,
                    logger=self.logger,
                    context=f"[Storage_Pulse] NetApp GET {endpoint} failed",
                )
                data = response.json()
                records.extend(data.get('records', []))
                next_link = data.get('_links', {}).get('next', {}).get('href')
                if next_link:
                    url = f"{self.origin}{next_link}"
                    params = {}
                else:
                    url = None
            except requests.exceptions.ConnectionError as e:
                if self.logger:
                    self.logger.error(f"[Storage_Pulse] NetApp API connection failed for endpoint '{endpoint}': {e}")
                raise
            except requests.exceptions.HTTPError as e:
                if self.logger:
                    self.logger.error(f"[Storage_Pulse] NetApp API HTTP error for endpoint '{endpoint}': {e}")
                raise
            except Exception as e:
                if self.logger:
                    self.logger.error(f"[Storage_Pulse] NetApp API request failed for endpoint '{endpoint}': {e}")
                raise

        return records

    def get_aggregates(self) -> List[Dict]:
        return self._get_all_records('storage/aggregates', params={'fields': 'name,space'})

    def get_volumes(self) -> List[Dict]:
        return self._get_all_records('storage/volumes', params={'fields': 'uuid,name,svm,aggregates,state,type,space,style'})

    def get_qtrees(self) -> List[Dict]:
        return self._get_all_records('storage/qtrees', params={'fields': 'name,volume,security_style,unix_permissions,statistics,svm'})

    def get_quota_reports(self) -> List[Dict]:
        return self._get_all_records('storage/quota/reports', params={'fields': 'volume,qtree,type,users,group,space,files,svm'})

    def get_ems_events(self, since: str) -> List[Dict]:
        return self._get_all_records(
            'support/ems/events',
            params={
                'time': f'>={since}',
                'fields': 'time,index,message,node,log_message',
            },
        )

    def get_volume_metrics(self) -> List[Dict]:
        return self._get_all_records(
            'storage/volumes',
            params={'fields': 'uuid,name,metric'},
        )

    def _write(self, method: str, endpoint: str, payload: Dict) -> Dict:
        response = getattr(self.session, method)(
            f"{self.base_url}/{endpoint}",
            params={"return_timeout": 120},
            json=payload,
            timeout=120,
        )
        raise_for_device_status(
            response,
            logger=self.logger,
            context=f"[Storage_Pulse] NetApp {method.upper()} {endpoint} failed",
        )
        data = response.json() if response.content else {}
        if response.status_code == 202:
            job_uuid = (data.get("job") or {}).get("uuid")
            if not job_uuid:
                raise RuntimeError("NetApp quota update returned an unknown job")
            self._wait_for_job(job_uuid)
        return data

    def _wait_for_job(self, job_uuid: str) -> None:
        for _ in range(120):
            response = self.session.get(
                f"{self.base_url}/cluster/jobs/{job_uuid}", timeout=60
            )
            raise_for_device_status(
                response,
                logger=self.logger,
                context=f"[Storage_Pulse] NetApp GET cluster/jobs/{job_uuid} failed",
            )
            state = response.json().get("state")
            if state == "success":
                return
            if state in {"failure", "paused"}:
                raise RuntimeError("NetApp quota update job failed")
            time.sleep(1)
        raise TimeoutError("NetApp quota update job timed out")

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
        if soft_grace is not None:
            raise ValueError("NetApp quotas do not support per-rule soft grace")
        params = {
            "fields": "uuid,volume,qtree,type,users,space",
            "volume.name": volume_name,
            "type": quota_type,
        }
        if qtree_name is not None:
            params["qtree.name"] = qtree_name
        if username is not None:
            params["users.name"] = username
        rules = self._get_all_records("storage/quota/rules", params=params)
        limits = {
            "hard_limit": hard_limit,
            "soft_limit": soft_limit if soft_limit is not None else -1,
        }
        if rules:
            self._write("patch", f"storage/quota/rules/{rules[0]['uuid']}", {"space": limits})
        else:
            payload = {
                "type": quota_type,
                "volume": {"name": volume_name},
                "qtree": {"name": qtree_name or ""},
                "space": limits,
            }
            if username is not None:
                payload["users"] = [{"name": username}]
            self._write("post", "storage/quota/rules", payload)

        report_params = {
            "fields": "volume,qtree,type,users,space",
            "volume.name": volume_name,
            "type": quota_type,
        }
        if qtree_name is not None:
            report_params["qtree.name"] = qtree_name
        if username is not None:
            report_params["users.name"] = username
        reports = self._get_all_records("storage/quota/reports", params=report_params)
        if not reports:
            raise RuntimeError("NetApp quota readback failed")
        space = reports[0].get("space") or {}
        return {
            "hard_limit": space.get("hard_limit"),
            "soft_limit": space.get("soft_limit"),
            "soft_grace": None,
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
        params = {
            "fields": "volume,qtree,type,users,space",
            "volume.name": volume_name,
            "type": quota_type,
        }
        if qtree_name is not None:
            params["qtree.name"] = qtree_name
        if username is not None:
            params["users.name"] = username
        reports = self._get_all_records("storage/quota/reports", params=params)
        if not reports:
            raise RuntimeError("NetApp quota readback failed")
        space = reports[0].get("space") or {}
        return {"hard_limit": space.get("hard_limit"), "soft_limit": space.get("soft_limit"), "soft_grace": None}

    def read_volume_capacity(self, *, volume_name: str) -> Dict:
        volumes = self._get_all_records(
            "storage/volumes", params={"name": volume_name, "fields": "uuid,name,size"},
        )
        if not volumes or volumes[0].get("size") is None:
            raise RuntimeError("NetApp volume readback failed")
        return {"hard_limit": volumes[0]["size"], "soft_limit": None, "soft_grace": None}

    def update_volume_capacity(self, *, volume_name: str, hard_limit: float) -> Dict:
        volumes = self._get_all_records(
            "storage/volumes",
            params={"name": volume_name, "fields": "uuid,name,size"},
        )
        if not volumes:
            raise RuntimeError("NetApp volume not found")
        self._write(
            "patch",
            f"storage/volumes/{volumes[0]['uuid']}",
            {"size": hard_limit},
        )
        current = self._get_all_records(
            "storage/volumes",
            params={"name": volume_name, "fields": "uuid,name,size"},
        )
        if not current or current[0].get("size") != hard_limit:
            raise RuntimeError("NetApp volume capacity readback failed")
        return {"hard_limit": current[0]["size"], "soft_limit": None}

    def close(self):
        if self.session:
            self.session.close()
