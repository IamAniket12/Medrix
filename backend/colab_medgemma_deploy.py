# ============================================================
# MedGemma Colab Deployment Script
# ============================================================
# How to use:
#   1. Open a new Google Colab notebook (Runtime → Change runtime → T4 GPU)
#   2. Copy-paste each cell below sequentially, or paste the whole file
#      into a single code cell.
#   3. You MUST have accepted the MedGemma licence on Hugging Face:
#      https://huggingface.co/google/medgemma-4b-it
#   4. Set your tokens in the Colab Secrets panel (key icon on left sidebar):
#        HF_TOKEN   – your Hugging Face token (read access)
#        NGROK_TOKEN – your free ngrok authtoken (https://dashboard.ngrok.com)
#   5. After the server starts, copy the printed ngrok URL and put it in
#      your .env as  MEDGEMMA_ENDPOINT_URL=https://xxxx.ngrok-free.app
# ============================================================

# ── CELL 1 : Install dependencies ────────────────────────────────────────────
# !pip install -q \
#     transformers>=4.41.0 \
#     accelerate>=0.30.0 \
#     bitsandbytes \
#     pillow \
#     fastapi \
#     uvicorn[standard] \
#     pyngrok \
#     httpx \
#     python-multipart

# ── CELL 2 : Load secrets ────────────────────────────────────────────────────
import os
from google.colab import userdata  # type: ignore  # only available in Colab

HF_TOKEN = os.environ.get("HF_TOKEN", "")  # Set HF_TOKEN env variable before running
NGROK_TOKEN = "39zcITdaAmUNjWznQCzyb4EPL1v_6dcGsjZAdxy9yrMmd8qjm"

os.environ["HF_TOKEN"] = HF_TOKEN

# ── CELL 3 : Load MedGemma model ─────────────────────────────────────────────
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
from PIL import Image
import base64
import io

MODEL_ID = "google/medgemma-1.5-4b-it"

print(f"Loading {MODEL_ID} …  (this takes 2-4 min on first run)")

processor = AutoProcessor.from_pretrained(MODEL_ID, token=HF_TOKEN)

model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID,
    token=HF_TOKEN,
    torch_dtype=torch.bfloat16,  # saves ~50% VRAM on T4
    device_map="cuda",  # auto-places layers on GPU / CPU
)
model.eval()
print("✅ Model loaded")


# ── CELL 4 : Helper functions ─────────────────────────────────────────────────
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
                # Malformed data URL
                raise ValueError("Data URL missing ';base64,' separator")

        # Decode base64
        image_bytes = base64.b64decode(b64_string)
        if len(image_bytes) == 0:
            raise ValueError("Base64 decode resulted in empty bytes")

        # Open image with PIL
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if needed (handle RGBA, palette, grayscale, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            # Keep grayscale as-is (model handles it)
            pass
        else:
            # Already RGB
            pass

        return img

    except base64.binascii.Error as e:
        raise ValueError(f"Invalid base64 encoding: {e}")
    except Exception as e:
        raise ValueError(f"Failed to decode image: {e}")


def strip_thinking_tokens(text: str) -> str:
    """
    Strip MedGemma-1.5 internal reasoning tokens before returning output.

    MedGemma 1.5 (Gemma 3 based) may emit thinking prefixes like:
    - "thought\\n<reasoning>\\n```json\\n{...}```"
    - "<unused94> reasoning <unused95>"

    We need to aggressively strip all of these.
    """
    import re

    original_len = len(text)

    # 1. Remove full thinking blocks:  <unusedN> ... <unusedN>
    text = re.sub(r"<unused\d+>.*?<unused\d+>\s*", "", text, flags=re.DOTALL)

    # 2. Remove any stray remaining tokens
    text = re.sub(r"<unused\d+>", "", text)

    # 3. Remove "thought" prefix that appears at the start
    # This is common in Gemma 3 when thinking suppression isn't available
    if text.startswith("thought"):
        # Remove everything up to the first real output
        # Usually the thought block ends before a code fence or blank line

        # Try to find JSON output after thought block
        json_match = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
        if json_match:
            # Extract just the JSON
            text = json_match.group(1)
        else:
            # No code fence - remove "thought\n" and any following explanation
            # until we hit actual content (paragraph or list)
            lines = text.split("\n")
            output_lines = []
            in_thought = True

            for line in lines:
                # Skip "thought" header
                if line.strip().lower() == "thought":
                    continue
                # Skip empty lines at the start
                if in_thought and not line.strip():
                    continue
                # Check if this line is still explanation/reasoning
                # vs actual output
                if in_thought:
                    # If line starts with capital letter and is a complete sentence,
                    # or is a list item, or is JSON, consider it output
                    if line.strip() and (
                        line.strip()[0] in '{["'  # JSON
                        or line.strip().startswith("-")  # List
                        or line.strip().startswith("*")  # List
                        or line.strip().startswith("1.")  # Numbered list
                        or (line.strip()[0].isupper() and "." not in line[:50])
                    ):  # Sentence
                        in_thought = False
                        output_lines.append(line)
                else:
                    output_lines.append(line)

            if output_lines:
                text = "\n".join(output_lines)
            # If we couldn't parse it, just remove first 2 lines
            elif len(lines) > 2:
                text = "\n".join(lines[2:])

    text = text.strip()

    if len(text) < original_len:
        print(
            f"  ↳ Stripped thinking tokens ({original_len - len(text)} chars removed)"
        )

    return text


def run_multimodal(prompt: str, image: Image.Image, max_new_tokens: int = 2048) -> str:
    """
    Run multimodal inference (image + text prompt).
    Matches the official HuggingFace MedGemma example exactly.

    T4 GPU has 16GB VRAM. Default limit is 2048 tokens.
    For very long prompts or large images, may need to reduce further.
    """
    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},  # PIL Image directly
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

        # Cap total tokens to prevent OOM (8192 = MedGemma 1.5 4B max context)
        # T4 GPU (16GB VRAM) can handle this with BF16
        max_new_tokens = min(max_new_tokens, 8192)

        with torch.inference_mode():
            generation = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )
            generation = generation[0][input_len:]

        decoded = processor.decode(generation, skip_special_tokens=True)
        return strip_thinking_tokens(decoded)
    except torch.cuda.OutOfMemoryError:
        # Try again with reduced tokens
        torch.cuda.empty_cache()
        log.warning(f"OOM with {max_new_tokens} tokens, retrying with 4096")
        if max_new_tokens > 4096:
            return run_multimodal(prompt, image, max_new_tokens=4096)
        elif max_new_tokens > 2048:
            log.warning(f"Still OOM, retrying with 2048")
            return run_multimodal(prompt, image, max_new_tokens=2048)
        raise
    except Exception as e:
        log.exception("Multimodal inference failed")
        raise


def run_text_only(
    messages: list, max_new_tokens: int = 1024, temperature: float = 0.0
) -> str:
    """Run text-only inference (chat completion style)."""
    try:
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device, dtype=torch.bfloat16)

        input_len = inputs["input_ids"].shape[-1]

        # Cap tokens to prevent OOM (8192 = MedGemma 1.5 4B max context)
        # T4 GPU (16GB VRAM) can handle this with BF16
        max_new_tokens = min(max_new_tokens, 8192)

        with torch.inference_mode():
            generation = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )
            generation = generation[0][input_len:]

        decoded = processor.decode(generation, skip_special_tokens=True)
        return strip_thinking_tokens(decoded)
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        log.warning(f"OOM with {max_new_tokens} tokens, retrying with 4096")
        if max_new_tokens > 4096:
            return run_text_only(messages, max_new_tokens=4096, temperature=temperature)
        elif max_new_tokens > 2048:
            log.warning(f"Still OOM, retrying with 2048")
            return run_text_only(messages, max_new_tokens=2048, temperature=temperature)
        raise
    except Exception as e:
        log.exception("Text-only inference failed")
        raise


# ── CELL 5 : FastAPI server ───────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("medgemma-colab")

app = FastAPI(title="MedGemma Colab Endpoint")


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID}


@app.post("/predict")
async def predict(request: Request):
    """
    Drop-in replacement for the Vertex AI predict endpoint.

    Accepts two instance formats used by medgemma_service.py:

    Format A – image + prompt (document analysis):
        {"prompt": "...", "image": {"bytesBase64Encoded": "..."}}

    Format B – chatCompletions (text Q&A):
        {"@requestFormat": "chatCompletions",
         "messages": [...],
         "max_tokens": 320,
         "temperature": 0.2}

    Returns:
        {"predictions": [{...}], "deployed_model_id": "medgemma-4b-it-colab"}
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

            # ── Format B : chatCompletions ────────────────────────────────
            if instance.get("@requestFormat") == "chatCompletions":
                messages = instance.get("messages", [])
                # Cap at 2048 — T4 has 16 GB VRAM
                max_tok = min(int(instance.get("max_tokens", 2048)), 2048)
                temp = float(instance.get("temperature", 0.0))

                # Collect system instruction + user text + any embedded image
                system_prefix = ""
                user_text_parts = []
                embedded_image = None  # PIL Image if present

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
                                # Data URL format: "data:<mime>;base64,<b64data>"
                                url = part.get("image_url", {}).get("url", "")
                                log.info(f"  Image URL length: {len(url)}")
                                log.info(f"  Image URL prefix: {url[:60]}...")

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

                # Build the full prompt (system + user text combined)
                full_prompt = "\n\n".join(
                    filter(None, [system_prefix] + user_text_parts)
                )
                log.info(f"  Prompt length: {len(full_prompt)} chars")
                log.info(f"  Has image: {embedded_image is not None}")

                if embedded_image is not None:
                    # Image present → multimodal inference
                    log.info("  → Running multimodal inference")
                    text_out = run_multimodal(
                        full_prompt, embedded_image, max_new_tokens=max_tok
                    )
                else:
                    # Text-only → wrap in messages list for chat template
                    log.info("  → Running text-only inference")
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

            # ── Format A : image + prompt ─────────────────────────────────
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

                text_out = run_multimodal(prompt, image)
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
            "deployed_model_id": "medgemma-4b-it-colab",
        }
    )


# ── CELL 6 : Start server + ngrok tunnel ─────────────────────────────────────
import threading
import time
import uvicorn
from pyngrok import ngrok, conf

# Port 7860 is Gradio's default and is virtually never occupied in Colab.
# Using it avoids any port-conflict / runtime-disconnect issues with 8080.
PORT = 7860

# ── Close any stale ngrok tunnels from a previous run ────────────────────────
try:
    for tunnel in ngrok.get_tunnels():
        ngrok.disconnect(tunnel.public_url)
    time.sleep(0.5)
except Exception:
    pass

# Authenticate ngrok
conf.get_default().auth_token = NGROK_TOKEN


# Start uvicorn in a background thread
def _run_server():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


server_thread = threading.Thread(target=_run_server, daemon=True)
server_thread.start()

time.sleep(3)  # Give uvicorn a moment to bind before ngrok connects

# Open a public ngrok tunnel
tunnel = ngrok.connect(PORT, bind_tls=True)
PUBLIC_URL = tunnel.public_url

print("\n" + "=" * 60)
print("  MedGemma Colab Endpoint is LIVE")
print("=" * 60)
print(f"  Base URL : {PUBLIC_URL}")
print(f"  Predict  : {PUBLIC_URL}/predict")
print(f"  Health   : {PUBLIC_URL}/health")
print("=" * 60)
print("\nPaste this into your backend/.env file:")
print(f"  MEDGEMMA_ENDPOINT_URL={PUBLIC_URL}")
print("\n⚠  Keep this Colab tab open — closing it stops the server.\n")
