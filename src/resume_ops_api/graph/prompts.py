from __future__ import annotations

import json
from typing import Any


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2)


def strategy_prompt(resume: dict[str, Any], job_description: str) -> tuple[str, str]:
    system = (
        "You are tailoring a resume without inventing facts. "
        "Return only structured JSON matching the following structure:\n"
        "{\n"
        "  \"target_narrative\": \"string\",\n"
        "  \"priority_keywords\": [\"string\"],\n"
        "  \"section_rules\": [\"string\"],\n"
        "  \"red_lines\": [\"string\"]\n"
        "}\n"
        "Use the full master resume for context to determine the tailoring strategy."
    )
    user = f"Job description:\n{job_description}\n\nMaster resume:\n{_json(resume)}"
    return system, user


def work_prompt(resume: dict[str, Any], job_description: str, strategy: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Tailor only the summary and highlights for each work item. "
        "Do not change company names, positions, dates, locations, urls, or order. "
        "Do not invent unsupported responsibilities or achievements. "
        "CRITICAL: The output 'work' list MUST align 1:1 in length and order with the input list. "
        "Return EXACTLY the same number of work entries in the same order. Do not skip or drop any items. "
        "Return structured JSON with this key: work (a list of objects with summary and highlights)."
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
        "Tailor only education courses. Preserve institution, degree, dates, scores, and other metadata exactly. "
        "CRITICAL: The output 'education' list MUST align 1:1 in length and order with the input list. "
        "Return EXACTLY the same number of education entries in the same order. Do not skip or drop any items. "
        "Return structured JSON with this key: education (a list of objects with courses list)."
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
        "Keep JSON Resume skill objects. Do not invent unsupported skills. "
        "Return structured JSON with this key: skills (a list of objects with name, level, and keywords)."
    )
    user = (
        f"Job description:\n{job_description}\n\n"
        f"Strategy:\n{_json(strategy)}\n\n"
        f"Master resume:\n{_json(resume)}"
    )
    return system, user


def projects_prompt(resume: dict[str, Any], job_description: str, strategy: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Choose only from existing projects. You may omit, reorder, and tailor descriptions and highlights. "
        "CRITICAL: You MUST keep the 'name' of each project EXACTLY as provided in the master resume. "
        "Do not alter project names even slightly (e.g. spelling, casing, symbols), or they will be dropped during merge. "
        "For each project, retain or tailor its 'keywords' list (technologies used) matching the StackOverflow layout theme. "
        "Return structured JSON with this key: projects (a list of tailored project objects with name, description, highlights, and keywords)."
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
        "Select only certificates that have a strong, direct mapping to the target role's priority keywords. "
        "Return a maximum of 18, but fewer if they do not meet a strict relevance threshold. "
        "Do not rewrite or invent certificate names; use existing certificate names verbatim. "
        "Return structured JSON with this key: certificates (a list of certificate names)."
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


def basics_prompt(resume: dict[str, Any], job_description: str, strategy: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Tailor only the professional label (headline/title) and the main summary paragraph "
        "of the basics section. "
        "Do not invent unsupported responsibilities or achievements. "
        "Do not modify other basics details like name, email, phone, location, profiles, or url. "
        "Return structured JSON with keys: label and summary."
    )
    user = (
        f"Job description:\n{job_description}\n\n"
        f"Strategy:\n{_json(strategy)}\n\n"
        f"Master resume for context:\n{_json(resume)}\n\n"
        f"Target basics section:\n{_json(resume.get('basics', {}))}"
    )
    return system, user
