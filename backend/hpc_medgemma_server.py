#!/usr/bin/env python3
"""
MedGemma HPC Deployment Script
==============================
Standalone server script for running MedGemma 1.5 4B on HPC with ngrok tunneling.

Prerequisites:
    pip install transformers>=4.41.0 accelerate>=0.30.0 bitsandbytes pillow \
                fastapi uvicorn[standard] pyngrok httpx python-multipart torch

Usage:
    python hpc_medgemma_server.py

The script will:
    1. Load MedGemma model on GPU
    2. Start FastAPI server on port 8000
    3. Create ngrok tunnel and print the public URL
    4. Accept requests in the same format as Vertex AI endpoints
"""

import os
import sys
import logging
import threading
import time
import base64
import io
from typing import Any, Dict, List

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
from PIL import Image
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
from pyngrok import ngrok

# ============================================================
# Configuration
# ============================================================

HF_TOKEN = os.environ.get("HF_TOKEN", "")  # Set HF_TOKEN env variable before running
NGROK_TOKEN = "39zcITdaAmUNjWznQCzyb4EPL1v_6dcGsjZAdxy9yrMmd8qjm"
MODEL_ID = "google/medgemma-1.5-4b-it"
PORT = 8000
MAX_TOKENS = 8192  # Always use max context window (we have powerful GPU)

# Set environment variables
os.environ["HF_TOKEN"] = HF_TOKEN

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("medgemma-hpc")

# ============================================================
# Global Model Variables
# ============================================================

processor = None
model = None

# ============================================================
# Helper Functions
# ============================================================


def decode_b64_image(b64_string: str) -> Image.Image:
    """
    Decode a base-64 encoded image string to a PIL Image.
    Handles both raw base64 strings and data URLs.
    """
    try:
        # Remove data URL prefix if present
        if b64_string.startswith("data:"):
            # Format: data:image/png;base64,<b64data>
            if ";base64," in b64_string:
                b64_string = b64_string.split(";base64,", 1)[1]
            else:
                raise ValueError("Data URL missing ';base64,' separator")

        # Decode base64
        image_bytes = base64.b64decode(b64_string)
        if len(image_bytes) == 0:
            raise ValueError("Base64 decode resulted in empty bytes")

        # Open image with PIL
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if needed
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            pass  # Keep grayscale as-is
        else:
            pass  # Already RGB

        return img

    except base64.binascii.Error as e:
        raise ValueError(f"Invalid base64 encoding: {e}")
    except Exception as e:
        raise ValueError(f"Failed to decode image: {e}")


def strip_thinking_tokens(text: str) -> str:
    """
    Strip MedGemma-1.5 internal reasoning tokens before returning output.

    MedGemma 1.5 may emit thinking prefixes like:
    - "thought\\n<reasoning>\\n```json\\n{...}```"
    - "<unused94> reasoning <unused95>"
    """
    import re

    original_len = len(text)

    # 1. Remove full thinking blocks: <unusedN> ... <unusedN>
    text = re.sub(r"<unused\d+>.*?<unused\d+>\s*", "", text, flags=re.DOTALL)

    # 2. Remove any stray remaining tokens
    text = re.sub(r"<unused\d+>", "", text)

    # 3. Remove "thought" prefix that appears at the start
    if text.startswith("thought"):
        # Try to find JSON output after thought block
        json_match = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        else:
            # Remove everything up to first JSON object
            lines = text.split("\n")
            output_lines = []
            in_thought = True

            for line in lines:
                if line.strip().lower() == "thought":
                    continue
                if in_thought and not line.strip():
                    continue
                if in_thought:
                    if line.strip() and (
                        line.strip()[0] in '{["'
                        or line.strip().startswith("-")
                        or line.strip().startswith("*")
                        or line.strip().startswith("1.")
                        or (line.strip()[0].isupper() and "." not in line[:50])
                    ):
                        in_thought = False
                        output_lines.append(line)
                else:
                    output_lines.append(line)

            if output_lines:
                text = "\n".join(output_lines)
            elif len(lines) > 2:
                text = "\n".join(lines[2:])

    text = text.strip()

    if len(text) < original_len:
        log.debug(
            f"Stripped thinking tokens ({original_len - len(text)} chars removed)"
        )

    return text


def run_multimodal(
    prompt: str, image: Image.Image, max_new_tokens: int = MAX_TOKENS
) -> str:
    """
    Run multimodal inference (image + text prompt).
    Always uses MAX_TOKENS (8192) for powerful GPU.
    """
    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device, dtype=torch.bfloat16)

        input_len = inputs["input_ids"].shape[-1]
        # Always use MAX_TOKENS - we have powerful GPU
        max_new_tokens = MAX_TOKENS

        with torch.inference_mode():
            generation = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=None,
            )
            generation = generation[0][input_len:]

        decoded = processor.decode(generation, skip_special_tokens=True)
        return strip_thinking_tokens(decoded)

    except Exception as e:
        log.exception("Multimodal inference failed")
        raise


def run_text_only(
    messages: list, max_new_tokens: int = MAX_TOKENS, temperature: float = 0.0
) -> str:
    """
    Run text-only inference (chat completion style).
    Always uses MAX_TOKENS (8192) for powerful GPU.
    """
    try:
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device, dtype=torch.bfloat16)

        input_len = inputs["input_ids"].shape[-1]
        # Always use MAX_TOKENS - we have powerful GPU
        max_new_tokens = MAX_TOKENS

        with torch.inference_mode():
            generation = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=(temperature > 0),
                temperature=temperature if temperature > 0 else None,
            )
            generation = generation[0][input_len:]

        decoded = processor.decode(generation, skip_special_tokens=True)
        return strip_thinking_tokens(decoded)

    except Exception as e:
        log.exception("Text-only inference failed")
        raise


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(title="MedGemma HPC Endpoint")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": MODEL_ID,
        "device": str(model.device) if model else "not_loaded",
    }


@app.post("/predict")
async def predict(request: Request):
    """
    Drop-in replacement for the Vertex AI predict endpoint.

    Accepts two instance formats:

    Format A – image + prompt (document analysis):
        {"prompt": "...", "image": {"bytesBase64Encoded": "..."}}

    Format B – chatCompletions (text Q&A):
        {"@requestFormat": "chatCompletions",
         "messages": [...],
         "max_tokens": 8192,
         "temperature": 0.0}

    Returns:
        {"predictions": [{...}], "deployed_model_id": "medgemma-4b-it-hpc"}
    """
    try:
        body: Dict[str, Any] = await request.json()
    except Exception as e:
        log.error(f"Failed to parse request JSON: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    instances: List[Dict[str, Any]] = body.get("instances", [])

    if not instances:
        raise HTTPException(status_code=422, detail="'instances' list is required")

    log.info(f"Processing {len(instances)} instance(s)")
    results = []

    for idx, instance in enumerate(instances):
        try:
            log.info(f"\n--- Processing instance {idx} ---")

            # ── Format B: chatCompletions ────────────────────────────────
            if instance.get("@requestFormat") == "chatCompletions":
                messages = instance.get("messages", [])
                # Always use MAX_TOKENS (8192) - we have powerful GPU
                max_tok = MAX_TOKENS
                temp = float(instance.get("temperature", 0.0))

                log.info(f"  Using max tokens: {max_tok} (HPC optimized)")

                # Collect system instruction + user text + any embedded image
                system_prefix = ""
                user_text_parts = []
                embedded_image = None

                for msg in messages:
                    role = msg.get("role", "")
                    content = msg.get("content", [])
                    parts = (
                        content
                        if isinstance(content, list)
                        else [{"type": "text", "text": str(content)}]
                    )

                    for part in parts:
                        ptype = part.get("type", "text")

                        if role == "system" and ptype == "text":
                            system_prefix = part.get("text", "")

                        elif role == "user":
                            if ptype == "text":
                                user_text_parts.append(part.get("text", ""))

                            elif ptype == "image_url":
                                url = part.get("image_url", {}).get("url", "")
                                log.info(f"  Image URL length: {len(url)}")

                                if not url:
                                    log.warning("  Empty image URL")
                                    continue

                                try:
                                    embedded_image = decode_b64_image(url)
                                    log.info(
                                        f"  ✓ Decoded image: {embedded_image.size} {embedded_image.mode}"
                                    )
                                except Exception as img_err:
                                    log.error(f"  ❌ Image decode failed: {img_err}")
                                    raise ValueError(
                                        f"Failed to decode image: {img_err}"
                                    )

                # Build the full prompt
                full_prompt = "\n\n".join(
                    filter(None, [system_prefix] + user_text_parts)
                )
                log.info(f"  Prompt length: {len(full_prompt)} chars")
                log.info(f"  Has image: {embedded_image is not None}")

                if embedded_image is not None:
                    # Image present → multimodal inference
                    log.info(f"  → Running multimodal inference (max_tokens={max_tok})")
                    text_out = run_multimodal(
                        full_prompt, embedded_image, max_new_tokens=max_tok
                    )
                else:
                    # Text-only → wrap in messages list for chat template
                    log.info(f"  → Running text-only inference (max_tokens={max_tok})")
                    flat_messages = [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": full_prompt}],
                        }
                    ]
                    text_out = run_text_only(
                        flat_messages, max_new_tokens=max_tok, temperature=temp
                    )

                log.info(f"  ✓ Generated {len(text_out)} chars")
                results.append(
                    {
                        "choices": [
                            {
                                "message": {"role": "assistant", "content": text_out},
                                "finish_reason": "stop",
                            }
                        ]
                    }
                )

            # ── Format A: image + prompt ─────────────────────────────────
            else:
                prompt = instance.get("prompt", "")
                img_data = instance.get("image", {})
                b64_str = img_data.get("bytesBase64Encoded", "")

                if not b64_str:
                    raise ValueError(
                        "No image data provided in instance['image']['bytesBase64Encoded']"
                    )
                if not prompt:
                    prompt = (
                        "Analyze this medical document and extract: "
                        "document type, patient info, date, findings, medications, "
                        "test results, and provide a brief summary."
                    )

                log.info(
                    f"  Format A: prompt={len(prompt)} chars, b64={len(b64_str)} chars"
                )

                try:
                    image = decode_b64_image(b64_str)
                    log.info(f"  ✓ Decoded image: {image.size} {image.mode}")
                except Exception as img_err:
                    log.error(f"  ❌ Image decode failed: {img_err}")
                    raise ValueError(f"Failed to decode image: {img_err}")

                # Always use MAX_TOKENS for powerful GPU
                text_out = run_multimodal(prompt, image, max_new_tokens=MAX_TOKENS)
                log.info(f"  ✓ Generated {len(text_out)} chars")

                results.append(
                    {
                        "text": text_out,
                        "labels": [],
                        "summary": (
                            text_out[:300] + "…" if len(text_out) > 300 else text_out
                        ),
                    }
                )

        except ValueError as ve:
            log.error(f"Validation error in instance {idx}: {ve}")
            results.append({"error": str(ve)})
        except torch.cuda.OutOfMemoryError as oom:
            log.error(f"GPU OOM in instance {idx}")
            torch.cuda.empty_cache()
            results.append(
                {"error": "GPU out of memory - try reducing image size or max_tokens"}
            )
        except Exception as exc:
            log.exception(f"Inference error in instance {idx}")
            results.append({"error": str(exc)})

    return JSONResponse(
        {
            "predictions": results,
            "deployed_model_id": "medgemma-4b-it-hpc",
        }
    )


# ============================================================
# Model Loading
# ============================================================


def load_model():
    """Load MedGemma model and processor."""
    global processor, model

    log.info(f"Loading {MODEL_ID} ... (this may take 2-4 minutes on first run)")

    try:
        # Load processor
        processor = AutoProcessor.from_pretrained(MODEL_ID, token=HF_TOKEN)

        # Load model
        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID,
            token=HF_TOKEN,
            torch_dtype=torch.bfloat16,  # Saves ~50% VRAM
            device_map="auto",  # Auto-place layers on GPU/CPU
        )
        model.eval()

        log.info("✅ Model loaded successfully")
        log.info(f"   Device: {model.device}")
        log.info(f"   Dtype: {model.dtype}")

    except Exception as e:
        log.error(f"Failed to load model: {e}")
        sys.exit(1)


# ============================================================
# Server Startup
# ============================================================


def start_server():
    """Start FastAPI server with ngrok tunnel."""
    log.info(f"Starting FastAPI server on port {PORT}...")

    # Set ngrok auth token
    ngrok.set_auth_token(NGROK_TOKEN)

    # Start ngrok tunnel
    log.info("Creating ngrok tunnel...")
    tunnel = ngrok.connect(PORT, bind_tls=True)
    public_url = tunnel.public_url

    log.info("=" * 70)
    log.info(f"🚀 MedGemma HPC Server is LIVE!")
    log.info(f"📍 Public URL: {public_url}")
    log.info(f"🏥 Model: {MODEL_ID}")
    log.info(f"💡 Health check: {public_url}/health")
    log.info(f"📡 Predict endpoint: {public_url}/predict")
    log.info("=" * 70)
    log.info("\n⚠️  Copy the Public URL above and set it in your .env file:")
    log.info(f"   MEDGEMMA_ENDPOINT_URL={public_url}\n")
    log.info("Press Ctrl+C to stop the server\n")

    # Start uvicorn server (blocking)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    log.info("🔬 MedGemma HPC Server - Starting...")

    # Check CUDA availability
    if not torch.cuda.is_available():
        log.warning("⚠️  CUDA not available! Model will run on CPU (very slow)")
    else:
        log.info(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
        log.info(
            f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB"
        )

    # Clear GPU cache
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Load model
    load_model()

    # Start server
    try:
        start_server()
    except KeyboardInterrupt:
        log.info("\n\n👋 Server shutting down...")
        sys.exit(0)
    except Exception as e:
        log.error(f"Server error: {e}")
        sys.exit(1)
