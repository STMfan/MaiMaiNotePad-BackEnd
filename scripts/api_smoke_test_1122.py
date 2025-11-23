#!/usr/bin/env python3
"""
MaiMaiNotePad 后端 API 烟测脚本。

本脚本测试 `docs/API.md` 中描述的公共/系统、认证、知识库、
人设卡、用户收藏记录、审核管理和消息管理端点。

使用示例:

    python scripts/api_smoke_test.py \\
        --base-url http://localhost:9278 \\
        --username your-user \\
        --password your-pass \\
        --email your-user@example.com

可选标志允许您选择实际发送邮件或需要一次性验证码的流程。

注意：审核端点需要 admin 或 moderator 角色。消息端点
使用已认证用户进行测试。
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import textwrap
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


@dataclass
class TestResult:
    name: str
    method: str
    path: str
    outcome: str  # "passed" | "failed" | "skipped" - 测试结果状态
    status_code: Optional[int] = None
    message: str = ""
    duration: float = 0.0


class APITestRunner:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.base_url = args.base_url.rstrip("/")
        self.session = requests.Session()
        self.results: List[TestResult] = []
        self.token: Optional[str] = None
        self.current_user: Dict[str, Any] = {}
        self.knowledge_id: Optional[str] = None
        self.kb_file_ids: List[str] = []
        self.persona_id: Optional[str] = None
        self.persona_file_ids: List[str] = []
        self.run_tag = uuid.uuid4().hex[:8]

    # ------------------------------------------------------------------ 辅助方法
    def _record(
        self,
        *,
        name: str,
        method: str,
        path: str,
        outcome: str,
        status_code: Optional[int] = None,
        message: str = "",
        duration: float = 0.0,
    ) -> None:
        self.results.append(
            TestResult(
                name=name,
                method=method,
                path=path,
                outcome=outcome,
                status_code=status_code,
                message=message.strip(),
                duration=duration,
            )
        )
        if self.args.verbose:
            prefix = {
                "passed": "[PASS]",
                "failed": "[FAIL]",
                "skipped": "[SKIP]",
            }.get(outcome, "[INFO]")
            detail = f"{prefix} {name} -> {method} {path}"
            if status_code is not None:
                detail += f" [{status_code}]"
            if message:
                detail += f" :: {message}"
            print(detail)

    def skip(self, name: str, method: str, path: str, reason: str) -> None:
        self._record(
            name=name,
            method=method,
            path=path,
            outcome="skipped",
            message=reason,
        )

    def _request(
        self,
        method: str,
        path: str,
        name: str,
        *,
        require_auth: bool = False,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> Optional[requests.Response]:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        if require_auth:
            if not self.token:
                self.skip(name, method, path, "缺少访问令牌")
                return None
            headers = {**headers, "Authorization": f"Bearer {self.token}"}

        start = time.perf_counter()
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.args.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            self._record(
                name=name,
                method=method,
                path=path,
                outcome="failed",
                message=str(exc),
            )
            return None
        duration = time.perf_counter() - start

        ok = response.ok if expected_status is None else response.status_code == expected_status
        snippet = self._extract_snippet(response)
        outcome = "passed" if ok else "failed"
        status_msg = snippet if snippet else response.reason
        self._record(
            name=name,
            method=method,
            path=path,
            outcome=outcome,
            status_code=response.status_code,
            message=status_msg,
            duration=duration,
        )
        if not ok:
            return None
        return response

    def _extract_snippet(self, response: requests.Response) -> str:
        content_type = response.headers.get("content-type", "")
        if not content_type:
            return ""
        if "application/json" in content_type:
            try:
                data = response.json()
                text = str(data)
            except ValueError:
                text = response.text
        elif "text/" in content_type:
            text = response.text
        else:
            size = len(response.content)
            text = f"<binary {size} bytes>"
        return textwrap.shorten(text, width=200, placeholder="…")

    def _make_file(
        self,
        field: str,
        filename: str,
        content: str,
        mime: str,
    ) -> tuple:
        buffer = io.BytesIO(content.encode("utf-8"))
        return (field, (filename, buffer, mime))

    # ------------------------------------------------------------------ 测试套件
    def run(self) -> int:
        try:
            self.test_system_endpoints()
            self.test_auth_endpoints()
            self.test_user_info()
            self.test_knowledge_endpoints()
            self.test_persona_endpoints()
            self.test_user_star_records()
            self.test_review_endpoints()
            self.test_message_endpoints()
            self._print_summary()
            return 0 if not any(r.outcome == "failed" for r in self.results) else 1
        finally:
            self.session.close()

    # --------------------------- 独立测试组
    def test_system_endpoints(self) -> None:
        self._request("GET", "/", "GET /")
        self._request("GET", "/health", "GET /health")

    def test_auth_endpoints(self) -> None:
        if not self.args.username or not self.args.password:
            self.skip("POST /api/token", "POST", "/api/token", "缺少凭据")
            return

        login_resp = self._request(
            "POST",
            "/api/token",
            "POST /api/token (login)",
            json={"username": self.args.username, "password": self.args.password},
        )
        if login_resp and login_resp.ok:
            data = login_resp.json()
            self.token = data.get("access_token")

        if self.args.include_email_flows:
            email = self.args.email or f"smoke+{self.run_tag}@example.com"
            self._request(
                "POST",
                "/api/send_verification_code",
                "POST /api/send_verification_code",
                data={"email": email},
            )
            if self.args.email:
                self._request(
                    "POST",
                    "/api/send_reset_password_code",
                    "POST /api/send_reset_password_code",
                    data={"email": self.args.email},
                )
            else:
                self.skip(
                    "POST /api/send_reset_password_code",
                    "POST",
                    "/api/send_reset_password_code",
                    "需要 --email 参数以进行实际调用",
                )
        else:
            self.skip(
                "POST /api/send_verification_code",
                "POST",
                "/api/send_verification_code",
                "已跳过（使用 --include-email-flows 启用）",
            )
            self.skip(
                "POST /api/send_reset_password_code",
                "POST",
                "/api/send_reset_password_code",
                "已跳过（使用 --include-email-flows 启用）",
            )

        if self.args.run_registration:
            if not all(
                [
                    self.args.registration_username,
                    self.args.registration_password,
                    self.args.registration_email,
                    self.args.registration_code,
                ]
            ):
                self.skip(
                    "POST /api/user/register",
                    "POST",
                    "/api/user/register",
                    "注册字段不完整",
                )
            else:
                self._request(
                    "POST",
                    "/api/user/register",
                    "POST /api/user/register",
                    data={
                        "username": self.args.registration_username,
                        "password": self.args.registration_password,
                        "email": self.args.registration_email,
                        "verification_code": self.args.registration_code,
                    },
                )
        else:
            self.skip(
                "POST /api/user/register",
                "POST",
                "/api/user/register",
                "已跳过（传递 --run-registration 启用）",
            )

        if self.args.run_password_reset:
            if not all([self.args.email, self.args.reset_code, self.args.new_password]):
                self.skip(
                    "POST /api/reset_password",
                    "POST",
                    "/api/reset_password",
                    "重置流程需要 --email/--reset-code/--new-password",
                )
            else:
                self._request(
                    "POST",
                    "/api/reset_password",
                    "POST /api/reset_password",
                    data={
                        "email": self.args.email,
                        "verification_code": self.args.reset_code,
                        "new_password": self.args.new_password,
                    },
                )
        else:
            self.skip(
                "POST /api/reset_password",
                "POST",
                "/api/reset_password",
                "已跳过（传递 --run-password-reset 启用）",
            )

    def test_user_info(self) -> None:
        resp = self._request(
            "GET",
            "/api/users/me",
            "GET /api/users/me",
            require_auth=True,
        )
        if resp and resp.ok:
            self.current_user = resp.json()

    # --------------------------- 知识库流程
    def test_knowledge_endpoints(self) -> None:
        if not self.token:
            self._skip_knowledge_block("缺少令牌")
            return

        name = f"kb-smoke-{self.run_tag}"
        description = "烟测知识库"
        files = [
            self._make_file(
                "files",
                f"{name}.txt",
                "这是一个烟测知识库文件。",
                "text/plain",
            )
        ]
        upload_resp = self._request(
            "POST",
            "/api/knowledge/upload",
            "POST /api/knowledge/upload",
            require_auth=True,
            data={
                "name": name,
                "description": description,
                "copyright_owner": "smoke-tester",
            },
            files=files,
        )
        if upload_resp and upload_resp.ok:
            self.knowledge_id = upload_resp.json().get("id")

        self._request("GET", "/api/knowledge/public", "GET /api/knowledge/public")

        if not self.knowledge_id:
            self._skip_knowledge_dependents("上传失败")
            return

        kb_path = f"/api/knowledge/{self.knowledge_id}"
        detail_resp = self._request("GET", kb_path, f"GET {kb_path}", require_auth=False)
        if detail_resp and detail_resp.ok:
            files_info = detail_resp.json().get("files", [])
            self.kb_file_ids = [f.get("file_id") for f in files_info if f.get("file_id")]

        if self.current_user.get("id"):
            user_path = f"/api/knowledge/user/{self.current_user['id']}"
            self._request(
                "GET",
                user_path,
                f"GET {user_path}",
                require_auth=True,
            )
        else:
            self.skip(
                "GET /api/knowledge/user/{user_id}",
                "GET",
                "/api/knowledge/user/{user_id}",
                "缺少当前用户ID",
            )

        update_resp = self._request(
            "PUT",
            kb_path,
            f"PUT {kb_path}",
            require_auth=True,
            json={
                "description": f"{description} (updated at {time.strftime('%H:%M:%S')})",
            },
        )
        if update_resp and update_resp.ok:
            pass

        extra_file = self._make_file(
            "files",
            f"{name}-extra.txt",
            "知识库的附加文件。",
            "text/plain",
        )
        self._request(
            "POST",
            f"{kb_path}/files",
            f"POST {kb_path}/files",
            require_auth=True,
            files=[extra_file],
        )

        refreshed = self._request("GET", kb_path, f"GET {kb_path} (refresh)")
        if refreshed and refreshed.ok:
            files_info = refreshed.json().get("files", [])
            self.kb_file_ids = [f.get("file_id") for f in files_info if f.get("file_id")]

        if self.kb_file_ids:
            file_id = self.kb_file_ids[-1]
            self._request(
                "DELETE",
                f"{kb_path}/{file_id}",
                f"DELETE {kb_path}/{file_id}",
                require_auth=True,
            )
        else:
            self.skip(
                "DELETE /api/knowledge/{kb_id}/{file_id}",
                "DELETE",
                "/api/knowledge/{kb_id}/{file_id}",
                "没有可用的知识库文件ID",
            )

        self._request(
            "GET",
            f"{kb_path}/download",
            f"GET {kb_path}/download",
            require_auth=True,
            stream=True,
        )

        if self.kb_file_ids:
            file_id = self.kb_file_ids[0]
            self._request(
                "GET",
                f"{kb_path}/file/{file_id}",
                f"GET {kb_path}/file/{file_id}",
                require_auth=True,
                stream=True,
            )
        else:
            self.skip(
                "GET /api/knowledge/{kb_id}/file/{file_id}",
                "GET",
                "/api/knowledge/{kb_id}/file/{file_id}",
                "没有可用的知识库文件ID",
            )

        self._request(
            "POST",
            f"{kb_path}/star",
            f"POST {kb_path}/star",
            require_auth=True,
        )
        self._request(
            "DELETE",
            f"{kb_path}/star",
            f"DELETE {kb_path}/star",
            require_auth=True,
        )

        self._request(
            "DELETE",
            kb_path,
            f"DELETE {kb_path}",
            require_auth=True,
        )
        self.knowledge_id = None
        self.kb_file_ids.clear()

    def _skip_knowledge_block(self, reason: str) -> None:
        endpoints = [
            ("GET /api/knowledge/public", "GET", "/api/knowledge/public"),
            ("GET /api/knowledge/{kb_id}", "GET", "/api/knowledge/{kb_id}"),
            ("GET /api/knowledge/user/{user_id}", "GET", "/api/knowledge/user/{user_id}"),
            ("PUT /api/knowledge/{kb_id}", "PUT", "/api/knowledge/{kb_id}"),
            ("POST /api/knowledge/{kb_id}/files", "POST", "/api/knowledge/{kb_id}/files"),
            ("DELETE /api/knowledge/{kb_id}/{file_id}", "DELETE", "/api/knowledge/{kb_id}/{file_id}"),
            ("GET /api/knowledge/{kb_id}/download", "GET", "/api/knowledge/{kb_id}/download"),
            ("GET /api/knowledge/{kb_id}/file/{file_id}", "GET", "/api/knowledge/{kb_id}/file/{file_id}"),
            ("POST /api/knowledge/{kb_id}/star", "POST", "/api/knowledge/{kb_id}/star"),
            ("DELETE /api/knowledge/{kb_id}/star", "DELETE", "/api/knowledge/{kb_id}/star"),
            ("DELETE /api/knowledge/{kb_id}", "DELETE", "/api/knowledge/{kb_id}"),
        ]
        for name, method, path in endpoints:
            self.skip(name, method, path, reason)

    def _skip_knowledge_dependents(self, reason: str) -> None:
        endpoints = [
            ("GET /api/knowledge/{kb_id}", "GET", "/api/knowledge/{kb_id}"),
            ("GET /api/knowledge/user/{user_id}", "GET", "/api/knowledge/user/{user_id}"),
            ("PUT /api/knowledge/{kb_id}", "PUT", "/api/knowledge/{kb_id}"),
            ("POST /api/knowledge/{kb_id}/files", "POST", "/api/knowledge/{kb_id}/files"),
            ("DELETE /api/knowledge/{kb_id}/{file_id}", "DELETE", "/api/knowledge/{kb_id}/{file_id}"),
            ("GET /api/knowledge/{kb_id}/download", "GET", "/api/knowledge/{kb_id}/download"),
            ("GET /api/knowledge/{kb_id}/file/{file_id}", "GET", "/api/knowledge/{kb_id}/file/{file_id}"),
            ("POST /api/knowledge/{kb_id}/star", "POST", "/api/knowledge/{kb_id}/star"),
            ("DELETE /api/knowledge/{kb_id}/star", "DELETE", "/api/knowledge/{kb_id}/star"),
            ("DELETE /api/knowledge/{kb_id}", "DELETE", "/api/knowledge/{kb_id}"),
        ]
        for name, method, path in endpoints:
            self.skip(name, method, path, reason)

    # --------------------------- 人设卡流程
    def test_persona_endpoints(self) -> None:
        if not self.token:
            self._skip_persona_block("缺少令牌")
            return

        name = f"pc-smoke-{self.run_tag}"
        description = "烟测人设卡"
        toml_content = textwrap.dedent(
            f"""
            [profile]
            name = "{name}"
            description = "{description}"
            """
        ).strip()
        files = [
            self._make_file(
                "files",
                f"{name}.toml",
                toml_content,
                "application/toml",
            )
        ]
        upload_resp = self._request(
            "POST",
            "/api/persona/upload",
            "POST /api/persona/upload",
            require_auth=True,
            data={
                "name": name,
                "description": description,
                "copyright_owner": "smoke-tester",
            },
            files=files,
        )
        if upload_resp and upload_resp.ok:
            self.persona_id = upload_resp.json().get("id")

        self._request("GET", "/api/persona/public", "GET /api/persona/public")

        if not self.persona_id:
            self._skip_persona_dependents("上传失败")
            return

        pc_path = f"/api/persona/{self.persona_id}"
        detail_resp = self._request("GET", pc_path, f"GET {pc_path}")
        if detail_resp and detail_resp.ok:
            files_info = detail_resp.json().get("files", [])
            self.persona_file_ids = [f.get("file_id") for f in files_info if f.get("file_id")]

        if self.current_user.get("id"):
            user_path = f"/api/persona/user/{self.current_user['id']}"
            self._request(
                "GET",
                user_path,
                f"GET {user_path}",
                require_auth=True,
            )
        else:
            self.skip(
                "GET /api/persona/user/{user_id}",
                "GET",
                "/api/persona/user/{user_id}",
                "缺少当前用户ID",
            )

        self._request(
            "PUT",
            pc_path,
            f"PUT {pc_path}",
            require_auth=True,
            data={
                "name": name,
                "description": f"{description} (updated at {time.strftime('%H:%M:%S')})",
            },
        )

        extra_toml = self._make_file(
            "files",
            f"{name}-extra.toml",
            toml_content + "\nnotes = \"extra\"",
            "application/toml",
        )
        self._request(
            "POST",
            f"{pc_path}/files",
            f"POST {pc_path}/files",
            require_auth=True,
            files=[extra_toml],
        )

        refreshed = self._request("GET", pc_path, f"GET {pc_path} (refresh)")
        if refreshed and refreshed.ok:
            files_info = refreshed.json().get("files", [])
            self.persona_file_ids = [
                f.get("file_id") for f in files_info if f.get("file_id")
            ]

        if self.persona_file_ids:
            file_id = self.persona_file_ids[-1]
            self._request(
                "DELETE",
                f"{pc_path}/{file_id}",
                f"DELETE {pc_path}/{file_id}",
                require_auth=True,
            )
        else:
            self.skip(
                "DELETE /api/persona/{pc_id}/{file_id}",
                "DELETE",
                "/api/persona/{pc_id}/{file_id}",
                "没有可用的人设卡文件ID",
            )

        self._request(
                "GET",
                f"{pc_path}/download",
                f"GET {pc_path}/download",
                stream=True,
            )

        if self.persona_file_ids:
            file_id = self.persona_file_ids[0]
            self._request(
                "GET",
                f"{pc_path}/file/{file_id}",
                f"GET {pc_path}/file/{file_id}",
                require_auth=True,
                stream=True,
            )
        else:
            self.skip(
                "GET /api/persona/{pc_id}/file/{file_id}",
                "GET",
                "/api/persona/{pc_id}/file/{file_id}",
                "没有可用的人设卡文件ID",
            )

        self._request(
            "POST",
            f"{pc_path}/star",
            f"POST {pc_path}/star",
            require_auth=True,
        )
        self._request(
            "DELETE",
            f"{pc_path}/star",
            f"DELETE {pc_path}/star",
            require_auth=True,
        )

        self._request(
            "DELETE",
            pc_path,
            f"DELETE {pc_path}",
            require_auth=True,
        )
        self.persona_id = None
        self.persona_file_ids.clear()

    def _skip_persona_block(self, reason: str) -> None:
        endpoints = [
            ("GET /api/persona/public", "GET", "/api/persona/public"),
            ("GET /api/persona/{pc_id}", "GET", "/api/persona/{pc_id}"),
            ("GET /api/persona/user/{user_id}", "GET", "/api/persona/user/{user_id}"),
            ("PUT /api/persona/{pc_id}", "PUT", "/api/persona/{pc_id}"),
            ("POST /api/persona/{pc_id}/files", "POST", "/api/persona/{pc_id}/files"),
            ("DELETE /api/persona/{pc_id}/{file_id}", "DELETE", "/api/persona/{pc_id}/{file_id}"),
            ("GET /api/persona/{pc_id}/download", "GET", "/api/persona/{pc_id}/download"),
            ("GET /api/persona/{pc_id}/file/{file_id}", "GET", "/api/persona/{pc_id}/file/{file_id}"),
            ("POST /api/persona/{pc_id}/star", "POST", "/api/persona/{pc_id}/star"),
            ("DELETE /api/persona/{pc_id}/star", "DELETE", "/api/persona/{pc_id}/star"),
            ("DELETE /api/persona/{pc_id}", "DELETE", "/api/persona/{pc_id}"),
        ]
        for name, method, path in endpoints:
            self.skip(name, method, path, reason)

    def _skip_persona_dependents(self, reason: str) -> None:
        endpoints = [
            ("GET /api/persona/{pc_id}", "GET", "/api/persona/{pc_id}"),
            ("GET /api/persona/user/{user_id}", "GET", "/api/persona/user/{user_id}"),
            ("PUT /api/persona/{pc_id}", "PUT", "/api/persona/{pc_id}"),
            ("POST /api/persona/{pc_id}/files", "POST", "/api/persona/{pc_id}/files"),
            ("DELETE /api/persona/{pc_id}/{file_id}", "DELETE", "/api/persona/{pc_id}/{file_id}"),
            ("GET /api/persona/{pc_id}/download", "GET", "/api/persona/{pc_id}/download"),
            ("GET /api/persona/{pc_id}/file/{file_id}", "GET", "/api/persona/{pc_id}/file/{file_id}"),
            ("POST /api/persona/{pc_id}/star", "POST", "/api/persona/{pc_id}/star"),
            ("DELETE /api/persona/{pc_id}/star", "DELETE", "/api/persona/{pc_id}/star"),
            ("DELETE /api/persona/{pc_id}", "DELETE", "/api/persona/{pc_id}"),
        ]
        for name, method, path in endpoints:
            self.skip(name, method, path, reason)

    # --------------------------- 收藏记录
    def test_user_star_records(self) -> None:
        self._request(
            "GET",
            "/api/user/stars",
            "GET /api/user/stars",
            require_auth=bool(self.token),
        )

    # --------------------------- review endpoints
    def test_review_endpoints(self) -> None:
        """测试审核管理相关端点（需要admin或moderator权限）"""
        if not self.token:
            self._skip_review_block("缺少令牌")
            return

        # 检查用户是否有审核权限（需要admin或moderator角色）
        # 如果没有权限，这些测试会被跳过
        user_info = self.current_user
        user_role = user_info.get("role", "user") if user_info else "user"
        
        if user_role not in ["admin", "moderator"]:
            self._skip_review_block(f"用户角色 '{user_role}' 缺少审核权限")
            return

        # 获取待审核知识库
        pending_kb_resp = self._request(
            "GET",
            "/api/review/knowledge/pending",
            "GET /api/review/knowledge/pending",
            require_auth=True,
        )
        
        # 获取待审核人设卡
        pending_pc_resp = self._request(
            "GET",
            "/api/review/persona/pending",
            "GET /api/review/persona/pending",
            require_auth=True,
        )

        # 如果有待审核的知识库，测试审核操作
        if pending_kb_resp and pending_kb_resp.ok:
            pending_kbs = pending_kb_resp.json()
            if pending_kbs and len(pending_kbs) > 0:
                # 测试审核通过（使用第一个）
                test_kb_id = pending_kbs[0].get("id")
                if test_kb_id:
                    self._request(
                        "POST",
                        f"/api/review/knowledge/{test_kb_id}/approve",
                        f"POST /api/review/knowledge/{test_kb_id}/approve",
                        require_auth=True,
                    )
                
                # 如果有第二个待审核的知识库，测试拒绝操作
                if len(pending_kbs) > 1:
                    test_kb_id_reject = pending_kbs[1].get("id")
                    if test_kb_id_reject:
                        self._request(
                            "POST",
                            f"/api/review/knowledge/{test_kb_id_reject}/reject",
                            f"POST /api/review/knowledge/{test_kb_id_reject}/reject",
                            require_auth=True,
                            json={"reason": "烟测拒绝原因：测试审核拒绝功能"},
                        )
                    else:
                        self.skip(
                            "POST /api/review/knowledge/{kb_id}/reject",
                            "POST",
                            "/api/review/knowledge/{kb_id}/reject",
                            "没有可用的知识库ID用于测试拒绝",
                        )
                else:
                    self.skip(
                        "POST /api/review/knowledge/{kb_id}/reject",
                        "POST",
                        "/api/review/knowledge/{kb_id}/reject",
                        "需要至少2个待审核的知识库才能同时测试通过和拒绝",
                    )
            else:
                self.skip(
                    "POST /api/review/knowledge/{kb_id}/approve",
                    "POST",
                    "/api/review/knowledge/{kb_id}/approve",
                    "没有待审核的知识库",
                )
                self.skip(
                    "POST /api/review/knowledge/{kb_id}/reject",
                    "POST",
                    "/api/review/knowledge/{kb_id}/reject",
                    "没有待审核的知识库",
                )
        else:
            self.skip(
                "POST /api/review/knowledge/{kb_id}/approve",
                "POST",
                "/api/review/knowledge/{kb_id}/approve",
                "无法获取待审核的知识库",
            )
            self.skip(
                "POST /api/review/knowledge/{kb_id}/reject",
                "POST",
                "/api/review/knowledge/{kb_id}/reject",
                "无法获取待审核的知识库",
            )

        # 如果有待审核的人设卡，测试审核操作
        if pending_pc_resp and pending_pc_resp.ok:
            pending_pcs = pending_pc_resp.json()
            if pending_pcs and len(pending_pcs) > 0:
                # 测试审核通过（使用第一个）
                test_pc_id = pending_pcs[0].get("id")
                if test_pc_id:
                    self._request(
                        "POST",
                        f"/api/review/persona/{test_pc_id}/approve",
                        f"POST /api/review/persona/{test_pc_id}/approve",
                        require_auth=True,
                    )
                
                # 如果有第二个待审核的人设卡，测试拒绝操作
                if len(pending_pcs) > 1:
                    test_pc_id_reject = pending_pcs[1].get("id")
                    if test_pc_id_reject:
                        self._request(
                            "POST",
                            f"/api/review/persona/{test_pc_id_reject}/reject",
                            f"POST /api/review/persona/{test_pc_id_reject}/reject",
                            require_auth=True,
                            json={"reason": "烟测拒绝原因：测试审核拒绝功能"},
                        )
                    else:
                        self.skip(
                            "POST /api/review/persona/{pc_id}/reject",
                            "POST",
                            "/api/review/persona/{pc_id}/reject",
                            "没有可用的人设卡ID用于测试拒绝",
                        )
                else:
                    self.skip(
                        "POST /api/review/persona/{pc_id}/reject",
                        "POST",
                        "/api/review/persona/{pc_id}/reject",
                        "需要至少2个待审核的人设卡才能同时测试通过和拒绝",
                    )
            else:
                self.skip(
                    "POST /api/review/persona/{pc_id}/approve",
                    "POST",
                    "/api/review/persona/{pc_id}/approve",
                    "没有待审核的人设卡",
                )
                self.skip(
                    "POST /api/review/persona/{pc_id}/reject",
                    "POST",
                    "/api/review/persona/{pc_id}/reject",
                    "没有待审核的人设卡",
                )
        else:
            self.skip(
                "POST /api/review/persona/{pc_id}/approve",
                "POST",
                "/api/review/persona/{pc_id}/approve",
                "无法获取待审核的人设卡",
            )
            self.skip(
                "POST /api/review/persona/{pc_id}/reject",
                "POST",
                "/api/review/persona/{pc_id}/reject",
                "无法获取待审核的人设卡",
            )

    def _skip_review_block(self, reason: str) -> None:
        endpoints = [
            ("GET /api/review/knowledge/pending", "GET", "/api/review/knowledge/pending"),
            ("GET /api/review/persona/pending", "GET", "/api/review/persona/pending"),
            ("POST /api/review/knowledge/{kb_id}/approve", "POST", "/api/review/knowledge/{kb_id}/approve"),
            ("POST /api/review/knowledge/{kb_id}/reject", "POST", "/api/review/knowledge/{kb_id}/reject"),
            ("POST /api/review/persona/{pc_id}/approve", "POST", "/api/review/persona/{pc_id}/approve"),
            ("POST /api/review/persona/{pc_id}/reject", "POST", "/api/review/persona/{pc_id}/reject"),
        ]
        for name, method, path in endpoints:
            self.skip(name, method, path, reason)

    # --------------------------- message endpoints
    def test_message_endpoints(self) -> None:
        """测试消息管理相关端点"""
        if not self.token:
            self._skip_message_block("缺少令牌")
            return

        sender_id = self.current_user.get("id", "") if self.current_user else ""
        if not sender_id:
            self._skip_message_block("缺少当前用户ID")
            return

        # 测试发送消息（需要另一个用户ID，这里使用自己作为接收者进行测试）
        message_resp = self._request(
            "POST",
            "/api/messages/send",
            "POST /api/messages/send",
            require_auth=True,
            json={
                "recipient_id": sender_id,  # 发送给自己用于测试
                "title": f"烟测消息 {self.run_tag}",
                "content": "这是一条烟测消息。",
                "message_type": "direct",
            },
        )

        message_id = None
        if message_resp and message_resp.ok:
            result = message_resp.json()
            message_ids = result.get("message_ids", [])
            if message_ids:
                message_id = message_ids[0]

        # 测试获取消息列表
        self._request(
            "GET",
            "/api/messages",
            "GET /api/messages",
            require_auth=True,
            params={"limit": 10, "offset": 0},
        )

        # 测试获取与特定用户的对话（使用自己）
        self._request(
            "GET",
            "/api/messages",
            "GET /api/messages?other_user_id={sender_id}",
            require_auth=True,
            params={"other_user_id": sender_id, "limit": 10, "offset": 0},
        )

        # 测试标记消息为已读
        if message_id:
            self._request(
                "POST",
                f"/api/messages/{message_id}/read",
                f"POST /api/messages/{message_id}/read",
                require_auth=True,
            )
        else:
            self.skip(
                "POST /api/messages/{message_id}/read",
                "POST",
                "/api/messages/{message_id}/read",
                "发送测试中没有可用的消息ID",
            )

        # 测试发送公告（需要admin权限，可选）
        user_role = self.current_user.get("role", "user") if self.current_user else "user"
        if user_role in ["admin", "moderator"]:
            # 测试发送给特定用户列表的公告
            self._request(
                "POST",
                "/api/messages/send",
                "POST /api/messages/send (announcement to list)",
                require_auth=True,
                json={
                    "recipient_ids": [sender_id],
                    "title": f"烟测公告 {self.run_tag}",
                    "content": "这是一条烟测公告。",
                    "message_type": "announcement",
                },
            )
        else:
            self.skip(
                "POST /api/messages/send (announcement)",
                "POST",
                "/api/messages/send",
                "发送公告需要 admin/moderator 角色",
            )

    def _skip_message_block(self, reason: str) -> None:
        endpoints = [
            ("POST /api/messages/send", "POST", "/api/messages/send"),
            ("GET /api/messages", "GET", "/api/messages"),
            ("POST /api/messages/{message_id}/read", "POST", "/api/messages/{message_id}/read"),
        ]
        for name, method, path in endpoints:
            self.skip(name, method, path, reason)

    # --------------------------- 总结
    def _print_summary(self) -> None:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.outcome == "passed")
        failed = sum(1 for r in self.results if r.outcome == "failed")
        skipped = sum(1 for r in self.results if r.outcome == "skipped")

        print("\n=== API 烟测总结 ===")
        print(f"总计: {total} | 通过: {passed} | 失败: {failed} | 跳过: {skipped}")

        if not self.args.verbose:
            print("\n失败 / 跳过的步骤:")
            for result in self.results:
                if result.outcome in {"failed", "skipped"}:
                    msg = result.message or ""
                    print(f" - [{result.outcome.upper()}] {result.name} -> {msg}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MaiMaiNotePad API 烟测工具")
    parser.add_argument("--base-url", default=os.getenv("MAIMNP_BASE_URL", "http://0.0.0.0:9278"))
    parser.add_argument("--username", default=os.getenv("MAIMNP_USERNAME"))
    parser.add_argument("--password", default=os.getenv("MAIMNP_PASSWORD"))
    parser.add_argument("--email", default=os.getenv("MAIMNP_EMAIL"))
    parser.add_argument("--timeout", type=float, default=15.0, help="每个请求的超时时间（秒）")
    parser.add_argument("--include-email-flows", action="store_true", help="实际调用邮件/验证端点")

    parser.add_argument("--run-registration", action="store_true", help="测试 /api/user/register 端点")
    parser.add_argument("--registration-username")
    parser.add_argument("--registration-password")
    parser.add_argument("--registration-email")
    parser.add_argument("--registration-code", help="/api/user/register 所需的验证码")

    parser.add_argument("--run-password-reset", action="store_true", help="测试 /api/reset_password 端点")
    parser.add_argument("--reset-code", help="密码重置的验证码")
    parser.add_argument("--new-password", help="运行重置流程时的新密码")

    parser.add_argument("--verbose", action="store_true", help="打印每个步骤的结果")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    runner = APITestRunner(args)
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())

