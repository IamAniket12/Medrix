"""
Quick diagnostic: sends a tiny test image to the Colab /predict endpoint
and prints the raw response so we can see if the model is reading the image.
Run: python test_colab_endpoint.py
"""

import urllib.request
import base64
import json
import struct
import zlib

ENDPOINT = "https://prophesiable-adversarially-lawanda.ngrok-free.dev"


def make_png(w: int, h: int, rgb_data: bytes) -> bytes:
    """Build a valid minimal PNG from raw RGB bytes."""

    def chunk(name: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + name + data
        return c + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + rgb_data[y * w * 3 : (y + 1) * w * 3] for y in range(h))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def call(payload: dict, label: str) -> None:
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print("=" * 60)
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{ENDPOINT}/predict",
        data=data,
        headers={
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
            print(json.dumps(resp, indent=2))
    except Exception as e:
        print(f"ERROR: {e}")


# ── Test 1: Health ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("TEST: /health")
print("=" * 60)
req = urllib.request.Request(
    f"{ENDPOINT}/health",
    headers={"ngrok-skip-browser-warning": "true"},
)
with urllib.request.urlopen(req, timeout=10) as r:
    print(json.dumps(json.loads(r.read()), indent=2))

# ── Test 2: chatCompletions WITH tiny red image ─────────────────────────────
png = make_png(10, 10, b"\xff\x00\x00" * 100)  # 10×10 solid red
b64 = base64.b64encode(png).decode()
data_url = f"data:image/png;base64,{b64}"

call(
    {
        "instances": [
            {
                "@requestFormat": "chatCompletions",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What color is this image? Reply in one word only.",
                            },
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                "max_tokens": 20,
                "temperature": 0.0,
            }
        ]
    },
    "chatCompletions with image (expect: red)",
)

# ── Test 3: chatCompletions text-only ───────────────────────────────────────
call(
    {
        "instances": [
            {
                "@requestFormat": "chatCompletions",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Reply with just the word HELLO and nothing else.",
                            }
                        ],
                    }
                ],
                "max_tokens": 10,
                "temperature": 0.0,
            }
        ]
    },
    "chatCompletions text-only (expect: HELLO)",
)
