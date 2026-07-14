"""通过 SMTP 发送本地生成的报告。"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol


class SmtpTransport(Protocol):
    """可替换的邮件传输协议，便于离线测试。"""

    def send(self, message: EmailMessage) -> None:
        """发送已组装好的邮件。"""


class SmtpEmailTransport:
    """基于标准库 SMTP STARTTLS 的邮件传输实现。"""

    def __init__(
        self, host: str, port: int, username: str, password: str, *, use_ssl: bool = False
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_ssl = use_ssl

    def send(self, message: EmailMessage) -> None:
        """经加密连接认证后发送邮件。"""
        client_type = smtplib.SMTP_SSL if self._use_ssl else smtplib.SMTP
        with client_type(self._host, self._port, timeout=20) as client:
            if not self._use_ssl:
                client.starttls(context=ssl.create_default_context())
            client.login(self._username, self._password)
            client.send_message(message)


class EmailReportSender:
    """将本地 Markdown 简报以附件形式发送给指定收件人。"""

    def __init__(self, transport: SmtpTransport, sender: str, recipients: tuple[str, ...]) -> None:
        if not recipients:
            raise ValueError("至少需要一个收件人")
        self._transport = transport
        self._sender = sender
        self._recipients = recipients

    def send_markdown_report(self, report_path: Path, *, subject: str) -> None:
        """发送 UTF-8 Markdown 附件，不在邮件正文重复报告内容。"""
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._sender
        message["To"] = ", ".join(self._recipients)
        message.set_content("本邮件附有自动生成的研究与复盘简报。")
        message.add_attachment(
            report_path.read_bytes(),
            maintype="text",
            subtype="markdown",
            filename=report_path.name,
        )
        self._transport.send(message)
