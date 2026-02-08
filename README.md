# Slides Maker

## Overview
Generate a professional PowerPoint (.pptx) from a topic using an AI slide planner, pluggable image generation, and python-pptx.

## Requirements
- Python 3.11

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure
Set environment variables for the OpenAI-compatible API:

```bash
export OPENAI_API_KEY="your_key_here"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
```

Optional image generation via OpenAI:

```bash
export USE_OPENAI_IMAGES="1"
export OPENAI_IMAGE_MODEL="gpt-image-1"
```

## Run
```bash
PYTHONPATH=src python main.py "Your Topic Here" --out output/presentation.pptx
```

## Output
- PowerPoint file: output/presentation.pptx
- Images: output/images/
