"""Load applicant list from CSV (MVP; in production this could come from parsed emails)."""
import csv
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APPLICANTS_CSV = os.getenv("APPLICANTS_CSV", "applicants.csv")


def get_applicants_path() -> Path:
    path = Path(APPLICANTS_CSV)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def load_applicants() -> list[dict]:
    """
    Load applicants from CSV. Expected columns: Name, Email, LinkedIn, Resume name; optional: Job.
    Job = job_id (filename stem in jobs/, e.g. senior-software-engineer or product-manager). Defaults to senior-software-engineer.
    Returns list of dicts with keys: name, email, linkedin, resume_name, job_id.
    """
    path = get_applicants_path()
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            job = (row.get("Job") or row.get("Job Applied") or "senior-software-engineer").strip()
            if not job:
                job = "senior-software-engineer"
            rows.append({
                "name": (row.get("Name") or "").strip(),
                "email": (row.get("Email") or "").strip(),
                "linkedin": (row.get("LinkedIn") or "").strip(),
                "resume_name": (row.get("Resume name") or "").strip(),
                "job_id": job,
            })
        return rows


def get_applicant_by_name(name: str) -> dict | None:
    """Return first applicant whose Name matches (case-insensitive)."""
    for a in load_applicants():
        if a["name"].lower() == name.strip().lower():
            return a
    return None
