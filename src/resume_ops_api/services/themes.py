from __future__ import annotations

from resume_ops_api.core.exceptions import AppError


class ThemeService:
    def __init__(self, allowed_themes: list[str], default_theme: str) -> None:
        self.allowed_themes = allowed_themes
        self.default_theme = default_theme
        if default_theme not in allowed_themes:
            raise AppError(
                "DEFAULT_THEME must be present in ALLOWED_THEMES.",
                code="invalid_theme_configuration",
                status_code=500,
            )

    def resolve(self, candidate: str | None) -> str:
        theme = (candidate or self.default_theme).strip()
        if theme not in self.allowed_themes:
            raise AppError(
                f"Theme '{theme}' is not allowed.",
                code="invalid_theme",
                status_code=400,
                details={"allowed_themes": self.allowed_themes},
            )
        return theme

