from __future__ import annotations

from fastapi import Request

from resume_ops_api.services.container import ServiceContainer


def get_container(request: Request) -> ServiceContainer:
    return request.app.state.container

