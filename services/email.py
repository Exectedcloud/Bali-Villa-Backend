import logging
import sys

import resend
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── shared HTML helpers ──────────────────────────────────────────────────────

def _btn(label: str, url: str) -> str:
    return (
        f'<a href="{url}" style="display:inline-block;background:#1F6B5C;color:#fff;'
        f'text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:600;'
        f'font-size:15px">{label}</a>'
    )

def _wrap(body: str) -> str:
    return (
        '<!DOCTYPE html><html><body style="margin:0;padding:40px 0;background:#FAFAF7;'
        'font-family:Inter,system-ui,sans-serif">'
        '<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;'
        'border:1px solid #E5E3DD;padding:40px">'
        + body
        + '<hr style="border:none;border-top:1px solid #E5E3DD;margin:28px 0">'
        '<p style="color:#9BB8B0;font-size:12px;margin:0">BaliVilla &mdash; 巴厘岛别墅，中文预订</p>'
        '</div></body></html>'
    )


# ─── core send ────────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, html: str, text: str = None) -> bool:
    """Send email via Resend. Always prints to terminal as fallback.
    Returns True on successful Resend delivery, False otherwise."""

    plain = text or subject
    log_line = f'\n[EMAIL] To: {to}\n[EMAIL] Subject: {subject}\n[EMAIL] Body:\n{plain}\n'
    try:
        print(log_line, flush=True)
    except UnicodeEncodeError:
        # Windows terminals with non-UTF-8 encoding (cp1252, etc.)
        sys.stdout.buffer.write(log_line.encode('utf-8', errors='replace'))
        sys.stdout.buffer.flush()

    if not settings.RESEND_API_KEY:
        logger.warning('RESEND_API_KEY not set — email printed to terminal only')
        return False

    # In development, Resend sandbox only delivers to the account owner's email.
    # Set EMAIL_TEST_OVERRIDE in .env to redirect ALL emails to that address.
    override = getattr(settings, 'EMAIL_TEST_OVERRIDE', '') or ''
    actual_to = override if override else (to if isinstance(to, list) else [to])
    if override:
        logger.info('EMAIL_TEST_OVERRIDE active — redirecting email for %s to %s', to, override)

    try:
        resend.api_key = settings.RESEND_API_KEY
        params: resend.Emails.SendParams = {
            'from': settings.DEFAULT_FROM_EMAIL,
            'to': [actual_to] if isinstance(actual_to, str) else actual_to,
            'subject': subject,
            'html': html,
        }
        if text:
            params['text'] = text
        resend.Emails.send(params)
        return True
    except Exception as exc:
        logger.error('Resend delivery failed for %s: %s', to, exc)
        return False


# ─── verification email ───────────────────────────────────────────────────────

def send_verification_email(user, base_url: str = None) -> bool:
    root = base_url or settings.FRONTEND_URL
    url = f"{root}/verify-email?uid={user.id}&token={user.email_verification_token}"
    html = _wrap(
        '<h2 style="font-family:Georgia,serif;color:#1A1A1A;margin:0 0 6px">欢迎来到 BaliVilla</h2>'
        '<p style="font-family:Georgia,serif;color:#767676;font-style:italic;margin:0 0 24px">'
        'Welcome to BaliVilla</p>'
        '<p style="color:#4A4A4A;line-height:1.7;margin:0 0 8px">'
        '请点击下方按钮验证您的邮箱地址，完成账号注册：</p>'
        '<p style="color:#767676;line-height:1.6;margin:0 0 24px">'
        'Click the button below to verify your email address and complete registration:</p>'
        + _btn('验证邮箱 · Verify Email', url)
        + '<p style="color:#767676;font-size:13px;margin:24px 0 0">'
        '此链接24小时内有效。<br>This link is valid for 24 hours.</p>'
    )
    text = (
        f'验证您的 BaliVilla 邮箱 / Verify your BaliVilla email:\n{url}\n\n'
        '此链接24小时内有效 / This link is valid for 24 hours.'
    )
    return send_email(user.email, 'Welcome to BaliVilla — verify your email', html, text)


# ─── password reset email ─────────────────────────────────────────────────────

def send_password_reset_email(user, uid: str, token: str, base_url: str = None) -> bool:
    root = base_url or settings.FRONTEND_URL
    url = f"{root}/reset-password?uid={uid}&token={token}"
    html = _wrap(
        '<h2 style="font-family:Georgia,serif;color:#1A1A1A;margin:0 0 6px">重置您的 BaliVilla 密码</h2>'
        '<p style="font-family:Georgia,serif;color:#767676;font-style:italic;margin:0 0 24px">'
        'Reset your BaliVilla password</p>'
        '<p style="color:#4A4A4A;line-height:1.7;margin:0 0 8px">'
        '请点击下方按钮重置您的密码：</p>'
        '<p style="color:#767676;line-height:1.6;margin:0 0 24px">'
        'Click the button below to reset your password:</p>'
        + _btn('重置密码 · Reset Password', url)
        + '<p style="color:#767676;font-size:13px;margin:24px 0 0">'
        '此链接1小时内有效。<br>This link is valid for 1 hour.</p>'
        '<p style="color:#767676;font-size:13px;margin:8px 0 0">'
        '如果您没有请求重置密码，请忽略此邮件。<br>'
        "If you didn't request this, you can safely ignore this email.</p>"
    )
    text = (
        f'重置密码 / Reset your password:\n{url}\n\n'
        '如果您没有请求重置密码，请忽略此邮件。\n'
        "If you didn't request this, you can safely ignore this email."
    )
    return send_email(user.email, 'Reset your BaliVilla password', html, text)
