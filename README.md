# Model Context Protocol (MCP)

## Watch the presentation

A full presentation of AVA (the recruiting assistant built on this MCP server)—including the problem it solves, architecture, and a live demo—is available to watch and evaluate:

**[Watch AVA presentation video (Google Drive)](https://drive.google.com/file/d/1BuV0v0yYRR5p9GUXOtI09N7ja-fLfPCx/view?usp=sharing)**

The video covers: existing ATS pain points, how AVA addresses them, the one critical decision that stays human (“the system recommends; the human decides”), and a demo of processing applications and drafting emails.

---

## How to run this example

1. Clone this repo
2. [Install uv](https://docs.astral.sh/uv/getting-started/installation/) if you haven't already
```
# Mac/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
3. Test the server in dev mode
```
uv run mcp dev mcp-server-example.py
```
4. Add server config to your AI app.

   **Cursor:** The config is already in this repo at **`.cursor/mcp.json`**. Cursor reads that file when you open this project. If your `uv` or project path is different, edit `.cursor/mcp.json` and update `command` (path to `uv`) and `args[1]` (path to this repo). Then **restart Cursor** (or reload the window) so it picks up the MCP server. MCP tools run in **Agent/Composer** mode.

   **Alternative in Cursor (UI):** Open **Settings** (`Cmd + ,` / `Ctrl + ,`) → **Tools & MCP** → **Add new MCP server**. Set name to `AVA`, type to **command**, command to the full path to `uv` (e.g. `/Users/sobby/.local/bin/uv`), and args to: `--directory`, `/Users/sobby/Workspace/mcp-demo`, `run`, `mcp-server-example.py` (exact order). Save and restart Cursor.

   **Claude Desktop:** Put the same JSON under the MCP config file used by Claude Desktop (see [Claude Desktop MCP docs](https://docs.anthropic.com/en/docs/build-with-claude/mcp)).
```
{
  "mcpServers": {
    "AVA": {
      "command": "/path/to/uv",
      "args": ["--directory", "/path/to/mcp-demo", "run", "mcp-server-example.py"]
    }
  }
}
```


## Recruiting pipeline (MVP)

**Trigger: upload new resumes to a directory.** No Gmail read. You provide:
- **applicants.csv** — columns: Name, Email, LinkedIn, Resume name, **Job** (optional). **Job** = job ID (filename stem in `jobs/`, e.g. `senior-software-engineer` or `product-manager`). Defaults to `senior-software-engineer` if missing. Add a row when you add a new resume.
- **resumes/** — one file per resume; filenames must match "Resume name" in the CSV (e.g. `jane-doe-sse.txt`).
- **jobs/** — one `.md` file per role (e.g. `senior-software-engineer.md`, `product-manager.md`). The **job ID** is the filename without `.md`. Each applicant is evaluated against the job indicated in their CSV row.
- **linkedin/** — (optional, for demo) One `.md` file per candidate; filename = resume stem without extension (e.g. `jane-doe-sse.md`). Used to compare resume vs LinkedIn when you ask: the `read_linkedin(resume_name)` tool loads a profile; comparison appears in the evaluation response.
- A **Google Sheet** with a tab named "Candidates" (or set `GOOGLE_SHEET_NAME`) and headers: **Name, Email, Job Applied, AI Score, Key Strengths, Gaps, Recommended Action, Status**.

**Flow:**
1. Upload new resume(s) to `resumes/` and add the corresponding row(s) to `applicants.csv`. Optionally add a matching file in `linkedin/` (e.g. `jane-doe-sse.md`) so evaluation can compare resume vs LinkedIn when you ask.
2. Ask AVA to **"Process new applications"** (or "Sync applicants to the sheet"). AVA runs `process_new_applications()`: evaluates each applicant and adds or updates rows. For LinkedIn comparison, ask explicitly (e.g. "Process new applications and compare with LinkedIn").
3. Open the sheet, filter/sort by score, strengths, gaps, status.
4. Ask AVA to **draft email** only for the candidates you choose (e.g. "Draft email to Jane Doe", "Create drafts for these 5"). AVA creates Gmail drafts; you send after review.

**Email draft template:** Drafts use the template in `email-templates/candidate-draft.txt` (greeting, body from the evaluator, sign-off). Edit that file to change wording; set `RECRUITER_NAME` in `.env` for the sign-off name.

### LinkedIn comparison (demo, opt-in)
The `read_linkedin(resume_name)` tool reads a markdown file from `linkedin/` whose filename matches the resume stem (e.g. `jane-doe-sse.md` for `jane-doe-sse.txt`). **LinkedIn is only used when you explicitly ask** for it: use **evaluate_candidate_with_linkedin** or **process_new_applications_with_linkedin** (e.g. "evaluate Jane Doe and compare with her LinkedIn"). The comparison appears in the evaluation response (`linkedin_notes`); it is not written to the Google Sheet. No real LinkedIn API is used; the demo uses sample `.md` profiles in `linkedin/`.

## Customizing AVA's Behavior

### Update Personal Details and Preferences
1. Locate the `prompts/ava.md` file in your project directory
2. Customize the file with:
   - Communication preferences
   - Specific instructions for handling tasks
   - Any other relevant guidelines for AVA

## Environment Setup (.env)

1. Create a `.env` file in the root directory of the project with the following variables:

```env
USER_EMAIL=your_email_address

# Google OAuth Credentials
GOOGLE_CREDENTIALS_PATH=.config/ava-agent/credentials.json
GOOGLE_TOKEN_PATH=.config/ava-agent/token.json

# Recruiting pipeline (MVP) — Claude for evaluation
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-haiku-20241022
GOOGLE_SHEET_ID=your_google_sheet_id
RECRUITER_NAME=Your Name
RESUME_DIR=resumes
APPLICANTS_CSV=applicants.csv
```

### Required Environment Variables:
- `USER_EMAIL`: The Gmail address you want to use for this application
- `GOOGLE_CREDENTIALS_PATH`: Path to your Google OAuth credentials file
- `GOOGLE_TOKEN_PATH`: Path where the Google OAuth token will be stored
- `ANTHROPIC_API_KEY` (or `CLAUDE_API_KEY`): For candidate evaluation via Claude (recruiting pipeline)
- `GOOGLE_SHEET_ID`: Spreadsheet ID for the candidate tracking sheet (recruiting; create the sheet first and use the ID from the URL)
- `RECRUITER_NAME`: Name used in draft email sign-off (e.g. "Jane Smith"). Optional; defaults to "The Hiring Team"

## Google OAuth Setup

### 1. Create Project Directory Structure

First, create the required directory structure:
```bash
mkdir -p .config/ava-agent
```

### 2. Set Up Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable APIs:
   - In the navigation menu, go to "APIs & Services" > "Library"
   - Enable **Gmail API** (search "Gmail API" > Enable)
   - Enable **Google Sheets API** (search "Google Sheets API" > Enable)

### 3. Create OAuth Credentials

1. In the Google Cloud Console:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop application" as the application type
   - Give it a name (e.g., "AVA Gmail Client")
   - Click "Create"

2. Download the credentials:
   - After creation, click "Download JSON"
   - Save the downloaded file as `credentials.json` in `.config/ava-agent/`
   - The file should contain your client ID and client secret

### 4. Configure OAuth Consent Screen

1. In the Google Cloud Console:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type
   - Fill in the required information:
     - App name
     - User support email
     - Developer contact information
   - Add scopes: `https://www.googleapis.com/auth/gmail.compose` and `https://www.googleapis.com/auth/spreadsheets`
   - Add your email as a test user
   - Complete the configuration

**Note:** If you add the Sheets scope after already having a token, delete `token.json` and run `uv run oauth.py` again.

## Signing into Google

Before the server can access you Gmail account you will need to authorize it. You can do this by running `uv run oauth.py` which does the following.
1. Check for the presence of `token.json`
2. If not found, it will initiate the Google OAuth authentication flow
3. Guide you through the authentication process in your browser:
   - You'll be asked to sign in to your Google account
   - Grant the requested permissions
   - The application will automatically save the token
4. Generate and store the token automatically

## Security Notes

### File Protection
- Never commit your `.env` file or `token.json` to version control
- Keep your Google credentials secure
- Add the following to your `.gitignore`:
  ```
  .env
  .config/ava-agent/token.json
  .config/ava-agent/credentials.json
  ``` 