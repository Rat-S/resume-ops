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
    name: str
    keywords: list[str] = Field(default_factory=list)


class SkillsTailoringOutput(BaseModel):
    skills: list[SkillEntry] = Field(default_factory=list)


class ProjectEntryTailoring(BaseModel):
    name: str
    description: str | None = None
    highlights: list[str] | None = None
    keywords: list[str] = Field(default_factory=list)


class ProjectsTailoringOutput(BaseModel):
    projects: list[ProjectEntryTailoring] = Field(default_factory=list)


class CertificatesSelectionOutput(BaseModel):
    certificates: list[str] = Field(default_factory=list)


class InterestTailoring(BaseModel):
    name: str
    keywords: list[str] = Field(default_factory=list)


class OptionalSectionsOutput(BaseModel):
    interests: list[InterestTailoring] = Field(default_factory=list)


class BasicsTailoringOutput(BaseModel):
    label: str | None = Field(default=None, description="Tailored professional title / headline matching the strategy.")
    summary: str | None = Field(default=None, description="Tailored professional summary paragraph matching the strategy.")


class TailorResult(BaseModel):
    resume: dict[str, Any]
    pdf_path: str
    pdf_base64: str
    theme: str
