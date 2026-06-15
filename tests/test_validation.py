from __future__ import annotations

import pytest
from pydantic import ValidationError

from resume_ops_api.graph.models import (
    ProjectsTailoringOutput,
    WorkTailoringOutput,
    EducationTailoringOutput,
    CertificatesSelectionOutput,
    OptionalSectionsOutput,
)


def test_validate_project_names_success():
    context = {
        "original_resume": {
            "projects": [
                {"name": "resume-ops"},
                {"name": "job-ops"},
            ]
        }
    }
    data = {
        "projects": [
            {"name": "resume-ops", "description": "A resume tailor", "keywords": ["Python"]},
            {"name": "Job-Ops", "description": "Job search", "keywords": ["Go"]},  # Check case-insensitivity
        ]
    }
    # Should validate successfully
    obj = ProjectsTailoringOutput.model_validate(data, context=context)
    assert len(obj.projects) == 2
    assert obj.projects[0].name == "resume-ops"
    assert obj.projects[1].name == "Job-Ops"


def test_validate_project_names_failure():
    context = {
        "original_resume": {
            "projects": [
                {"name": "resume-ops"},
            ]
        }
    }
    data = {
        "projects": [
            {"name": "hallucinated-project", "description": "Does not exist"},
        ]
    }
    with pytest.raises(ValidationError) as excinfo:
        ProjectsTailoringOutput.model_validate(data, context=context)
    
    assert "Project name 'hallucinated-project' does not match any project name in the master resume verbatim" in str(excinfo.value)


def test_validate_work_count_success():
    context = {
        "original_resume": {
            "work": [
                {"name": "Google"},
                {"name": "Facebook"},
            ]
        }
    }
    data = {
        "work": [
            {"summary": "Built search", "highlights": []},
            {"summary": "Built feed", "highlights": []},
        ]
    }
    obj = WorkTailoringOutput.model_validate(data, context=context)
    assert len(obj.work) == 2


def test_validate_work_count_failure():
    context = {
        "original_resume": {
            "work": [
                {"name": "Google"},
                {"name": "Facebook"},
            ]
        }
    }
    data = {
        "work": [
            {"summary": "Only one job", "highlights": []},
        ]
    }
    with pytest.raises(ValidationError) as excinfo:
        WorkTailoringOutput.model_validate(data, context=context)
    
    assert "The number of work items returned (1) must align 1:1 with the master resume (2)" in str(excinfo.value)


def test_validate_education_count_success():
    context = {
        "original_resume": {
            "education": [
                {"institution": "Stanford"},
            ]
        }
    }
    data = {
        "education": [
            {"courses": ["CS101"]},
        ]
    }
    obj = EducationTailoringOutput.model_validate(data, context=context)
    assert len(obj.education) == 1


def test_validate_education_count_failure():
    context = {
        "original_resume": {
            "education": [
                {"institution": "Stanford"},
            ]
        }
    }
    data = {
        "education": []
    }
    with pytest.raises(ValidationError) as excinfo:
        EducationTailoringOutput.model_validate(data, context=context)
    
    assert "The number of education items returned (0) must align 1:1 with the master resume (1)" in str(excinfo.value)


def test_validate_certificate_names_success():
    context = {
        "original_resume": {
            "certificates": [
                {"name": "AWS Certified Solutions Architect"},
                {"name": "Certified Kubernetes Administrator"},
            ]
        }
    }
    data = {
        "certificates": [
            "aws certified solutions architect",
            "Certified Kubernetes Administrator",
        ]
    }
    obj = CertificatesSelectionOutput.model_validate(data, context=context)
    assert len(obj.certificates) == 2


def test_validate_certificate_names_failure():
    context = {
        "original_resume": {
            "certificates": [
                {"name": "AWS Certified Solutions Architect"},
            ]
        }
    }
    data = {
        "certificates": [
            "GCP Cloud Digital Leader",
        ]
    }
    with pytest.raises(ValidationError) as excinfo:
        CertificatesSelectionOutput.model_validate(data, context=context)
    
    assert "Certificate 'GCP Cloud Digital Leader' does not exist in the master resume" in str(excinfo.value)


def test_validate_interest_names_success():
    context = {
        "original_resume": {
            "interests": [
                {"name": "Hiking"},
                {"name": "Chess"},
            ]
        }
    }
    data = {
        "interests": [
            {"name": "hiking", "keywords": []},
            {"name": "Chess", "keywords": []},
        ]
    }
    obj = OptionalSectionsOutput.model_validate(data, context=context)
    assert len(obj.interests) == 2


def test_validate_interest_names_failure():
    context = {
        "original_resume": {
            "interests": [
                {"name": "Hiking"},
            ]
        }
    }
    data = {
        "interests": [
            {"name": "Gaming", "keywords": []},
        ]
    }
    with pytest.raises(ValidationError) as excinfo:
        OptionalSectionsOutput.model_validate(data, context=context)
    
    assert "Interest 'Gaming' does not exist in the master resume" in str(excinfo.value)
