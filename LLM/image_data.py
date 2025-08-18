# pip install google-generativeai pillow requests
import os, io, json, mimetypes, textwrap
from typing import Union, Optional, Tuple
import requests
from PIL import Image
import google.generativeai as genai

APIKEY = os.getenv("GEMINI_API_KEY_IMAGE")
if not APIKEY:
    APIKEY = os.getenv("GEMINI_API_KEY_1")

genai.configure(api_key=APIKEY)
model = genai.GenerativeModel("gemini-1.5-flash")


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

    img_bytes, mime = _read_image_and_mime(image)

    system_prompt = textwrap.dedent("""
        You are a meticulous vision data extractor. Analyze the image and output a single JSON object.
        Be accurate. If a detail is unclear or not legible, write "unknown" or omit the field.
        Do NOT add any text outside of the JSON. Do NOT wrap with code fences.

        JSON schema (keys and semantics):
        {
          "overview": "1–3 sentences summarizing what the image contains and why it might matter.",
          "text_blocks": [
            {
              "region": "short label like header/body/footer/annotation N",
              "text": "verbatim text as read left-to-right, top-to-bottom"
            }
          ],
          "tables": [
            {
              "title": "table caption or inferred title, or 'Table 1'",
              "markdown": "GitHub-Flavored Markdown table with header row if present.",
              "notes": "mention merged cells, footnotes, units, approximations"
            }
          ],
          "charts": [
            {
              "title": "e.g., Sales by Quarter (2019–2024)",
              "type": "bar | line | pie | scatter | heatmap | other",
              "axes": {
                "x": {"label": "string or 'unknown'", "units": "string or 'none'"},
                "y": {"label": "string or 'unknown'", "units": "string or 'none'"}
              },
              "series": [
                {"name": "series name or 'overall'", "trend": "one-sentence trend"}
              ],
              "key_points": [
                "3–6 concise bullets with concrete values if legible"
              ],
              "approx_data": [
                {"x": "value/category", "y": "numeric or 'unknown'", "series": "optional series name"}
              ],
              "explanation": "clear lay summary (4–8 sentences) of what the chart shows and why it matters"
            }
          ],
          "other_visuals": [
            {
              "type": "diagram | map | UI | form | infographic | other",
              "description": "what it depicts and how the parts relate",
              "entities": ["list key labels/nodes/components"],
              "relationships": ["brief relationships or flows"]
            }
          ],
          "final_summary": "5–8 bullets: the most actionable insights across text/tables/charts."
        }

        Additional directives:
        - Keep all tables in valid Markdown pipe-table format.
        - Use consistent units; if inferring units, state that they are inferred.
        - Prefer faithful extraction over guessing; do not invent numbers.
        - For handwriting or blurry text, include best-effort text with a note.
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

    # Try reading strict JSON. If it fails, we return whatever the model sent.
    data = None
    try:
        data = json.loads(raw)
    except Exception:
        # Fallback: the model might have returned near-JSON or text. Return as-is.
        return f"## Image Analysis\n\n{raw.strip()}"

    # Compose a clean Markdown report.
    lines = []

    def add(section_title: str):
        lines.append(f"## {section_title}")

    # Overview
    if data.get("overview"):
        add("Overview")
        lines.append(data["overview"].strip())
        lines.append("")

    # Text blocks
    text_blocks = data.get("text_blocks") or []
    if text_blocks:
        add("Text Data (OCR)")
        for i, tb in enumerate(text_blocks, 1):
            region = tb.get("region") or f"region {i}"
            text = (tb.get("text") or "").strip()
            if text:
                lines.append(f"**{region}:**")
                # Preserve line breaks but keep it tidy
                lines.append("")
                lines.append(text)
                lines.append("")
        lines.append("")

    # Tables
    tables = data.get("tables") or []
    if tables:
        add("Tables")
        for i, t in enumerate(tables, 1):
            title = t.get("title") or f"Table {i}"
            markdown_tbl = (t.get("markdown") or "").strip()
            notes = (t.get("notes") or "").strip()
            lines.append(f"**{title}**")
            lines.append("")
            if markdown_tbl:
                lines.append(markdown_tbl)
                lines.append("")
            if notes:
                lines.append(f"_Notes:_ {notes}")
                lines.append("")
        lines.append("")

    # Charts & Visuals
    charts = data.get("charts") or []
    if charts:
        add("Charts & Visuals")
        for c in charts:
            title = c.get("title") or "Chart"
            ctype = c.get("type") or "other"
            lines.append(f"**{title}** — _{ctype}_")
            axes = c.get("axes") or {}
            x = axes.get("x") or {}
            y = axes.get("y") or {}
            lines.append(f"- **X-axis:** {x.get('label','unknown')} ({x.get('units','none')})")
            lines.append(f"- **Y-axis:** {y.get('label','unknown')} ({y.get('units','none')})")
            series = c.get("series") or []
            if series:
                lines.append("- **Series/Trends:**")
                for s in series:
                    nm = s.get("name") or "overall"
                    tr = s.get("trend") or ""
                    lines.append(f"  - {nm}: {tr}")
            kps = c.get("key_points") or []
            if kps:
                lines.append("- **Key points:**")
                for kp in kps:
                    lines.append(f"  - {kp}")
            approx = c.get("approx_data") or []
            if approx:
                lines.append("- **Approximate data (if legible):**")
                for row in approx:
                    xs = row.get("x")
                    ys = row.get("y")
                    ser = row.get("series")
                    tag = f" [{ser}]" if ser else ""
                    lines.append(f"  - {xs} → {ys}{tag}")
            explain = c.get("explanation")
            if explain:
                lines.append("")
                lines.append(explain.strip())
            lines.append("")
        lines.append("")

    # Other visuals
    others = data.get("other_visuals") or []
    if others:
        add("Other Visual Insights")
        for o in others:
            typ = o.get("type") or "other"
            desc = o.get("description") or ""
            ents = o.get("entities") or []
            rels = o.get("relationships") or []
            lines.append(f"- **{typ.capitalize()}:** {desc}")
            if ents:
                lines.append(f"  - Entities: {', '.join(ents)}")
            if rels:
                lines.append(f"  - Relationships: {', '.join(rels)}")
        lines.append("")

    # Final summary
    if data.get("final_summary"):
        add("Final Summary")
        # If model returned multiple bullets as a single string, keep them as text.
        lines.append(data["final_summary"].strip())
        lines.append("")

    markdown = "\n".join(lines).strip() or "No content extracted."
    return markdown


# --- Example usage ---
# report = analyze_image_to_markdown("invoice_or_dashboard.png")
# print(report)
