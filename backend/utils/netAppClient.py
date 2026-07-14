# -*- coding: utf-8 -*-
import requests
from typing import List, Dict, Optional


class NetAppClient:
    """NetApp ONTAP REST API client (ONTAP 9.6+)."""

    def __init__(self, hostname: str, username: str, password: str, port: int = 443, logger=None, tls_verify=True):
        self.hostname = hostname
        self.port = port
        self.logger = logger
        self.base_url = f"https://{hostname}:{port}/api"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = tls_verify
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
                response.raise_for_status()
                data = response.json()
                records.extend(data.get('records', []))
                next_link = data.get('_links', {}).get('next', {}).get('href')
                if next_link:
                    url = f"https://{self.hostname}:{self.port}{next_link}"
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
        return self._get_all_records('storage/volumes', params={'fields': 'name,svm,aggregates,state,type,space,style'})

    def get_qtrees(self) -> List[Dict]:
        return self._get_all_records('storage/qtrees', params={'fields': 'name,volume,security_style,unix_permissions,statistics,svm'})

    def get_quota_reports(self) -> List[Dict]:
        return self._get_all_records('storage/quota/reports', params={'fields': 'volume,qtree,type,users,group,space,files,svm'})

    def close(self):
        if self.session:
            self.session.close()
