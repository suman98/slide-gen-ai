from __future__ import annotations

import argparse
from pathlib import Path

from slides_maker.application.ai_agent import SlidePlanner
from slides_maker.application.image_service import build_image_service
from slides_maker.application.ppt_builder import PPTBuilder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a PPTX from a topic.")
    parser.add_argument("topic", type=str, help="Topic for the presentation")
    parser.add_argument("--out", type=str, default="output/presentation.pptx")
    parser.add_argument("--images", type=str, default="output/images")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.out)
    image_dir = Path(args.images)

    planner = SlidePlanner()
    plan = planner.generate_plan(args.topic)

    image_service = build_image_service(image_dir)
    image_paths = []
    for idx, slide in enumerate(plan.slides, start=1):
        filename = f"slide_{idx:02d}.png"
        image_path = image_service.generate_image(slide.image_prompt, filename)
        image_paths.append(image_path)

    builder = PPTBuilder()
    for slide, image_path in zip(plan.slides, image_paths):
        builder.add_slide(slide, image_path=image_path)

    builder.save(output_path)


if __name__ == "__main__":
    main()
