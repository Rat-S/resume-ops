from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StrategyOutput(BaseModel):
    target_narrative: str
    priority_keywords: list[str] = Field(default_factory=list)
    section_rules: list[str] = Field(default_factory=list)
    red_lines: list[str] = Field(default_factory=list)


class WorkEntryTailoring(BaseModel):
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)


class WorkTailoringOutput(BaseModel):
    work: list[WorkEntryTailoring] = Field(default_factory=list)


class EducationEntryTailoring(BaseModel):
    courses: list[str] = Field(default_factory=list)


class EducationTailoringOutput(BaseModel):
    education: list[EducationEntryTailoring] = Field(default_factory=list)


class SkillEntry(BaseModel):
    name: str = Field(..., description="The name of the skill category (e.g., Frontend Development).")
    keywords: list[str] = Field(
        default_factory=list,
        min_length=1,
        max_length=8,
        description="List of 3 to 8 keywords/technologies for this skill category."
    )


class SkillsTailoringOutput(BaseModel):
    skills: list[SkillEntry] = Field(
        default_factory=list,
        min_length=1,
        max_length=6,
        description="List of 4 to 6 skill categories tailored to the job description."
    )


class ProjectEntryTailoring(BaseModel):
    name: str = Field(..., description="The name of the project, matching the master resume verbatim.")
    description: str | None = Field(default=None, description="Tailored description of the project.")
    highlights: list[str] | None = Field(
        default=None,
        max_length=3,
        description="At most 3 key highlights or accomplishments for this project."
    )
    keywords: list[str] = Field(
        default_factory=list,
        max_length=6,
        description="At most 6 relevant technologies/keywords used in this project."
    )


class ProjectsTailoringOutput(BaseModel):
    projects: list[ProjectEntryTailoring] = Field(
        default_factory=list,
        max_length=4,
        description="List of at most 4 tailored projects that are most relevant to the target job description."
    )


class CertificatesSelectionOutput(BaseModel):
    certificates: list[str] = Field(default_factory=list)


class InterestTailoring(BaseModel):
    name: str
    keywords: list[str] = Field(default_factory=list)


class OptionalSectionsOutput(BaseModel):
    interests: list[InterestTailoring] = Field(default_factory=list)


class BasicsTailoringOutput(BaseModel):
    label: str | None = Field(default=None, description="Tailored professional title / headline matching the strategy.")
    summary: str | None = Field(
        default=None,
        description="Tailored professional summary paragraph matching the strategy. Keep it concise, writing a single punchy paragraph aiming for under 100 words."
    )


class TailorResult(BaseModel):
    resume: dict[str, Any]
    pdf_path: str
    pdf_base64: str
    theme: str
