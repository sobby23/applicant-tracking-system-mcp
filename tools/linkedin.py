"""Read sample LinkedIn profile content from the linkedin/ folder (one .md per candidate)."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LINKEDIN_DIR = Path(os.getenv("LINKEDIN_DIR", str(PROJECT_ROOT / "linkedin")))


def get_linkedin_path(resume_name: str) -> Path:
    """Resolve LinkedIn .md path from resume filename (e.g. jane-doe-sse.txt -> linkedin/jane-doe-sse.md)."""
    base = Path(resume_name).stem
    return Path(LINKEDIN_DIR) / f"{base}.md"


def read_linkedin(resume_name: str) -> str:
    """
    Read LinkedIn profile content for a candidate. resume_name must match the resume filename (e.g. jane-doe-sse.txt).
    Returns profile text, or empty string if no file exists.
    """
    path = get_linkedin_path(resume_name)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def list_linkedin_profiles() -> list[str]:
    """List basenames of .md files in the linkedin folder (e.g. jane-doe-sse)."""
    p = Path(LINKEDIN_DIR)
    if not p.exists():
        return []
    return sorted(f.stem for f in p.glob("*.md"))
