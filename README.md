# Resume Ops API

Podman-first FastAPI service for tailoring a JSON Resume to a job description while protecting immutable resume fields.

## What It Does

The service accepts:

- an optional master resume in JSON Resume format (if omitted, falls back to the configured `MASTER_RESUME_PATH`)
- a target job description
- an optional rendering theme
- an optional callback URL for async execution

It then:

- runs a structured multi-step LLM pipeline
- keeps protected fields unchanged
- tailors only allowed sections
- validates the final output against the JSON Resume schema
- renders a PDF using `resumed`

## Tailoring Rules

The service is intentionally conservative.

- `basics` is preserved exactly as provided
- `work` keeps every job and only tailors `summary` and `highlights`
- `education` only tailors `courses`
- `skills` can be regrouped, prioritized, and rewritten, but must remain plausible from the master resume
- `projects` can be selected, omitted, reordered, and rewritten, but new projects must not be invented
- `certificates` are selection-only; certificate content is not rewritten, and the final output is capped at 18 certificates
- `interests` can be tailored if present
- `languages`, `volunteer`, `awards`, `publications`, `references`, `meta`, and other unhandled fields pass through unchanged

## API Modes

### Synchronous

If `callback_url` is omitted, `POST /api/v1/tailor` returns:

- tailored JSON resume
- base64-encoded PDF
- resolved theme

### Asynchronous

If `callback_url` is provided, `POST /api/v1/tailor` returns `202 Accepted` with a `task_id`.

The service then:

- stores the job in SQLite
- processes it in the background
- posts the final result or failure to the callback URL
- exposes status via `GET /api/v1/tasks/{task_id}`

## Endpoints

- `POST /api/v1/tailor`
- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/themes`
- `GET /healthz`
- `GET /readyz`

## Configuration

Copy `.env.example` to `.env` and set the values you need.

Important variables:

- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`: provider credentials
- `OPENAI_BASE_URL`: optional custom endpoint such as OpenRouter
- `STRATEGY_MODEL`, `WORK_MODEL`, `EDUCATION_MODEL`, `SKILLS_MODEL`, `PROJECTS_MODEL`, `OPTIONAL_SECTIONS_MODEL`: model routing
- `DEFAULT_THEME`: default PDF theme
- `ALLOWED_THEMES`: comma-separated allowlist of supported themes
- `MAX_CONCURRENT_JOBS`: background worker concurrency
- `CALLBACK_TIMEOUT_SECONDS`: outbound callback timeout
- `MASTER_RESUME_PATH`: optional path to a default JSON Resume on disk. If provided, the API caller can omit the `resume` field from the request payload.
- `DATA_DIR`: persistent app data path, including SQLite DB and rendered PDFs
- `DATABASE_URL`: optional explicit DB URL; if unset, SQLite is created under `DATA_DIR`

Example:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=
STRATEGY_MODEL=openai/gpt-4o-mini
WORK_MODEL=openai/gpt-4o-mini
EDUCATION_MODEL=openai/gpt-4o-mini
SKILLS_MODEL=openai/gpt-4o-mini
PROJECTS_MODEL=openai/gpt-4o-mini
OPTIONAL_SECTIONS_MODEL=openai/gpt-4o-mini
DEFAULT_THEME=jsonresume-theme-stackoverflow
ALLOWED_THEMES=jsonresume-theme-stackoverflow,jsonresume-theme-even
MAX_CONCURRENT_JOBS=2
CALLBACK_TIMEOUT_SECONDS=5
MASTER_RESUME_PATH=/data/master-resume.json
DATA_DIR=/data
```

## Deployment & Local Development

This project supports two execution modes: deploying via pre-built images from GitHub Container Registry (GHCR) (recommended for running the pipeline without local build overhead) and building locally for development.

### Host Directory Permissions (Crucial for Podman / Rootless Docker)

> [!IMPORTANT]
> **Directory Write Permissions**: Because both `resume-ops` and `job-ops` run inside containers as secure non-root users (`appuser` and `node` respectively), they do not have root privileges to write to directories owned solely by your host user. 
> 
> If the local data directories do not have open write permissions, the services will fail during startup with a `PermissionError: [Errno 13] Permission denied` (e.g., when attempting to create SQLite databases or directory structures).
>
> To resolve this, grant write permissions to your local data folder on the host:
> ```bash
> mkdir -p data/
> chmod -R 777 data/
> ```

---

### Environment Setup Checklist

You need to configure two separate `.env` files—one for each container.

#### 1. Core API Config (`./.env`)
Create `./.env` in the root `resume-ops` folder:
```env
# API Keys (Set at least one depending on your model choice)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# Model Routing Configuration
STRATEGY_MODEL=openai/gpt-4o-mini
WORK_MODEL=openai/gpt-4o-mini
EDUCATION_MODEL=openai/gpt-4o-mini
SKILLS_MODEL=openai/gpt-4o-mini
PROJECTS_MODEL=openai/gpt-4o-mini
OPTIONAL_SECTIONS_MODEL=openai/gpt-4o-mini

# Paths (Keep as-is for container execution)
MASTER_RESUME_PATH=/data/master-resume.json
DATA_DIR=/data
```

#### 2. Submodule Config (`./job-ops/.env`)
Create `./job-ops/.env` in the `job-ops` directory. It **must** point to the `resume-ops` container as its backend:
```env
# Integration Backend (Crucial)
RESUME_GENERATION_BACKEND=resume_ops
RESUME_OPS_BASE_URL=http://resume-ops:8000

# Data Storage
DATA_DIR=/app/data

# Scraper Credentials (Gmail, Apify, etc.)
# ...
```

---

### Option 1: Running with Pre-built Images (Recommended)

To run the complete pipeline (`resume-ops` and `job-ops`) directly using pre-built containers from GHCR:

1. **Follow the Environment Checklist** above to configure both `.env` files.
2. **Provide your master resume**: Place your JSON Resume file at `./master-resume.json` in the `resume-ops` root folder. Both services will automatically mount this file.
3. **Configure permissions** as shown in the Host Directory Permissions warning block.
4. **Launch the services**:
   ```bash
   podman compose up -d
   ```
   This will pull `ghcr.io/rat-s/resume-ops:latest` and `ghcr.io/rat-s/job-ops:latest` and launch them immediately without local compile overhead.

Once running:
- **JobOps Web UI**: accessible at `http://localhost:3005`
- **resume-ops API**: accessible at `http://localhost:8000`

### Option 2: Running with Local Development Build

If you are developing or want to build/recompile the images locally:

1. **Clone the repo with submodules**:
   ```bash
   git clone --recurse-submodules https://github.com/Rat-S/resume-ops.git
   cd resume-ops
   ```
2. **Follow the configuration steps** (environment, permissions, and master resume setup) as shown in Option 1.
3. **Start the services**:
   ```bash
   podman compose up -d --build
   ```
   *Note: Because `compose.override.yaml` is present, `podman compose` will automatically merge the local build settings and compile the images locally instead of pulling from GHCR.*

---

## Building and Publishing to GHCR

Container images are automatically built and published to GHCR (`ghcr.io/rat-s/resume-ops` and `ghcr.io/rat-s/job-ops`) via GitHub Actions when a version tag (`v*`) is pushed to the repository:

```bash
# 1. Create a version tag
git tag v0.1.0

# 2. Push the tag to GitHub (triggers the CI build and publish)
git push origin v0.1.0
```

*Note: For the `job-ops` submodule, make sure you push the tag to your own fork repo (`Rat-S/job-ops`).*

## Example Requests

### List Available Themes

```bash
curl http://127.0.0.1:8000/api/v1/themes
```

Example response:

```json
{
  "default_theme": "jsonresume-theme-stackoverflow",
  "allowed_themes": ["jsonresume-theme-stackoverflow"]
}
```

### Synchronous Tailoring

If a `MASTER_RESUME_PATH` is configured in your `.env` (or via Docker), you can tailor your resume by simply providing the job description:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tailor \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "job_description": "Looking for a product leader with AI and platform experience.",
  "theme": "jsonresume-theme-stackoverflow"
}
JSON
```

If you don't have a `MASTER_RESUME_PATH` configured, or if you want to override it, you can provide the full JSON Resume in the payload:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tailor \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "resume": {
    "basics": {
      "name": "Jane Doe",
      "email": "jane@example.com",
      "summary": "Product leader with experience in AI systems."
    },
    "work": []
  },
  "job_description": "Looking for a product leader with AI and platform experience."
}
JSON
```

Successful response shape:

```json
{
  "resume": {
    "...": "tailored json resume"
  },
  "pdf_base64": "JVBERi0xLjQK...",
  "theme": "jsonresume-theme-stackoverflow"
}
```

### Asynchronous Tailoring With Callback

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tailor \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "resume": {
    "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
    "basics": {
      "name": "Jane Doe",
      "email": "jane@example.com"
    }
  },
  "job_description": "Need a technical product manager for an AI platform.",
  "callback_url": "https://example.com/webhooks/resume-ready"
}
JSON
```

Accepted response:

```json
{
  "task_id": "9f5b4b08f74b4cb2bc4ebae613cb2e77",
  "status": "queued"
}
```

### Poll Task Status

```bash
curl http://127.0.0.1:8000/api/v1/tasks/9f5b4b08f74b4cb2bc4ebae613cb2e77
```

Completed response shape:

```json
{
  "task_id": "9f5b4b08f74b4cb2bc4ebae613cb2e77",
  "status": "completed",
  "created_at": "2025-05-13T08:30:00Z",
  "updated_at": "2025-05-13T08:30:25Z",
  "resume": {
    "...": "tailored json resume"
  },
  "pdf_base64": "JVBERi0xLjQK...",
  "error": null,
  "theme": "jsonresume-theme-stackoverflow"
}
```

Failed response shape:

```json
{
  "task_id": "9f5b4b08f74b4cb2bc4ebae613cb2e77",
  "status": "failed",
  "created_at": "2025-05-13T08:30:00Z",
  "updated_at": "2025-05-13T08:30:10Z",
  "resume": null,
  "pdf_base64": null,
  "error": {
    "code": "llm_generation_failed",
    "message": "Structured LLM generation failed for model 'openai/gpt-4o-mini'."
  },
  "theme": "jsonresume-theme-stackoverflow"
}
```

## Callback Payloads

Successful callback payload:

```json
{
  "task_id": "9f5b4b08f74b4cb2bc4ebae613cb2e77",
  "status": "completed",
  "result": {
    "resume": {
      "...": "tailored json resume"
    },
    "pdf_base64": "JVBERi0xLjQK...",
    "theme": "jsonresume-theme-stackoverflow"
  }
}
```

Failure callback payload:

```json
{
  "task_id": "9f5b4b08f74b4cb2bc4ebae613cb2e77",
  "status": "failed",
  "error": {
    "code": "llm_generation_failed",
    "message": "Structured LLM generation failed for model 'openai/gpt-4o-mini'."
  }
}
```

## Data Storage

By default the service stores:

- SQLite database under `/data`
- rendered PDFs under `/data/jobs/<task_id>/output.pdf`

In the provided Podman compose setup, `/data` is backed by the local `./data` directory.

## Local Development

If you want to run without Podman:

```bash
uv run python -m resume_ops_api
```

That requires the Python dependencies from `pyproject.toml` to be available in your local environment.

## CLI Usage

You can also use `resume-ops` directly from your terminal to generate tailored resumes locally without starting the API server. You have two options for running the CLI:

### Option 1: Via Container (Recommended)

Since the Podman image already bundles all dependencies (including Node.js and the PDF renderer), you can run the CLI through the container. To make file paths work seamlessly, mount your current working directory to the same path inside the container:

```bash
podman run --rm \
  --env-file .env \
  -v "$(pwd)":"$(pwd)" \
  -w "$(pwd)" \
  resume-ops \
  resume-ops \
    --resume ./my-master-resume.json \
    --jd ./target-job.md \
    --output ./tailored-resume.pdf \
    --theme jsonresume-theme-stackoverflow
```

### Option 2: Running Natively (Local Environment)

If you prefer to run it natively without a container, you can install the CLI directly into your Python environment:

```bash
uv pip install -e .
```

**Important Requirement for Native Usage:** The project relies on `resumed` to render PDFs. You must have Node.js installed and manually install the renderer and any themes you wish to use:

```bash
npm install -g resumed jsonresume-theme-stackoverflow
```

Once installed natively, you can run the command directly:

```bash
resume-ops \
  --resume my-master-resume.json \
  --jd target-job.md \
  --output ./tailored-resume.pdf \
  --output-json ./tailored-resume.json \
  --theme jsonresume-theme-stackoverflow
```

**CLI Options:**

- `--resume`: (Required) Path to the master JSON resume.
- `--jd`: (Required) Path to the text or markdown job description.
- `--output`: (Required) Path to save the resulting PDF.
- `--output-json`: (Optional) Path to save the intermediate tailored JSON resume.
- `--theme`: (Optional) The theme to use for rendering (must be in `ALLOWED_THEMES`).

## Current Limitations

- No authentication is built in
- Background execution is single-process and intended for one API worker
- Theme support is allowlist-based, not dynamic package installation at request time
- The service relies on `resumed` being installed in the runtime environment

## License

This project is licensed under `AGPL-3.0-only`. See [LICENSE](./LICENSE).
