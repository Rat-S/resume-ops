# Resume Ops API

Podman-first FastAPI service for tailoring a JSON Resume to a job description while protecting immutable resume fields.

## What It Does

The service accepts:

- a master resume in JSON Resume format
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
- `certificates` are selection-only; certificate content is not rewritten
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
DATA_DIR=/data
```

## Run With Podman

1. Copy `.env.example` to `.env`.
2. Fill in at least one provider credential and your chosen model names.
3. Start the service:

```bash
podman compose up --build
```

The API listens on `http://127.0.0.1:8000`.

Persistent data is mounted to `./data` by `compose.yaml`.

## Example Requests

### List Available Themes

```bash
curl http://127.0.0.1:8000/api/v1/themes
```

Example response:

```json
{
  "default_theme": "jsonresume-theme-stackoverflow",
  "allowed_themes": [
    "jsonresume-theme-stackoverflow"
  ]
}
```

### Synchronous Tailoring

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tailor \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "resume": {
    "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
    "basics": {
      "name": "Jane Doe",
      "email": "jane@example.com",
      "summary": "Product leader with experience in AI systems."
    },
    "work": [
      {
        "name": "Example Corp",
        "position": "Product Manager",
        "startDate": "2022-01",
        "endDate": "2024-06",
        "highlights": [
          "Led roadmap planning",
          "Worked with engineering"
        ]
      }
    ],
    "education": [],
    "skills": [],
    "projects": [],
    "certificates": []
  },
  "job_description": "Looking for a product leader with AI and platform experience.",
  "theme": "jsonresume-theme-stackoverflow"
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

## Current Limitations

- No authentication is built in
- Background execution is single-process and intended for one API worker
- Theme support is allowlist-based, not dynamic package installation at request time
- The service relies on `resumed` being installed in the runtime environment
