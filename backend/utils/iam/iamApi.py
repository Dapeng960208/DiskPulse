# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import requests

from crud.configCrud import get_storage_config
from models import User
from schemas.usersSchema import IamUser


class IamApi:
    def __init__(self, db, logger, type="storage"):
        self.db = db
        self.logger = logger
        self.config = None
        self.session_url = None
        self.account_url = None
        self.iam_api_url = None
        self.token = None

    def set_up(self):
        self.config = get_storage_config(db=self.db)
        self.iam_api_url = self.config.iam_url
        self.session_url = f"{self.iam_api_url}/accounts/login".replace("//", "/").replace(":/", "://")
        self.account_url = f"{self.iam_api_url}/accounts".replace("//", "/").replace(":/", "://")
        self._get_token()

    def _get_token(self):
        response = requests.post(
            url=self.session_url,
            json={"username": self.config.iam_account, "password": self.config.iam_password},
        )
        if response.status_code == 200:
            self.token = response.json().get("result")
        else:
            self.logger.error("Unable to get IAM token")

    def get_users(self):
        result = []
        self.set_up()
        if self.token is None:
            return result
        headers = {"Authorization": self.token}
        response = requests.get(url=self.account_url, headers=headers)
        if response.status_code != 200:
            return result
        user_infos = response.json().get("result", {}).get("content", [])
        for user_info in user_infos:
            extension = user_info.get("extensionAttributes") or {}
            rd_username = extension.get("rdUsername")
            if rd_username is None:
                continue
            department = (user_info.get("department") or {}).get("name")
            if department is None:
                department = extension.get("wxVendor") or (user_info.get("type") or {}).get("label")
            result.append(
                IamUser(
                    iam_id=user_info.get("id"),
                    rd_username=rd_username,
                    department=department,
                    avatar_url=user_info.get("avatarUrl"),
                    email=user_info.get("emailAddress"),
                    username=user_info.get("username"),
                )
            )
        return result

    def synchronize_user_data(self):
        iam_users = self.get_users()
        updated_at = datetime.now()
        if not iam_users:
            return
        for iam_user in iam_users:
            user_db = self.db.query(User).filter(User.rd_username == iam_user.rd_username).first()
            if not user_db:
                self.logger.warning("IAM user %s %s not in system", iam_user.username, iam_user.rd_username)
                continue
            for key, value in iam_user.model_dump(exclude={"rd_username"}).items():
                setattr(user_db, key, value)
            user_db.updated_at = updated_at
            user_db.user_type = 2
            user_db.quit_days = 0
            self.db.commit()
        quit_users = self.db.query(User).filter(User.updated_at < updated_at - timedelta(seconds=30)).all()
        for quit_user in quit_users:
            quit_user.quit_days = (datetime.now() - quit_user.updated_at).days
            if quit_user.user_type == 2:
                quit_user.user_type = 0
        self.db.commit()

    def initiating_bpm_process(self, data: dict):
        if self.token is None:
            self.set_up()
        if self.config.bpm_api_url is None or self.config.bpm_process_id is None:
            self.logger.warning("BPM api url is None or process id is None")
            return None
        headers = {"Authorization": self.token}
        data["processId"] = self.config.bpm_process_id
        response = requests.post(self.config.bpm_api_url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json().get("result")
        self.logger.warning(
            "initiating bpm process failed. status code:%s,response:%s,data:%s",
            response.status_code,
            response.json(),
            data,
        )
        return None
