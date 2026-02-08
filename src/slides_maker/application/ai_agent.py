from __future__ import annotations

import json
from typing import Any, Dict

from jsonschema import Draft202012Validator

from slides_maker.domain.schemas import SLIDE_PLAN_SCHEMA, SlidePlanDict, to_slide_plan
from slides_maker.infrastructure.openai_client import OpenAIClient


SYSTEM_PROMPT = (
    "You are a slide planning assistant. Return ONLY valid JSON. "
    "No markdown, no commentary, no code fences. "
    "The JSON must strictly follow the provided schema."
)

USER_PROMPT_TEMPLATE = (
    "Topic: {topic}\n"
    "Create a slide plan JSON with 6-10 slides. "
    "Use slide_type in [title, section, content]. "
    "Each slide must include: slide_type, heading, bullet_points (max 5), image_prompt. "
    "Ensure bullet_points is an array (may be empty for title)."
)


class SlidePlanner:
    def __init__(self, client: OpenAIClient | None = None) -> None:
        self.client = client or OpenAIClient()
        self.validator = Draft202012Validator(SLIDE_PLAN_SCHEMA)

    def generate(self, topic: str) -> SlidePlanDict:
        prompt = USER_PROMPT_TEMPLATE.format(topic=topic)
        response = self.client.chat(SYSTEM_PROMPT, prompt)
        data = self._parse_json(response["content"])
        if not self._is_valid(data):
            repaired = self._repair_json(topic, response["content"])
            if not self._is_valid(repaired):
                raise ValueError("AI output is invalid after repair")
            return repaired
        return data

    def generate_plan(self, topic: str):
        return to_slide_plan(self.generate(topic))

    def _parse_json(self, content: str) -> Dict[str, Any]:
        content = content.strip()
        return json.loads(content)

    def _is_valid(self, data: Dict[str, Any]) -> bool:
        errors = list(self.validator.iter_errors(data))
        return len(errors) == 0

    def _repair_json(self, topic: str, bad_output: str) -> Dict[str, Any]:
        repair_prompt = (
            "The previous output was invalid. Fix it to be valid JSON ONLY. "
            "Do not add markdown or code fences. "
            "Schema reminder: {schema}\n"
            "Invalid output: {bad_output}\n"
            "Topic: {topic}"
        ).format(schema=json.dumps(SLIDE_PLAN_SCHEMA), bad_output=bad_output, topic=topic)
        response = self.client.chat(SYSTEM_PROMPT, repair_prompt)
        return self._parse_json(response["content"])
