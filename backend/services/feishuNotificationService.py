# -*- coding: utf-8 -*-
import httpx


class FeishuNotificationService:
    def __init__(self, config):
        self.config = dict(config or {})
        if self.config.get("enabled"):
            missing = [key for key in ("base_url", "app", "app_key") if not self.config.get(key)]
            if missing:
                raise ValueError(f"Missing Feishu configuration: {', '.join(missing)}")

    def __repr__(self):
        safe = {key: value for key, value in self.config.items() if key != "app_key"}
        return f"FeishuNotificationService({safe!r})"

    def send(self, *, usernames, title, paragraphs):
        if not self.config.get("enabled"):
            return []
        base_url = self.config["base_url"].rstrip("/")
        options = {
            "timeout": self.config.get("timeout_seconds", 5),
            "verify": self.config.get("tls_verify", True),
        }
        token_response = httpx.post(
            f"{base_url}/auth/token",
            json={"app": self.config["app"], "app_key": self.config["app_key"]},
            **options,
        )
        token_response.raise_for_status()
        body = token_response.json()
        token = body.get("access_token") or body.get("token") or body.get("data", {}).get("access_token")
        if not token:
            raise ValueError("Feishu token response did not include access_token")
        results = []
        for username in usernames:
            response = httpx.post(
                f"{base_url}/send_info",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "username": username,
                    "msg_type": "post",
                    "title": title,
                    "paragraphs": paragraphs,
                },
                **options,
            )
            response.raise_for_status()
            result = response.json()
            if result.get("code") not in (None, 0, 200):
                raise ValueError(f"Feishu send failed with code {result.get('code')}")
            results.append(result)
        return results
