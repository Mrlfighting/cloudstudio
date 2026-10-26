"""QQ SMTP传输与HTML/纯文本渲染，真实发信仅发生在独立worker中。"""

import asyncio
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from uuid import UUID

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import get_mail_settings

templates = Environment(
    loader=FileSystemLoader(Path(__file__).with_name("templates")),
    autoescape=select_autoescape(["html", "xml"]),
)
SUBJECTS = {"welcome": "欢迎加入云上工坊！", "binding": "云上工坊 · 验证你的邮箱", "unbind": "云上工坊 · 邮箱解绑验证"}


def render(kind: str, recipient: str, payload: dict, job_id: UUID) -> EmailMessage:
    """同一任务固定Message-ID；模板转义所有变量，避免昵称或配置注入HTML。"""
    cfg = get_mail_settings()
    if kind not in SUBJECTS:
        raise ValueError("未知邮件模板")
    context = {**payload, "base_url": cfg.public_base_url.rstrip("/"), "support_email": cfg.support_email}
    message = EmailMessage()
    message["From"] = formataddr(("云上工坊", cfg.smtp_from))
    message["To"] = recipient
    message["Subject"] = SUBJECTS[kind]
    message["Message-ID"] = f"<{job_id}@{cfg.smtp_from.split('@')[-1]}>"
    message["Auto-Submitted"] = "auto-generated"
    message.set_content(templates.get_template(f"{kind}.txt").render(context))
    message.add_alternative(templates.get_template(f"{kind}.html").render(context), subtype="html")
    return message


async def send(kind: str, recipient: str, payload: dict, job_id: UUID) -> None:
    """使用整体超时、显式TLS和证书校验，不把授权码或SMTP正文写入异常日志。"""
    cfg = get_mail_settings()
    message = render(kind, recipient, payload, job_id)
    async with asyncio.timeout(cfg.smtp_timeout):
        await aiosmtplib.send(
            message,
            hostname=cfg.smtp_host,
            port=cfg.smtp_port,
            username=cfg.smtp_username or None,
            password=cfg.smtp_password.get_secret_value() or None,
            use_tls=cfg.smtp_use_tls,
            start_tls=cfg.smtp_start_tls,
            validate_certs=True,
            timeout=cfg.smtp_timeout,
        )
