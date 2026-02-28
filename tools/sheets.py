"""Google Sheets API helpers for candidate tracking sheet."""
import os
from googleapiclient.discovery import build
from dotenv import load_dotenv
from tools.gmail import get_credentials

load_dotenv()

# Sheet name/tab (default first sheet); can override via env
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Candidates")


def get_sheets_service():
    """Return Google Sheets API v4 service."""
    return build("sheets", "v4", credentials=get_credentials())


def _get_sheet_id():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID is not set in .env")
    return sheet_id


def get_sheet_data() -> list[dict]:
    """
    Read the candidate sheet. Returns list of dicts with keys: row_index, name, email, job_applied, ai_score, key_strengths, gaps, recommended_action, status.
    row_index is 1-based (header = 1, first data row = 2). Empty sheet or only header returns [].
    """
    service = get_sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=_get_sheet_id(),
            range=f"'{SHEET_NAME}'!A2:H",
        )
        .execute()
    )
    rows = result.get("values", [])
    if not rows:
        return []
    out = []
    for i, row in enumerate(rows):
        padded = (row + [""] * 8)[:8]
        out.append({
            "row_index": i + 2,
            "name": padded[0],
            "email": padded[1],
            "job_applied": padded[2],
            "ai_score": padded[3],
            "key_strengths": padded[4],
            "gaps": padded[5],
            "recommended_action": padded[6],
            "status": padded[7],
        })
    return out


def get_existing_emails() -> set[str]:
    """Set of email addresses already in the sheet (column B)."""
    data = get_sheet_data()
    return {d["email"].strip().lower() for d in data if d.get("email", "").strip()}


def update_candidate_row(
    row_index: int,
    name: str,
    email: str,
    job_applied: str,
    ai_score: str,
    key_strengths: str,
    gaps: str,
    recommended_action: str,
    status: str = "Evaluated",
) -> dict:
    """Update one row in the sheet by 1-based row index."""
    service = get_sheets_service()
    body = {
        "values": [
            [
                name,
                email,
                job_applied,
                ai_score,
                key_strengths,
                gaps,
                recommended_action,
                status,
            ]
        ]
    }
    result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=_get_sheet_id(),
            range=f"'{SHEET_NAME}'!A{row_index}:H{row_index}",
            valueInputOption="USER_ENTERED",
            body=body,
        )
        .execute()
    )
    return result


def append_candidate_row(
    name: str,
    email: str,
    job_applied: str,
    ai_score: str,
    key_strengths: str,
    gaps: str,
    recommended_action: str,
    status: str = "Evaluated",
) -> dict:
    """
    Append one row to the recruiter's Google Sheet.
    Sheet must exist and have headers: Name, Email, Job Applied, AI Score, Key Strengths, Gaps, Recommended Action, Status.
    """
    service = get_sheets_service()
    body = {
        "values": [
            [
                name,
                email,
                job_applied,
                ai_score,
                key_strengths,
                gaps,
                recommended_action,
                status,
            ]
        ]
    }
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=_get_sheet_id(),
            range=f"'{SHEET_NAME}'!A:H",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )
    return result
