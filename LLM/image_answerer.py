import os
import requests
import google.generativeai as genai
from PIL import Image
from io import BytesIO
from typing import List, Union

from dotenv import load_dotenv

load_dotenv()

APIKEY = os.getenv("GEMINI_API_KEY_IMAGE")
if not APIKEY:
    APIKEY = os.getenv("GEMINI_API_KEY_1")

genai.configure(api_key=APIKEY)

def load_image(image_source: str) -> Image.Image:
    """Load image from a URL or local path."""
    try:
        if image_source.startswith("http://") or image_source.startswith("https://"):
            response = requests.get(image_source)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGB")
        elif os.path.isfile(image_source):
            return Image.open(image_source).convert("RGB")
        else:
            raise ValueError("Invalid image source: must be a valid URL or file path")
    except Exception as e:
        raise RuntimeError(f"Failed to load image: {e}")

def get_answer_for_image(image_source: str, questions: List[str], retries: int = 3) -> List[str]:
    """Ask questions about an image using Gemini Vision model."""
    image = load_image(image_source)
    prompt =  """
    Answer the following questions about the image. Give the answers in the same order as the questions. 
    Answers should be descriptive. give one answer per line with numbering as "1. 2.  3. ..".
    Example answer:
    1. Answer 1, Explaination
    2. Answer 2, Explaination

    Questions: 
    """
    prompt += "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    model = genai.GenerativeModel("gemini-1.5-flash")
    
    for attempt in range(retries):
        try:
            response = model.generate_content(
                [prompt, image],
                generation_config=genai.types.GenerationConfig(temperature=0.4)
            )
            raw_text = response.text.strip()
            answers = extract_ordered_answers(raw_text, len(questions))
            if len(answers) == len(questions):
                return answers
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed after {retries} attempts: {e}")

    raise RuntimeError("Failed to get valid response from Gemini.")

def extract_ordered_answers(raw_text: str, expected_count: int) -> List[str]:
    """Parse the raw Gemini output into a clean list of answers."""
    import re
    lines = raw_text.splitlines()
    answers = []
    for line in lines:
        match = re.match(r"^\s*(\d+)[\).\s-]*\s*(.+)", line)
        if match:
            answers.append(match.group(2).strip())
    if len(answers) < expected_count:
        # fallback: use plain lines if numbering failed
        answers = [line.strip() for line in lines if line.strip()]
    return answers[:expected_count]

