import os, io, json, mimetypes, textwrap
from typing import Union, Optional, Tuple
import requests
from PIL import Image
import google.generativeai as genai

APIKEY = os.getenv("GEMINI_API_KEY_IMAGE")
if not APIKEY:
    APIKEY = os.getenv("GEMINI_API_KEY_1")

genai.configure(api_key=APIKEY)
model = genai.GenerativeModel("gemini-2.0-flash-lite")

cache = {}

def _read_image_and_mime(image: Union[str, bytes, io.BytesIO]) -> Tuple[bytes, str]:
    """
    Accepts: file path, URL (http/https), raw bytes, or BytesIO.
    Returns: (image_bytes, mime_type)
    """
    if isinstance(image, (bytes, bytearray)):
        img_bytes = bytes(image)
        # Try sniffing with Pillow to determine MIME.
        with Image.open(io.BytesIO(img_bytes)) as im:
            fmt = (im.format or "PNG").lower()
        mime = f"image/{'jpeg' if fmt == 'jpg' else fmt}"
        return img_bytes, mime

    if isinstance(image, io.BytesIO):
        img_bytes = image.getvalue()
        with Image.open(io.BytesIO(img_bytes)) as im:
            fmt = (im.format or "PNG").lower()
        mime = f"image/{'jpeg' if fmt == 'jpg' else fmt}"
        return img_bytes, mime

    if isinstance(image, str):
        if image.startswith("http://") or image.startswith("https://"):
            resp = requests.get(image, timeout=30)
            resp.raise_for_status()
            img_bytes = resp.content
            # Prefer server MIME; fallback to Pillow.
            mime = resp.headers.get("Content-Type")
            if not mime or not mime.startswith("image/"):
                with Image.open(io.BytesIO(img_bytes)) as im:
                    fmt = (im.format or "PNG").lower()
                mime = f"image/{'jpeg' if fmt == 'jpg' else fmt}"
            return img_bytes, mime
        else:
            with open(image, "rb") as f:
                img_bytes = f.read()
            # Guess by extension first; verify with Pillow.
            mime, _ = mimetypes.guess_type(image)
            if not mime or not mime.startswith("image/"):
                with Image.open(image) as im:
                    fmt = (im.format or "PNG").lower()
                mime = f"image/{'jpeg' if fmt == 'jpg' else fmt}"
            return img_bytes, mime

    raise TypeError("Unsupported image input. Use path, URL, bytes, or BytesIO.")


def extract_data_from_image(
    image: Union[str, bytes, io.BytesIO],
    doc_id = None,
    *,
    api_key: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 4096,
) -> str:
    """
    Analyze an image with a Gemini multimodal model and return a well-explained Markdown report.

    What you get:
      - Overview: concise what/why of the image
      - Text Data: all readable text (printed/handwritten), grouped by regions
      - Tables: each reconstructed in GitHub-Flavored Markdown (GFM)
      - Charts & Visuals: chart types, axes, units, trends, key points, plain-English explanation
      - Other Visual Insights: diagrams, forms, maps, UI components, etc.
      - Final Summary: 5–8 bullet takeaways

    Parameters
    ----------
    image : path | URL | bytes | BytesIO
        The image to analyze.
    temperature : float
        Decoding temperature; lower = more deterministic.
    max_output_tokens : int
        Cap on response size.

    Returns
    -------
    markdown : str
        A complete Markdown report suitable for saving or rendering directly.
    """

    cached_data = cache.get(doc_id)
    if cached_data:
        return cached_data

    img_bytes, mime = _read_image_and_mime(image)

    system_prompt = textwrap.dedent("""
You are an expert AI assistant for a robust RAG (Retrieval-Augmented Generation) system.
Your task is to analyze the provided image and extract all relevant informations.

Based on the image content, please do the following:

1.  **Identify the image contents** (e.g., 'table', 'bar chart', 'line graph', 'photograph', 'diagram').
2.  **Extract all text verbatim (OCR)** if any is present.
3.  **If it is a table:** Convert the entire table into a clean, pipe-delimited Markdown format.
4.  **If it is a chart or graph:** Do not just describe it. Summarize the key insights, trends, and main data points. For example, "The bar chart shows a 50% increase in Q4 sales compared to Q1."
5.  **If it is a general photograph or diagram:** Provide a detailed caption describing what is shown.
                        
    """)

    image_part = {"mime_type": mime, "data": img_bytes}

    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "response_mime_type": "application/json",
    }

    try:
        resp = model.generate_content(
            [system_prompt, image_part],
            generation_config=generation_config,
        )
        raw = resp.text or ""
    except Exception as e:
        # Don’t bury the lede—surface the exact error.
        return f"**Image Analysis Failed**\n\n> {e}\n\nCheck your API key/model name and that the image is accessible."
    cache[doc_id] = raw
    print("🟢 Image data extracted!!")
    return raw