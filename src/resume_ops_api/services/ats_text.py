"""
ats_text.py
Converts a JSONResume dict into ATS-friendly plain text.

One label: value per line so parsers like Workday can reliably extract fields.
Call ``json_to_ats_text(data)`` with the already-parsed dict from the tailor
pipeline; no file I/O is performed here.
"""

from __future__ import annotations

from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_date(date_str: str) -> str:
    """Turn '2021-07' or '2021' into a human-readable month/year string."""
    if not date_str:
        return "Present"
    for fmt in ("%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime(
                "%B %Y" if "-" in date_str else "%Y"
            )
        except ValueError:
            pass
    return date_str


def _section(title: str) -> str:
    bar = "=" * 72
    return f"\n{bar}\n{title.upper()}\n{bar}\n"


def _sub_section() -> str:
    return "\n" + "-" * 72 + "\n"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_basics(b: dict) -> str:
    out = []
    out.append(_section("Contact Information"))
    out.append(f"Name: {b.get('name', '')}")
    out.append(f"Title: {b.get('label', '')}")
    out.append(f"Email: {b.get('email', '')}")
    out.append(f"Phone: {b.get('phone', '')}")
    loc = b.get("location", {})
    city = loc.get("city", "")
    region = loc.get("region", "")
    country = loc.get("countryCode", "")
    out.append(f"Location: {city}, {region}, {country}")
    for p in b.get("profiles", []):
        network = p.get("network", "")
        username = p.get("username", "")
        url = p.get("url", "")
        if url:
            # For dribbble, use the username as the label (e.g. "Interactive Resume")
            # since the network name itself is not meaningful to ATS parsers
            label = (
                username
                if network.lower() == "dribbble" and username
                else network
            )
            out.append(f"{label}: {url}")
    return "\n".join(out)


def _render_summary(b: dict) -> str:
    summary = b.get("summary", "").strip()
    if not summary:
        return ""
    out = [_section("Professional Summary")]
    out.append(f"Summary: {summary}")
    return "\n".join(out)


def _render_work(work: list) -> str:
    if not work:
        return ""
    out = [_section("Work Experience")]
    for i, job in enumerate(work):
        if i > 0:
            out.append(_sub_section())
        out.append(f"Job Title: {job.get('position', '')}")
        out.append(f"Company: {job.get('name', '')}")
        out.append(f"Location: {job.get('location', '')}")
        out.append(f"From: {_fmt_date(job.get('startDate', ''))}")
        out.append(f"To: {_fmt_date(job.get('endDate', ''))}")

        summary = job.get("summary", "").strip()
        highlights = job.get("highlights", [])

        if summary or highlights:
            out.append("Role Description:")
            if summary:
                out.append(summary)
            for h in highlights:
                out.append(f"- {h}")

        url = job.get("url", "")
        if url:
            out.append(f"Reference URL: {url}")
    return "\n".join(out)


def _render_education(education: list) -> str:
    if not education:
        return ""
    out = [_section("Education")]
    for i, edu in enumerate(education):
        if i > 0:
            out.append(_sub_section())
        out.append(f"Degree: {edu.get('studyType', '')}")
        out.append(f"Field of Study: {edu.get('area', '')}")
        out.append(f"Institution: {edu.get('institution', '')}")
        out.append(f"From: {_fmt_date(edu.get('startDate', ''))}")
        out.append(f"To: {_fmt_date(edu.get('endDate', ''))}")
        courses = edu.get("courses", [])
        if courses:
            out.append(f"Relevant Coursework: {', '.join(courses)}")
        url = edu.get("url", "")
        if url:
            out.append(f"Institution URL: {url}")
    return "\n".join(out)


def _render_skills(skills: list) -> str:
    if not skills:
        return ""
    out = [_section("Skills")]
    for skill in skills:
        name = skill.get("name", "")
        keywords = skill.get("keywords", [])
        out.append(f"Skill Category: {name}")
        if keywords:
            out.append(f"Keywords: {', '.join(keywords)}")
    return "\n".join(out)


def _render_certificates(certs: list) -> str:
    if not certs:
        return ""
    out = [_section("Certifications")]
    for cert in certs:
        out.append(f"Certification: {cert.get('name', '')}")
        out.append(f"Issuer: {cert.get('issuer', '')}")
        date = cert.get("date", "")
        if date:
            out.append(f"Date: {_fmt_date(date)}")
        url = cert.get("url", "")
        if url:
            out.append(f"Certification URL: {url}")
    return "\n".join(out)


def _render_projects(projects: list) -> str:
    if not projects:
        return ""
    out = [_section("Projects")]
    for i, proj in enumerate(projects):
        if i > 0:
            out.append(_sub_section())
        out.append(f"Project Name: {proj.get('name', '')}")
        start = proj.get("startDate", "")
        end = proj.get("endDate", "")
        if start:
            out.append(f"From: {_fmt_date(start)}")
        if end:
            out.append(f"To: {_fmt_date(end)}")
        desc = proj.get("description", "").strip()
        highlights = proj.get("highlights", [])
        if desc or highlights:
            out.append("Project Description:")
            if desc:
                out.append(desc)
            for h in highlights:
                out.append(f"- {h}")
        keywords = proj.get("keywords", [])
        if keywords:
            out.append(f"Keywords: {', '.join(keywords)}")
        url = proj.get("url", "")
        if url:
            out.append(f"Project URL: {url}")
    return "\n".join(out)


def _render_interests(interests: list) -> str:
    if not interests:
        return ""
    out = [_section("Interests")]
    for interest in interests:
        name = interest.get("name", "")
        keywords = interest.get("keywords", [])
        out.append(f"Interest: {name}")
        if keywords:
            out.append(f"Details: {', '.join(keywords)}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def json_to_ats_text(data: dict) -> str:
    """Convert a JSONResume dict to an ATS-friendly plain-text string."""
    parts = [
        _render_basics(data.get("basics", {})),
        _render_summary(data.get("basics", {})),
        _render_work(data.get("work", [])),
        _render_education(data.get("education", [])),
        _render_skills(data.get("skills", [])),
        _render_certificates(data.get("certificates", [])),
        _render_projects(data.get("projects", [])),
        _render_interests(data.get("interests", [])),
    ]
    return "\n".join(p for p in parts if p.strip())
