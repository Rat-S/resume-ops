from __future__ import annotations

import asyncio
import json
from pathlib import Path

from resume_ops_api.core.exceptions import AppError


class ResumeRenderer:
    def __init__(self, binary: str = "resumed") -> None:
        self.binary = binary

    async def render(self, *, resume: dict, theme: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        input_path = output_dir / "resume.json"
        pdf_path = output_dir / "output.pdf"
        input_path.write_text(json.dumps(resume, ensure_ascii=True, indent=2), encoding="utf-8")
        process = await asyncio.create_subprocess_exec(
            self.binary,
            "export",
            str(input_path),
            "--theme",
            theme,
            "-o",
            str(pdf_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise AppError(
                "PDF rendering failed.",
                code="render_failed",
                status_code=500,
                details={"stderr": stderr.decode("utf-8", errors="ignore")},
            )
        header = pdf_path.read_bytes()[:5]
        if header != b"%PDF-":
            raise AppError(
                "Renderer output was not a valid PDF.",
                code="invalid_pdf_output",
                status_code=500,
                details={"output_path": str(pdf_path)},
            )
        return pdf_path
