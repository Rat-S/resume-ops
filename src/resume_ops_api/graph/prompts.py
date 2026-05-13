from __future__ import annotations

import json
from typing import Any


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2)


def strategy_prompt(resume: dict[str, Any], job_description: str) -> tuple[str, str]:
    system = (
        "You are tailoring a resume without inventing facts. "
        "Return only structured JSON matching the requested schema. "
        "Use the full master resume for context, but describe only relevance rules and priorities."
    )
    user = f"Job description:\n{job_description}\n\nMaster resume:\n{_json(resume)}"
    return system, user


def work_prompt(resume: dict[str, Any], job_description: str, strategy: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Tailor only the summary and highlights for each work item. "
        "Do not change company names, positions, dates, locations, urls, or order. "
        "Do not invent unsupported responsibilities or achievements."
    )
    user = (
        f"Job description:\n{job_description}\n\n"
        f"Strategy:\n{_json(strategy)}\n\n"
        f"Master resume for context:\n{_json(resume)}\n\n"
        f"Target work section:\n{_json(resume.get('work', []))}"
    )
    return system, user


def education_prompt(resume: dict[str, Any], job_description: str, strategy: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Tailor only education courses. Preserve institution, degree, dates, scores, and other metadata exactly."
    )
    user = (
        f"Job description:\n{job_description}\n\n"
        f"Strategy:\n{_json(strategy)}\n\n"
        f"Master resume for context:\n{_json(resume)}\n\n"
        f"Target education section:\n{_json(resume.get('education', []))}"
    )
    return system, user


def skills_prompt(resume: dict[str, Any], job_description: str, strategy: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Tailor the skills section by regrouping and prioritizing existing evidence from the master resume. "
        "Keep JSON Resume skill objects. Do not invent unsupported skills."
    )
    user = (
        f"Job description:\n{job_description}\n\n"
        f"Strategy:\n{_json(strategy)}\n\n"
        f"Master resume:\n{_json(resume)}"
    )
    return system, user


def projects_prompt(resume: dict[str, Any], job_description: str, strategy: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Choose only from existing projects. You may omit, reorder, and tailor descriptions, highlights, keywords, and roles. "
        "Do not invent new project names or metadata."
    )
    user = (
        f"Job description:\n{job_description}\n\n"
        f"Strategy:\n{_json(strategy)}\n\n"
        f"Master resume:\n{_json(resume)}\n\n"
        f"Projects section:\n{_json(resume.get('projects', []))}"
    )
    return system, user


def certificates_prompt(resume: dict[str, Any], job_description: str, strategy: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Select at most 18 of the most relevant certificates by existing certificate names only. "
        "Return the strongest subset for the target job, ordered by relevance. "
        "Do not rewrite or invent certificate content."
    )
    user = (
        f"Job description:\n{job_description}\n\n"
        f"Strategy:\n{_json(strategy)}\n\n"
        f"Certificates:\n{_json(resume.get('certificates', []))}"
    )
    return system, user


def optional_sections_prompt(resume: dict[str, Any], job_description: str, strategy: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Tailor optional sections only if they already exist. "
        "For interests, keep interest names grounded in the source and tailor keywords conservatively."
    )
    user = (
        f"Job description:\n{job_description}\n\n"
        f"Strategy:\n{_json(strategy)}\n\n"
        f"Master resume:\n{_json(resume)}\n\n"
        f"Optional sections:\n{_json({'interests': resume.get('interests', [])})}"
    )
    return system, user
