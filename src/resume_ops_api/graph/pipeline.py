from __future__ import annotations

from pathlib import Path

from langgraph.graph import END, START, StateGraph

from resume_ops_api.core.exceptions import AppError
from resume_ops_api.graph import prompts
from resume_ops_api.graph.merge import ResumeMerger
from resume_ops_api.graph.models import (
    CertificatesSelectionOutput,
    EducationTailoringOutput,
    OptionalSectionsOutput,
    ProjectsTailoringOutput,
    SkillsTailoringOutput,
    StrategyOutput,
    WorkTailoringOutput,
)
from resume_ops_api.graph.state import ResumeGraphState
from resume_ops_api.services.llm import StructuredLLMClient
from resume_ops_api.services.renderer import ResumeRenderer
from resume_ops_api.services.schema import ResumeSchemaValidator


class ResumeGraph:
    def __init__(
        self,
        *,
        llm_client: StructuredLLMClient,
        merger: ResumeMerger,
        renderer: ResumeRenderer,
        validator: ResumeSchemaValidator,
        strategy_model: str,
        work_model: str,
        education_model: str,
        skills_model: str,
        projects_model: str,
        optional_sections_model: str,
    ) -> None:
        self.llm_client = llm_client
        self.merger = merger
        self.renderer = renderer
        self.validator = validator
        self.strategy_model = strategy_model
        self.work_model = work_model
        self.education_model = education_model
        self.skills_model = skills_model
        self.projects_model = projects_model
        self.optional_sections_model = optional_sections_model
        graph = StateGraph(ResumeGraphState)
        graph.add_node("strategy", self.strategy_node)
        graph.add_node("work_tailoring", self.work_node)
        graph.add_node("education_tailoring", self.education_node)
        graph.add_node("skills_tailoring", self.skills_node)
        graph.add_node("projects_tailoring", self.projects_node)
        graph.add_node("certificates_selection", self.certificates_node)
        graph.add_node("optional_sections_tailoring", self.optional_sections_node)
        graph.add_node("merge", self.merge_node)
        graph.add_node("render", self.render_node)
        graph.add_edge(START, "strategy")
        # Fan-out: strategy feeds all section nodes in parallel
        graph.add_edge("strategy", "work_tailoring")
        graph.add_edge("strategy", "education_tailoring")
        graph.add_edge("strategy", "skills_tailoring")
        graph.add_edge("strategy", "projects_tailoring")
        graph.add_edge("strategy", "certificates_selection")
        graph.add_edge("strategy", "optional_sections_tailoring")
        # Fan-in: all section nodes feed into merge
        graph.add_edge("work_tailoring", "merge")
        graph.add_edge("education_tailoring", "merge")
        graph.add_edge("skills_tailoring", "merge")
        graph.add_edge("projects_tailoring", "merge")
        graph.add_edge("certificates_selection", "merge")
        graph.add_edge("optional_sections_tailoring", "merge")
        graph.add_edge("merge", "render")
        graph.add_edge("render", END)
        self._compiled = graph.compile()

    async def run(self, state: ResumeGraphState) -> ResumeGraphState:
        return await self._compiled.ainvoke(state)

    async def strategy_node(self, state: ResumeGraphState) -> dict[str, StrategyOutput]:
        system, user = prompts.strategy_prompt(state["original_resume"], state["job_description"])
        strategy = await self.llm_client.generate_structured(
            model=self.strategy_model,
            system_prompt=system,
            user_prompt=user,
            response_model=StrategyOutput,
        )
        return {"strategy": strategy}

    async def work_node(self, state: ResumeGraphState) -> dict[str, WorkTailoringOutput]:
        if not state["original_resume"].get("work"):
            return {"tailored_work": WorkTailoringOutput(work=[])}
        system, user = prompts.work_prompt(
            state["original_resume"],
            state["job_description"],
            state["strategy"].model_dump(),
        )
        output = await self.llm_client.generate_structured(
            model=self.work_model,
            system_prompt=system,
            user_prompt=user,
            response_model=WorkTailoringOutput,
        )
        return {"tailored_work": output}

    async def education_node(self, state: ResumeGraphState) -> dict[str, EducationTailoringOutput]:
        if not state["original_resume"].get("education"):
            return {"tailored_education": EducationTailoringOutput(education=[])}
        system, user = prompts.education_prompt(
            state["original_resume"],
            state["job_description"],
            state["strategy"].model_dump(),
        )
        output = await self.llm_client.generate_structured(
            model=self.education_model,
            system_prompt=system,
            user_prompt=user,
            response_model=EducationTailoringOutput,
        )
        return {"tailored_education": output}

    async def skills_node(self, state: ResumeGraphState) -> dict[str, SkillsTailoringOutput]:
        system, user = prompts.skills_prompt(
            state["original_resume"],
            state["job_description"],
            state["strategy"].model_dump(),
        )
        output = await self.llm_client.generate_structured(
            model=self.skills_model,
            system_prompt=system,
            user_prompt=user,
            response_model=SkillsTailoringOutput,
        )
        return {"tailored_skills": output}

    async def projects_node(self, state: ResumeGraphState) -> dict[str, ProjectsTailoringOutput]:
        if not state["original_resume"].get("projects"):
            return {"tailored_projects": ProjectsTailoringOutput(projects=[])}
        system, user = prompts.projects_prompt(
            state["original_resume"],
            state["job_description"],
            state["strategy"].model_dump(),
        )
        output = await self.llm_client.generate_structured(
            model=self.projects_model,
            system_prompt=system,
            user_prompt=user,
            response_model=ProjectsTailoringOutput,
        )
        return {"tailored_projects": output}

    async def certificates_node(self, state: ResumeGraphState) -> dict[str, CertificatesSelectionOutput]:
        if not state["original_resume"].get("certificates"):
            return {"selected_certificates": CertificatesSelectionOutput(certificates=[])}
        system, user = prompts.certificates_prompt(
            state["original_resume"],
            state["job_description"],
            state["strategy"].model_dump(),
        )
        output = await self.llm_client.generate_structured(
            model=self.projects_model,
            system_prompt=system,
            user_prompt=user,
            response_model=CertificatesSelectionOutput,
        )
        return {"selected_certificates": output}

    async def optional_sections_node(self, state: ResumeGraphState) -> dict[str, OptionalSectionsOutput]:
        if not state["original_resume"].get("interests"):
            return {"tailored_optional_sections": OptionalSectionsOutput(interests=[])}
        system, user = prompts.optional_sections_prompt(
            state["original_resume"],
            state["job_description"],
            state["strategy"].model_dump(),
        )
        output = await self.llm_client.generate_structured(
            model=self.optional_sections_model,
            system_prompt=system,
            user_prompt=user,
            response_model=OptionalSectionsOutput,
        )
        return {"tailored_optional_sections": output}

    async def merge_node(self, state: ResumeGraphState) -> dict[str, dict]:
        final_resume = self.merger.merge(
            original_resume=state["original_resume"],
            tailored_work=state.get("tailored_work"),
            tailored_education=state.get("tailored_education"),
            tailored_skills=state.get("tailored_skills"),
            tailored_projects=state.get("tailored_projects"),
            selected_certificates=state.get("selected_certificates"),
            tailored_optional_sections=state.get("tailored_optional_sections"),
        )
        self.validator.validate(final_resume, context="tailored resume", status_code=500)
        return {"final_resume": final_resume}

    async def render_node(self, state: ResumeGraphState) -> dict[str, str]:
        output_dir: Path = state["output_dir"]
        if not state.get("final_resume"):
            raise AppError("Cannot render before merge completes.", code="render_without_resume", status_code=500)
        pdf_path = await self.renderer.render(
            resume=state["final_resume"],
            theme=state["theme"],
            output_dir=output_dir,
        )
        return {"pdf_path": str(pdf_path)}

