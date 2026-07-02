import os
import base64
from email.message import EmailMessage
from typing import Any

import httpx

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _get_token() -> str:
    return os.environ.get("GMAIL_ACCESS_TOKEN", "")


def _get_refresh_config() -> tuple[str, str, str]:
    return (
        os.environ.get("GMAIL_REFRESH_TOKEN", ""),
        os.environ.get("GMAIL_CLIENT_ID", ""),
        os.environ.get("GMAIL_CLIENT_SECRET", ""),
    )


async def _refresh_token() -> bool:
    refresh_token, client_id, client_secret = _get_refresh_config()
    if not (refresh_token and client_id and client_secret):
        return False
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                OAUTH_TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                },
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            new_token = data.get("access_token", "")
            if new_token:
                os.environ["GMAIL_ACCESS_TOKEN"] = new_token
                return True
    except Exception:
        pass
    return False


def _check_token() -> bool:
    return bool(_get_token())


async def _request(method: str, path: str, **kwargs) -> dict:
    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as c:
        r = await c.request(
            method, f"{GMAIL_API}{path}",
            headers=headers, timeout=30, **kwargs
        )
        if r.status_code == 401:
            refreshed = await _refresh_token()
            if refreshed:
                headers["Authorization"] = f"Bearer {_get_token()}"
                r = await c.request(
                    method, f"{GMAIL_API}{path}",
                    headers=headers, timeout=30, **kwargs
                )
            else:
                raise RuntimeError(
                    "Gmail API returned 401 and token refresh failed. "
                    "Set GMAIL_REFRESH_TOKEN, GMAIL_CLIENT_ID, and GMAIL_CLIENT_SECRET "
                    "to enable automatic refresh, or update GMAIL_ACCESS_TOKEN manually."
                )
        r.raise_for_status()
        return r.json()


async def _get(path: str, params: dict | None = None) -> dict:
    return await _request("GET", path, params=params)


async def _post(path: str, data: dict) -> dict:
    return await _request("POST", path, json=data)


def _decode_body(part: dict) -> str:
    if part.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    if part.get("parts"):
        for p in part["parts"]:
            result = _decode_body(p)
            if result:
                return result
    return ""


def _format_email(msg: dict) -> str:
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    subject = headers.get("Subject", "(no subject)")
    sender = headers.get("From", "(unknown)")
    date = headers.get("Date", "(unknown)")
    snippet = msg.get("snippet", "")
    body = _decode_body(msg["payload"])[:2000]
    return (
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Date: {date}\n"
        f"Snippet: {snippet}\n"
        f"\n{body}"
    )


async def search(query: str, max_results: int = 10) -> str:
    if not _check_token():
        return "Error: GMAIL_ACCESS_TOKEN not configured"
    try:
        data = await _get("/messages", {"q": query, "maxResults": max_results})
        messages = data.get("messages", [])
        if not messages:
            return f"No messages found for query: {query}"
        lines = [f"# Emails matching: {query}", ""]
        for msg_ref in messages:
            msg = await _get(f"/messages/{msg_ref['id']}", {"format": "metadata"})
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            subject = headers.get("Subject", "(no subject)")[:60]
            sender = headers.get("From", "(unknown)")[:40]
            date = headers.get("Date", "")[:17]
            lines.append(f"- {msg_ref['id']}: {subject}")
            lines.append(f"  {sender} — {date}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching emails: {e}"


async def read(email_id: str) -> str:
    if not _check_token():
        return "Error: GMAIL_ACCESS_TOKEN not configured"
    try:
        msg = await _get(f"/messages/{email_id}", {"format": "full"})
        return _format_email(msg)
    except Exception as e:
        return f"Error reading email: {e}"


async def send(to: str, subject: str, body: str, cc: str = "") -> str:
    if not _check_token():
        return "Error: GMAIL_ACCESS_TOKEN not configured"
    try:
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        msg.set_content(body)
        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = await _post("/messages/send", {"raw": encoded})
        return f"Email sent to {to}: {result.get('id', '')}"
    except Exception as e:
        return f"Error sending email: {e}"


async def draft(to: str, subject: str, body: str) -> str:
    if not _check_token():
        return "Error: GMAIL_ACCESS_TOKEN not configured"
    try:
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = await _post("/drafts", {"message": {"raw": encoded}})
        return f"Draft saved: {result.get('id', '')}"
    except Exception as e:
        return f"Error creating draft: {e}"


async def list_labels() -> str:
    if not _check_token():
        return "Error: GMAIL_ACCESS_TOKEN not configured"
    try:
        data = await _get("/labels")
        labels = data.get("labels", [])
        lines = ["# Labels", ""]
        for label in labels:
            lines.append(f"- {label['name']} ({label.get('messagesTotal', 0)} messages)")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing labels: {e}"


async def list_threads(query: str = "", max_results: int = 10) -> str:
    if not _check_token():
        return "Error: GMAIL_ACCESS_TOKEN not configured"
    try:
        params: dict[str, Any] = {"maxResults": max_results}
        if query:
            params["q"] = query
        data = await _get("/threads", params)
        threads = data.get("threads", [])
        if not threads:
            return "No threads found"
        lines = [f"# Threads ({len(threads)})", ""]
        for t in threads:
            snippet = t.get("snippet", "")[:80]
            lines.append(f"- {t['id']}: {snippet}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing threads: {e}"
