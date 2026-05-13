from __future__ import annotations

import copy
import re
from typing import Any

from resume_ops_api.core.exceptions import AppError
from resume_ops_api.graph.models import (
    CertificatesSelectionOutput,
    EducationTailoringOutput,
    OptionalSectionsOutput,
    ProjectsTailoringOutput,
    SkillsTailoringOutput,
    WorkTailoringOutput,
)

TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize(value: str) -> str:
    return " ".join(TOKEN_RE.findall(value.lower()))


def _tokenize(value: str) -> set[str]:
    return set(TOKEN_RE.findall(value.lower()))


def _stringify(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_stringify(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def _clean_string_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    return [item.strip() for item in values if item and item.strip()]


class ResumeMerger:
    def merge(
        self,
        *,
        original_resume: dict[str, Any],
        tailored_work: WorkTailoringOutput | None,
        tailored_education: EducationTailoringOutput | None,
        tailored_skills: SkillsTailoringOutput | None,
        tailored_projects: ProjectsTailoringOutput | None,
        selected_certificates: CertificatesSelectionOutput | None,
        tailored_optional_sections: OptionalSectionsOutput | None,
    ) -> dict[str, Any]:
        merged = copy.deepcopy(original_resume)
        merged["basics"] = copy.deepcopy(original_resume.get("basics", {}))
        self._merge_work(merged, original_resume, tailored_work)
        self._merge_education(merged, original_resume, tailored_education)
        self._merge_skills(merged, original_resume, tailored_skills)
        self._merge_projects(merged, original_resume, tailored_projects)
        self._merge_certificates(merged, original_resume, selected_certificates)
        self._merge_optional_sections(merged, original_resume, tailored_optional_sections)
        return merged

    def _merge_work(
        self,
        merged: dict[str, Any],
        original_resume: dict[str, Any],
        tailored_work: WorkTailoringOutput | None,
    ) -> None:
        original_work = copy.deepcopy(original_resume.get("work", []))
        if not original_work:
            return
        if tailored_work and tailored_work.work and len(tailored_work.work) != len(original_work):
            raise AppError(
                "Tailored work output must align 1:1 with the original work history.",
                code="invalid_work_output",
                status_code=500,
            )
        for index, original_entry in enumerate(original_work):
            if not tailored_work or index >= len(tailored_work.work):
                continue
            original_entry["highlights"] = _clean_string_list(tailored_work.work[index].highlights)
        merged["work"] = original_work

    def _merge_education(
        self,
        merged: dict[str, Any],
        original_resume: dict[str, Any],
        tailored_education: EducationTailoringOutput | None,
    ) -> None:
        original_education = copy.deepcopy(original_resume.get("education", []))
        if not original_education:
            return
        if tailored_education and tailored_education.education and len(tailored_education.education) != len(original_education):
            raise AppError(
                "Tailored education output must align 1:1 with the original education history.",
                code="invalid_education_output",
                status_code=500,
            )
        for index, original_entry in enumerate(original_education):
            if not tailored_education or index >= len(tailored_education.education):
                continue
            original_entry["courses"] = _clean_string_list(tailored_education.education[index].courses)
        merged["education"] = original_education

    def _merge_skills(
        self,
        merged: dict[str, Any],
        original_resume: dict[str, Any],
        tailored_skills: SkillsTailoringOutput | None,
    ) -> None:
        if not tailored_skills:
            return
        corpus_text = _normalize(_stringify(original_resume))
        corpus_tokens = _tokenize(corpus_text)
        filtered: list[dict[str, Any]] = []
        for skill in tailored_skills.skills:
            supported_name = self._is_supported(skill.name, corpus_text, corpus_tokens)
            supported_keywords = [
                keyword
                for keyword in _clean_string_list(skill.keywords)
                if self._is_supported(keyword, corpus_text, corpus_tokens)
            ]
            if not supported_name and not supported_keywords:
                continue
            filtered.append(
                {
                    "name": skill.name.strip(),
                    "level": (skill.level or "").strip(),
                    "keywords": supported_keywords,
                }
            )
        merged["skills"] = filtered

    def _merge_projects(
        self,
        merged: dict[str, Any],
        original_resume: dict[str, Any],
        tailored_projects: ProjectsTailoringOutput | None,
    ) -> None:
        if not tailored_projects:
            return
        original_projects = original_resume.get("projects", [])
        originals_by_name = {_normalize(project.get("name", "")): project for project in original_projects}
        merged_projects: list[dict[str, Any]] = []
        for project in tailored_projects.projects:
            normalized_name = _normalize(project.name)
            original = originals_by_name.get(normalized_name)
            if not original:
                continue
            updated = copy.deepcopy(original)
            if project.description is not None:
                updated["description"] = project.description.strip()
            if project.highlights is not None:
                updated["highlights"] = _clean_string_list(project.highlights)
            if project.keywords is not None:
                updated["keywords"] = _clean_string_list(project.keywords)
            if project.roles is not None:
                updated["roles"] = _clean_string_list(project.roles)
            merged_projects.append(updated)
        merged["projects"] = merged_projects

    def _merge_certificates(
        self,
        merged: dict[str, Any],
        original_resume: dict[str, Any],
        selected_certificates: CertificatesSelectionOutput | None,
    ) -> None:
        if not selected_certificates:
            return
        original_certificates = original_resume.get("certificates", [])
        originals_by_name = {_normalize(certificate.get("name", "")): certificate for certificate in original_certificates}
        merged["certificates"] = [
            copy.deepcopy(originals_by_name[name_key])
            for name in selected_certificates.certificates
            if (name_key := _normalize(name)) in originals_by_name
        ]

    def _merge_optional_sections(
        self,
        merged: dict[str, Any],
        original_resume: dict[str, Any],
        tailored_optional_sections: OptionalSectionsOutput | None,
    ) -> None:
        if not tailored_optional_sections:
            return
        original_interests = original_resume.get("interests")
        if not original_interests:
            return
        originals_by_name = {_normalize(interest.get("name", "")): interest for interest in original_interests}
        merged_interests: list[dict[str, Any]] = []
        for interest in tailored_optional_sections.interests:
            normalized_name = _normalize(interest.name)
            original = originals_by_name.get(normalized_name)
            if not original:
                continue
            updated = copy.deepcopy(original)
            updated["keywords"] = _clean_string_list(interest.keywords)
            merged_interests.append(updated)
        merged["interests"] = merged_interests

    def _is_supported(self, value: str, corpus_text: str, corpus_tokens: set[str]) -> bool:
        normalized = _normalize(value)
        if not normalized:
            return False
        if normalized in corpus_text:
            return True
        tokens = _tokenize(normalized)
        significant = {token for token in tokens if len(token) > 2}
        if not significant:
            return False
        overlap = significant & corpus_tokens
        return len(overlap) / len(significant) >= 0.5

