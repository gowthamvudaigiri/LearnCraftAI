from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from src.models import GeneratedQuiz, GenerationRequest, LessonPlan, SourceAnalysis, ValidationReport

PROMPT_DIR = Path(__file__).parents[1] / "prompts"

def _prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")

def _request_payload(request: GenerationRequest) -> dict[str, Any]:
    payload = request.model_dump(mode="json")
    payload.pop("attachment_descriptors", None)
    return payload

def _source_payload(sources: list[dict]) -> list[dict[str, Any]]:
    return [
        {
            "source_id": source.get("source_id"),
            "filename": source.get("filename"),
            "pages": source.get("pages"),
            "status": source.get("status"),
            "text_excerpt": source.get("text", "")[:20_000],
        }
        for source in sources
    ]

def _source_content_blocks(sources: list[dict]) -> list[dict[str, Any]]:
    blocks=[]
    for source in sources:
        data=source.get("analysis_data")
        mime_type=source.get("mime_type")
        if not isinstance(data,(bytes,bytearray)) or not mime_type:
            continue
        encoded=base64.b64encode(data).decode("ascii")
        if mime_type == "application/pdf":
            blocks.append({
                "type":"file",
                "source_type":"base64",
                "mime_type":mime_type,
                "data":encoded,
                "filename":source.get("filename") or "source.pdf",
            })
        elif mime_type.startswith("image/"):
            blocks.append({
                "type":"image",
                "source_type":"base64",
                "mime_type":mime_type,
                "data":encoded,
            })
    return blocks

def friendly_llm_error(error: Exception) -> str:
    message = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", str(error))
    lowered = message.casefold()
    if "authentication" in lowered or "incorrect api key" in lowered or "401" in lowered:
        return "The configured OpenAI API key was rejected. Check the server environment."
    if "rate limit" in lowered or "429" in lowered:
        return "The model rate limit was reached. Wait briefly or choose another model."
    if "model" in lowered and ("not found" in lowered or "does not exist" in lowered):
        return "That model is unavailable for this API key. Choose a model available to your OpenAI project."
    if "function tools with reasoning_effort" in lowered:
        return "This model requires Responses API structured output. Restart the updated app and try again."
    return message[:500]

class OpenAIContentProvider:
    """OpenAI provider configured with a server-side API key."""

    def __init__(self, api_key: str, model: str, client: Any | None = None):
        if not api_key.strip():
            raise ValueError("OPENAI_API_KEY is not configured on the server.")
        if not model.strip():
            raise ValueError("Choose or enter an OpenAI model.")
        self.model = model.strip()
        client_options = {
            "api_key": api_key.strip(),
            "model": self.model,
            "temperature": None,
            "timeout": 120,
            "max_retries": 2,
            "use_responses_api": True,
            "output_version": "responses/v1",
        }
        if self.model.casefold().startswith("gpt-5.6"):
            client_options["reasoning"] = {"effort": "none"}
        self.client = client or ChatOpenAI(**client_options)

    def _invoke(self, schema, system_prompt: str, payload: dict[str, Any], content_blocks: list[dict[str, Any]] | None = None):
        structured = self.client.with_structured_output(schema, method="json_schema")
        payload_text=json.dumps(payload,ensure_ascii=False,default=str)
        human=(
            HumanMessage(content=[{"type":"text","text":payload_text},*(content_blocks or [])])
            if content_blocks
            else ("human",payload_text)
        )
        return structured.invoke([("system",system_prompt),human])

    def analyze(self, request: GenerationRequest, sources: list[dict]) -> SourceAnalysis:
        return self._invoke(
            SourceAnalysis,
            _prompt("source_analyst.md"),
            {"request": _request_payload(request), "untrusted_sources": _source_payload(sources)},
            _source_content_blocks(sources),
        )

    def generate_lesson(self, request: GenerationRequest, analysis: SourceAnalysis) -> LessonPlan:
        return self._invoke(
            LessonPlan,
            _prompt("lesson_author.md"),
            {"request": _request_payload(request), "approved_source_analysis": analysis.model_dump(mode="json")},
        )

    def generate_quiz(self, request: GenerationRequest, analysis: SourceAnalysis) -> GeneratedQuiz:
        return self._invoke(
            GeneratedQuiz,
            _prompt("quiz_writer.md"),
            {"request": _request_payload(request), "approved_source_analysis": analysis.model_dump(mode="json")},
        )

    def repair_quiz(
        self,
        request: GenerationRequest,
        analysis: SourceAnalysis,
        quiz: GeneratedQuiz,
        report: ValidationReport,
    ) -> GeneratedQuiz:
        return self._invoke(
            GeneratedQuiz,
            _prompt("repair.md"),
            {
                "request": _request_payload(request),
                "approved_source_analysis": analysis.model_dump(mode="json"),
                "quiz_to_repair": quiz.model_dump(mode="json"),
                "validation_issues": report.model_dump(mode="json"),
            },
        )
