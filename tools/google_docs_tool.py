"""
tools/google_docs_tool.py
Safe + robust Google Docs read/write tool
"""

from __future__ import annotations
import os
import re
from typing import Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain.tools import BaseTool
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings


SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


# ── Input Schemas ─────────────────────────────────────────────

class GoogleDocsReadInput(BaseModel):
    doc_url_or_id: str


class GoogleDocsWriteInput(BaseModel):
    title: str
    content: str


# ── Auth Helper ───────────────────────────────────────────────

def _get_credentials() -> Credentials:
    cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS

    # ✅ 1. Service Account (BEST)
    if cred_path and os.path.exists(cred_path):
        try:
            logger.info("Using service account")
            return service_account.Credentials.from_service_account_file(
                cred_path, scopes=SCOPES
            )
        except Exception as e:
            logger.warning(f"Service account failed: {e}")

    # ✅ 2. OAuth fallback (SAFE)
    token_path = "config/google_token.json"
    client_secret_path = "config/google_oauth_client.json"

    creds: Optional[Credentials] = None

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            creds = None

    # ✅ refresh expired token
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            return creds
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")

    # ✅ 3. Interactive login (only if config exists)
    if os.path.exists(client_secret_path):
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_path, SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

        return creds

    # ❌ FINAL fallback
    raise RuntimeError(
        "No valid Google credentials found. "
        "Provide service account or OAuth client config."
    )


# ── Utility ───────────────────────────────────────────────────

def _extract_doc_id(url_or_id: str) -> str:
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url_or_id)
    return match.group(1) if match else url_or_id.strip()


# ── Reader Tool ───────────────────────────────────────────────

class GoogleDocsReaderTool(BaseTool):
    name: str = "google_docs_reader"
    description: str = "Read text content from a Google Doc"
    args_schema: type[BaseModel] = GoogleDocsReadInput

    def _run(self, doc_url_or_id: str) -> str:
        try:
            doc_id = _extract_doc_id(doc_url_or_id)
            creds = _get_credentials()

            service = build("docs", "v1", credentials=creds)

            doc = service.documents().get(documentId=doc_id).execute()

            text = self._parse_doc(doc)

            if not text:
                return "Warning: Document is empty or unreadable."

            return text

        except HttpError as e:
            return f"Google Docs API error: {e}"
        except Exception as e:
            return f"Error reading Google Doc: {e}"

    @staticmethod
    def _parse_doc(doc: dict) -> str:
        parts = []

        for element in doc.get("body", {}).get("content", []):
            para = element.get("paragraph")
            if not para:
                continue

            for elem in para.get("elements", []):
                text_run = elem.get("textRun")
                if text_run:
                    parts.append(text_run.get("content", ""))

        return "".join(parts).strip()

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError


# ── Writer Tool ───────────────────────────────────────────────

class GoogleDocsWriterTool(BaseTool):
    name: str = "google_docs_writer"
    description: str = "Create a Google Doc with content"
    args_schema: type[BaseModel] = GoogleDocsWriteInput

    def _run(self, title: str, content: str) -> str:
        try:
            creds = _get_credentials()
            service = build("docs", "v1", credentials=creds)

            doc = service.documents().create(body={"title": title}).execute()
            doc_id = doc["documentId"]

            service.documents().batchUpdate(
                documentId=doc_id,
                body={
                    "requests": [
                        {
                            "insertText": {
                                "location": {"index": 1},
                                "text": content,
                            }
                        }
                    ]
                },
            ).execute()

            url = f"https://docs.google.com/document/d/{doc_id}/edit"
            logger.success(f"Created doc: {url}")

            return url

        except HttpError as e:
            return f"Google Docs API error: {e}"
        except Exception as e:
            return f"Error creating Google Doc: {e}"

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError