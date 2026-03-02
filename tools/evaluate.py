"""Evaluate a candidate against the job description using Claude (structured output)."""
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# Paths (project root = parent of tools/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = PROJECT_ROOT / "jobs"
DEFAULT_JOB_FILE = JOBS_DIR / "senior-software-engineer.md"
EMAIL_TEMPLATE_FILE = PROJECT_ROOT / "email-templates" / "candidate-draft.txt"


def list_job_ids() -> list[str]:
    """Return list of job IDs (filename stems of .md files in jobs/)."""
    if not JOBS_DIR.exists():
        return []
    return sorted(p.stem for p in JOBS_DIR.glob("*.md"))


def get_job_role_display_name(job_id: str | None) -> str:
    """Get human-readable job role from the first line of the job file (e.g. 'Senior Software Engineer')."""
    if not job_id:
        job_id = DEFAULT_JOB_FILE.stem
    path = JOBS_DIR / f"{job_id}.md"
    if not path.exists():
        return job_id.replace("-", " ").title()
    first_line = path.read_text(encoding="utf-8", errors="replace").strip().split("\n")[0]
    return first_line.lstrip("#").strip() or job_id.replace("-", " ").title()


def load_job_description(job_id: str | None = None, job_path: Path | None = None) -> str:
    """Load job description by job_id (e.g. 'senior-software-engineer') or by path. job_id uses jobs/<job_id>.md."""
    if job_path is not None:
        path = job_path
    elif job_id:
        path = JOBS_DIR / f"{job_id}.md"
    else:
        path = DEFAULT_JOB_FILE
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


EVALUATION_SYSTEM = """You are a fair, consistent recruiter assistant. You evaluate candidates against the job description.
When LinkedIn profile text is provided, also compare it to the resume: note what is on LinkedIn but missing or different on the resume (e.g. roles, dates, titles), and any discrepancies. Put that in linkedin_notes.
Output valid JSON with exactly these keys:
- ai_score: string, one of "1", "2", "3", "4", "5" (1=poor fit, 5=strong fit)
- key_strengths: string, 2-5 bullet points on how the candidate matches the job (tie each to a requirement)
- gaps: string, bullet points where they fall short of requirements (or "None significant" if minor)
- recommended_action: string, one of "Advance to phone screen", "Reject", "Review with hiring manager"
- draft_body: string, the middle paragraph only for the candidate email (2-4 sentences, no greeting or sign-off). If advancing: state next step. If reject: polite decline. Professional and concise.
- linkedin_notes: string, REQUIRED when LinkedIn profile text is included above: write 2-5 bullet points comparing resume vs LinkedIn (dates, roles, discrepancies, or "No significant discrepancies"). When no LinkedIn text is provided, use exactly "Not compared".
Be concise. Base evaluation on the resume and job; use LinkedIn only for comparison notes. Reply with only the JSON object, no markdown fences or extra text."""


def _load_email_template() -> str:
    """Load the candidate draft email template. Falls back to a minimal template if file missing."""
    if EMAIL_TEMPLATE_FILE.exists():
        return EMAIL_TEMPLATE_FILE.read_text(encoding="utf-8", errors="replace").strip()
    return "Hi {candidate_name},\n\nThank you for applying to the {job_role} position.\n\n{body}\n\nWe appreciate your interest and the time you took to apply. If you have any questions, please feel free to reply to this email.\n\nBest regards,\n{recruiter_name}"


def _compose_draft_message(candidate_name: str, body: str, job_id: str | None = None) -> str:
    """Wrap the evaluator's draft body in the email template (greeting, job role, body, closing, sign-off)."""
    recruiter = (os.getenv("RECRUITER_NAME") or "The Hiring Team").strip()
    first_name = candidate_name.strip().split()[0] if candidate_name.strip() else "there"
    job_role = get_job_role_display_name(job_id)
    template = _load_email_template()
    return template.format(
        candidate_name=first_name,
        job_role=job_role,
        body=body,
        recruiter_name=recruiter,
    )


def _parse_json_from_response(text: str) -> dict:
    """Extract JSON from model response (strip markdown code blocks if present)."""
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return json.loads(m.group(0))
    return json.loads(text)


def evaluate_candidate(
    applicant_name: str,
    applicant_email: str,
    resume_text: str,
    job_description: str | None = None,
    job_id: str | None = None,
    linkedin_text: str | None = None,
) -> dict:
    """
    Run Claude evaluation and return structured result.
    If linkedin_text is provided, the model will compare resume vs LinkedIn and set linkedin_notes.
    Returns dict with: ai_score, key_strengths, gaps, recommended_action, draft_message, linkedin_notes.
    """
    if not job_description:
        job_description = load_job_description(job_id=job_id)

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY or CLAUDE_API_KEY must be set in .env")

    client = Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    linkedin_block = ""
    if linkedin_text and linkedin_text.strip():
        linkedin_block = f"""
LinkedIn profile (compare to resume for gaps/discrepancies):
{linkedin_text.strip()}

---
"""

    user_content = f"""Job description:
{job_description}

---
Candidate: {applicant_name} ({applicant_email})

Resume:
{resume_text}
{linkedin_block}
Evaluate this candidate and output the JSON only (no markdown, no extra text)."""

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=EVALUATION_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    text = response.content[0].text
    out = _parse_json_from_response(text)

    for key in ("ai_score", "key_strengths", "gaps", "recommended_action", "draft_body", "linkedin_notes"):
        if key not in out:
            out[key] = ""
    # Normalize linkedin_notes: accept multiple key names and list/string values (column "LinkedIn Notes" in sheet)
    _ln = (
        out.get("linkedin_notes")
        or out.get("Linkedin_notes")
        or out.get("LinkedIn_notes")
        or out.get("linkedIn_notes")
        or out.get("LinkedIn Notes")
    )
    if isinstance(_ln, list):
        _ln = "\n".join(str(x).strip() for x in _ln if x)
    out["linkedin_notes"] = str(_ln or "").strip()
    # When LinkedIn was provided but model returned no notes, set fallback so the sheet gets a value
    if linkedin_text and linkedin_text.strip() and not out["linkedin_notes"]:
        out["linkedin_notes"] = "LinkedIn profile compared; see evaluation above."
    # Compose full draft email from template (greeting + job role + body + closing + sign-off)
    body = (out.get("draft_body") or "").strip()
    out["draft_message"] = _compose_draft_message(applicant_name, body, job_id=job_id) if body else ""
    return out
