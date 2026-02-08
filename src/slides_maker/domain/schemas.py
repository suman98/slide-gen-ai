from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, TypedDict


SlideType = Literal["title", "section", "content"]


class SlideDict(TypedDict):
    slide_type: SlideType
    heading: str
    bullet_points: List[str]
    image_prompt: str


class SlidePlanDict(TypedDict):
    topic: str
    slides: List[SlideDict]


SLIDE_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["topic", "slides"],
    "properties": {
        "topic": {"type": "string", "minLength": 1},
        "slides": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["slide_type", "heading", "bullet_points", "image_prompt"],
                "properties": {
                    "slide_type": {
                        "type": "string",
                        "enum": ["title", "section", "content"],
                    },
                    "heading": {"type": "string", "minLength": 1},
                    "bullet_points": {
                        "type": "array",
                        "maxItems": 5,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "image_prompt": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}


@dataclass
class Slide:
    slide_type: SlideType
    heading: str
    bullet_points: List[str]
    image_prompt: str


@dataclass
class SlidePlan:
    topic: str
    slides: List[Slide]


def to_slide_plan(data: SlidePlanDict) -> SlidePlan:
    slides = [
        Slide(
            slide_type=slide["slide_type"],
            heading=slide["heading"],
            bullet_points=slide["bullet_points"],
            image_prompt=slide["image_prompt"],
        )
        for slide in data["slides"]
    ]
    return SlidePlan(topic=data["topic"], slides=slides)
