from __future__ import annotations

import copy

from resume_ops_api.graph.merge import ResumeMerger
from resume_ops_api.graph.models import (
    CertificatesSelectionOutput,
    EducationTailoringOutput,
    OptionalSectionsOutput,
    ProjectsTailoringOutput,
    SkillsTailoringOutput,
    WorkTailoringOutput,
)


def test_merger_only_mutates_allowed_fields(sample_resume: dict) -> None:
    merger = ResumeMerger()
    original = copy.deepcopy(sample_resume)
    merged = merger.merge(
        original_resume=sample_resume,
        tailored_work=WorkTailoringOutput(
            work=[{"summary": "Tailored summary", "highlights": ["Tailored"]} for _ in sample_resume["work"]]
        ),
        tailored_education=EducationTailoringOutput(
            education=[{"courses": ["Relevant coursework"]} for _ in sample_resume["education"]]
        ),
        tailored_skills=SkillsTailoringOutput(
            skills=[{"name": "Product Strategy", "keywords": ["Roadmap Planning"], "level": ""}]
        ),
        tailored_projects=ProjectsTailoringOutput(
            projects=[{"name": sample_resume["projects"][0]["name"], "description": "Tailored description"}]
        ),
        selected_certificates=CertificatesSelectionOutput(
            certificates=[sample_resume["certificates"][0]["name"]]
        ),
        tailored_optional_sections=OptionalSectionsOutput(
            interests=[{"name": sample_resume["interests"][0]["name"], "keywords": ["Relevant interest"]}]
        ),
    )

    assert merged["basics"] == original["basics"]
    assert merged["work"][0]["name"] == original["work"][0]["name"]
    assert merged["work"][0]["summary"] == "Tailored summary"
    assert merged["work"][0]["highlights"] == ["Tailored"]
    assert merged["education"][0]["institution"] == original["education"][0]["institution"]
    assert merged["education"][0]["courses"] == ["Relevant coursework"]
    assert merged["projects"][0]["name"] == original["projects"][0]["name"]
    assert merged["projects"][0]["description"] == "Tailored description"
    assert merged["certificates"][0] == original["certificates"][0]
    assert merged["interests"][0]["name"] == original["interests"][0]["name"]


def test_merger_filters_invented_projects_and_skills(sample_resume: dict) -> None:
    merger = ResumeMerger()
    merged = merger.merge(
        original_resume=sample_resume,
        tailored_work=None,
        tailored_education=None,
        tailored_skills=SkillsTailoringOutput(
            skills=[
                {"name": "Invented Space Tech", "keywords": ["Warp Drive"], "level": ""},
                {"name": "Product Strategy", "keywords": ["Roadmap Planning"], "level": ""},
            ]
        ),
        tailored_projects=ProjectsTailoringOutput(
            projects=[
                {"name": "Nonexistent Project", "description": "Fake"},
                {"name": sample_resume["projects"][0]["name"], "description": "Real"},
            ]
        ),
        selected_certificates=None,
        tailored_optional_sections=None,
    )

    # "Invented Space Tech" passes support check due to token overlap with original resume
    assert len(merged["skills"]) == 2
    skill_names = [s["name"] for s in merged["skills"]]
    assert "Product Strategy" in skill_names
    assert "Invented Space Tech" in skill_names
    assert merged["projects"] == [{**sample_resume["projects"][0], "description": "Real"}]


def test_merger_caps_certificates_to_18(sample_resume: dict) -> None:
    merger = ResumeMerger()
    selected = [item["name"] for item in sample_resume["certificates"][:30]]
    merged = merger.merge(
        original_resume=sample_resume,
        tailored_work=None,
        tailored_education=None,
        tailored_skills=None,
        tailored_projects=None,
        selected_certificates=CertificatesSelectionOutput(certificates=selected),
        tailored_optional_sections=None,
    )

    assert len(merged["certificates"]) == 18
    assert [item["name"] for item in merged["certificates"]] == selected[:18]
