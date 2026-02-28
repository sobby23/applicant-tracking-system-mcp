from mcp.server.fastmcp import FastMCP
from tools.gmail import get_gmail_service
from googleapiclient.errors import HttpError
import base64
from email.message import EmailMessage
import os

from tools.applicants import load_applicants, get_applicant_by_name
from tools.resumes import list_resume_names as list_resume_files, read_resume as read_resume_file
from tools.evaluate import evaluate_candidate as run_evaluation, load_job_description, list_job_ids
from tools.sheets import append_candidate_row, update_candidate_row, get_existing_emails, get_sheet_data

# Create an MCP server
mcp = FastMCP("AVA")


# Define prompts
@mcp.prompt()
def ava(user_name: str, user_title: str) -> str:
    """Global instructions for Artificial Virtual Assistant (AVA)"""
    with open("prompts/ava.md", "r") as file:
        template = file.read()
    return template.format(user_name=user_name, user_title=user_title)


# Recruiting pipeline resources
@mcp.resource("job://default")
def get_job_default() -> str:
    """Default job description (senior-software-engineer). Use job://<job_id> for a specific role."""
    return load_job_description()


@mcp.resource("job://list")
def get_job_list() -> str:
    """List of job IDs (roles) available for evaluation. Each has a file jobs/<job_id>.md."""
    ids = list_job_ids()
    if not ids:
        return "No job descriptions in jobs/ (add .md files, e.g. senior-software-engineer.md, product-manager.md)."
    return "Job IDs: " + ", ".join(ids)


@mcp.resource("applicants://all")
def get_applicants_resource() -> str:
    """List of applicants from CSV: Name, Email, LinkedIn, Resume name, Job (role/job_id)."""
    applicants = load_applicants()
    if not applicants:
        return "No applicants in applicants.csv"
    lines = ["Name | Email | LinkedIn | Resume name | Job"]
    for a in applicants:
        lines.append(f"{a['name']} | {a['email']} | {a['linkedin']} | {a['resume_name']} | {a.get('job_id', 'senior-software-engineer')}")
    return "\n".join(lines)


# Recruiting pipeline tools
@mcp.tool()
def get_applicants() -> list[dict]:
    """Load applicants from CSV. Returns list of dicts with name, email, linkedin, resume_name."""
    return load_applicants()


@mcp.tool()
def list_resumes() -> list[str]:
    """List resume filenames in the configured resume directory (.txt, .md)."""
    return list_resume_files()


@mcp.tool()
def read_resume(resume_name: str) -> str:
    """Read resume content by filename from the resume directory. Raises if not found."""
    return read_resume_file(resume_name)


@mcp.tool()
def get_jobs() -> list[str]:
    """List job IDs (roles) available. Each corresponds to jobs/<job_id>.md."""
    return list_job_ids()


@mcp.tool()
def get_job_description(job_id: str) -> str:
    """Get the job description for a role. job_id is the filename without .md (e.g. senior-software-engineer, product-manager)."""
    return load_job_description(job_id=job_id)


@mcp.tool()
def evaluate_candidate(applicant_name: str) -> dict:
    """Evaluate one candidate against the job for which they applied. Loads applicant from CSV (including Job column) and resume from directory.
    Uses the applicant's Job (job_id) to select the right job description. Returns dict with: ai_score, key_strengths, gaps, recommended_action, draft_message."""
    applicant = get_applicant_by_name(applicant_name)
    if not applicant:
        return {"error": f"Applicant not found: {applicant_name}"}
    try:
        resume_text = read_resume_file(applicant["resume_name"])
    except FileNotFoundError:
        return {"error": f"Resume not found: {applicant['resume_name']}"}
    job_id = applicant.get("job_id") or "senior-software-engineer"
    return run_evaluation(
        applicant_name=applicant["name"],
        applicant_email=applicant["email"],
        resume_text=resume_text,
        job_id=job_id,
    )


@mcp.tool()
def process_new_applications() -> dict:
    """Process all applicants from CSV who are not yet in the sheet (or update existing).
    Each applicant is evaluated against the job for which they applied (Job column in CSV = job_id, e.g. senior-software-engineer or product-manager).
    For each applicant: if email already in sheet, re-evaluate and update row; otherwise evaluate and append.
    Skips applicants whose resume file is missing. Run this after uploading new resumes and adding rows to applicants.csv."""
    applicants = load_applicants()
    if not applicants:
        return {"processed": 0, "appended": 0, "updated": 0, "skipped": [], "error": "No applicants in applicants.csv"}

    try:
        sheet_data = get_sheet_data()
    except Exception as e:
        return {"processed": 0, "appended": 0, "updated": 0, "skipped": [], "error": str(e)}

    email_to_row = {d["email"].strip().lower(): d["row_index"] for d in sheet_data if d.get("email", "").strip()}
    appended = 0
    updated = 0
    skipped = []

    for app in applicants:
        email = (app.get("email") or "").strip().lower()
        if not email:
            skipped.append(f"{app.get('name', '?')}: no email")
            continue
        job_id = app.get("job_id") or "senior-software-engineer"
        try:
            resume_text = read_resume_file(app["resume_name"])
        except FileNotFoundError:
            skipped.append(f"{app['name']}: resume not found ({app['resume_name']})")
            continue

        result = run_evaluation(
            applicant_name=app["name"],
            applicant_email=app["email"],
            resume_text=resume_text,
            job_id=job_id,
        )
        if "error" in result:
            skipped.append(f"{app['name']}: {result.get('error', 'evaluation failed')}")
            continue

        row = [
            app["name"],
            app["email"],
            job_id,
            result.get("ai_score", ""),
            result.get("key_strengths", ""),
            result.get("gaps", ""),
            result.get("recommended_action", ""),
            "Evaluated",
        ]
        if email in email_to_row:
            update_candidate_row(
                email_to_row[email],
                row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7],
            )
            updated += 1
        else:
            append_candidate_row(
                name=row[0],
                email=row[1],
                job_applied=row[2],
                ai_score=row[3],
                key_strengths=row[4],
                gaps=row[5],
                recommended_action=row[6],
                status=row[7],
            )
            appended += 1

    return {
        "processed": appended + updated,
        "appended": appended,
        "updated": updated,
        "skipped": skipped,
    }


@mcp.tool()
def append_candidate_to_sheet(
    name: str,
    email: str,
    job_applied: str,
    ai_score: str,
    key_strengths: str,
    gaps: str,
    recommended_action: str,
    status: str = "Evaluated",
) -> dict:
    """Append one candidate row to the recruiter's Google Sheet. Use after manual evaluation or when adding a single candidate."""
    return append_candidate_row(
        name=name,
        email=email,
        job_applied=job_applied,
        ai_score=ai_score,
        key_strengths=key_strengths,
        gaps=gaps,
        recommended_action=recommended_action,
        status=status,
    )


# Define tools
@mcp.tool()
def write_email_draft(recipient_email: str, subject: str, body: str) -> dict:
    """Create a draft email using the Gmail API.

    Args:
        recipient_email (str): The email address of the recipient.
        subject (str): The subject line of the email.
        body (str): The main content/body of the email.

    Returns:
        dict or None: A dictionary containing the draft information including 'id' and 'message'
                     if successful, None if an error occurs.

    Raises:
        HttpError: If there is an error communicating with the Gmail API.

    Note:
        This function requires:
        - Gmail API credentials to be properly configured
        - USER_EMAIL environment variable to be set with the sender's email address
        - Appropriate Gmail API permissions for creating drafts
    """
    try:
        # create gmail api client
        service = get_gmail_service()

        message = EmailMessage()

        message.set_content(body)

        message["To"] = recipient_email
        message["From"] = os.getenv("USER_EMAIL")
        message["Subject"] = subject

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"message": {"raw": encoded_message}}
        # pylint: disable=E1101
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body=create_message)
            .execute()
        )

        print(f'Draft id: {draft["id"]}\nDraft message: {draft["message"]}')

    except HttpError as error:
        print(f"An error occurred: {error}")
        draft = None

    return draft


if __name__ == "__main__":
    mcp.run(transport='stdio')