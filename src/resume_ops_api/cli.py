import argparse
import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

from resume_ops_api.core.config import settings
from resume_ops_api.services.container import ServiceContainer

# Configure basic logging for the CLI
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def async_main(args: argparse.Namespace) -> int:
    resume_path = Path(args.resume)
    jd_path = Path(args.jd)
    output_pdf_path = Path(args.output)
    output_json_path = Path(args.output_json) if args.output_json else None

    if not resume_path.is_file():
        logging.error(f"Resume file not found: {resume_path}")
        return 1

    if not jd_path.is_file():
        logging.error(f"Job Description file not found: {jd_path}")
        return 1

    try:
        resume_data = json.loads(resume_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse resume JSON: {e}")
        return 1

    job_description = jd_path.read_text(encoding="utf-8")

    logging.info("Initializing service container...")
    container = ServiceContainer(settings)

    theme = args.theme
    if not theme:
        theme = container.theme_service.default_theme
    else:
        # Validate the theme using the theme service
        try:
            theme = container.theme_service.resolve(theme)
        except Exception as e:
            logging.error(f"Theme error: {e}")
            return 1

    logging.info(f"Starting tailoring process with theme '{theme}'...")
    try:
        result = await container.orchestrator.run(
            resume=resume_data,
            job_description=job_description,
            theme=theme,
        )
    except Exception as e:
        logging.error(f"Tailoring failed: {e}")
        return 1

    # Ensure output directory exists
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy the generated PDF to the requested location
    if result.pdf_path and Path(result.pdf_path).is_file():
        shutil.copy(result.pdf_path, output_pdf_path)
        logging.info(f"Successfully wrote PDF to {output_pdf_path}")
    else:
        logging.error("PDF was not generated successfully.")
        return 1

    # Optionally save the tailored JSON
    if output_json_path:
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(result.resume, indent=2, ensure_ascii=False), encoding="utf-8")
        logging.info(f"Successfully wrote tailored JSON to {output_json_path}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Tailor a JSON resume to a job description.")
    parser.add_argument(
        "--resume",
        required=True,
        help="Path to the master resume JSON file",
    )
    parser.add_argument(
        "--jd",
        required=True,
        help="Path to the job description text/markdown file",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path where the final tailored PDF should be saved",
    )
    parser.add_argument(
        "--output-json",
        help="Optional path to save the tailored JSON resume",
    )
    parser.add_argument(
        "--theme",
        help="Theme to use for the PDF generation",
    )

    args = parser.parse_args()

    try:
        sys.exit(asyncio.run(async_main(args)))
    except KeyboardInterrupt:
        logging.info("Process interrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
