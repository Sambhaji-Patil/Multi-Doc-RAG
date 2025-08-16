from groq import Groq
import os
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY_LITE = os.getenv("GROQ_API_KEY_LITE", "")
if GROQ_API_KEY_LITE == "":
    GROQ_API_KEY_LITE = os.getenv("GROQ_API_KEY_LITE") 

GROQ_MODEL_LITE = "llama3-8b-8192"

assert GROQ_API_KEY_LITE, "GROQ KEY LITE NOT SET"

client = Groq(api_key=GROQ_API_KEY_LITE)

def generate_lite(
    prompt: str, 
    temperature: float = 0.7, 
    max_tokens: int = 1024,
) -> str:
    """
    Generate a response using Groq API
    
    Args:
        prompt (str): The input prompt to send to the model
        temperature (float): Controls randomness (0.0 to 2.0, default 0.7)
        max_tokens (int): Maximum number of tokens to generate (default 1024)
        model (str): The model to use (default "llama3-8b-8192")
        api_key (str, optional): Groq API key. If None, reads from GROQ_API_KEY env var
    
    Returns:
        str: The generated response from Groq
    
    Raises:
        Exception: If API call fails or authentication issues occur
    """
    try:
        # Initia
        
        # Make API call
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=GROQ_MODEL_LITE,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Extract and return the response
        response = chat_completion.choices[0].message.content
        return response
        
    except Exception as e:
        raise Exception(f"Error generating response from Groq: {str(e)}")


# Example usage
if __name__ == "__main__":
    try:
        response = generate_lite(
            prompt="Explain quantum computing in simple terms",
            temperature=0.7,
            max_tokens=500
        )
        print("Response:", response)
        
    except Exception as e:
        print(f"Error: {e}")