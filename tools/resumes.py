"""Read resumes from a local directory (MVP; can be swapped for Drive later)."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RESUME_DIR = os.getenv("RESUME_DIR", "resumes")


def get_resume_dir() -> Path:
    """Resolve resume directory (project-relative or absolute from env)."""
    path = Path(RESUME_DIR)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def list_resume_names() -> list[str]:
    """List filenames of resume files in the configured directory (.txt, .md)."""
    base = get_resume_dir()
    if not base.exists():
        return []
    names = []
    for f in base.iterdir():
        if f.is_file() and f.suffix.lower() in (".txt", ".md"):
            names.append(f.name)
    return sorted(names)


def read_resume(resume_name: str) -> str:
    """
    Read resume content by filename. Raises FileNotFoundError if not found.
    """
    base = get_resume_dir()
    path = base / resume_name
    if not path.is_file():
        raise FileNotFoundError(f"Resume not found: {resume_name} in {base}")
    return path.read_text(encoding="utf-8", errors="replace")
