import os
import requests
from dotenv import load_dotenv
from pathlib import Path
from app.utils.logger import logger
import json
from typing import Dict, Optional

def setup_env() -> None:
    """Initialize environment variables from .env file in root directory."""
    root_dir = Path(__file__).resolve().parent
    env_path = root_dir / '.env'
    load_dotenv(dotenv_path=env_path)

def get_openrouter_response(prompt: str) -> Dict:
    """
    Get response from OpenRouter API.
    
    Args:
        prompt: The user's input prompt
        
    Returns:
        Dict: The API response
    """
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    response = requests.post(
        url=OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        },
        json={
            "model": "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
    )
    
    return response

def main() -> None:
    """Main function to run the OpenRouter API test."""
    setup_env()
    
    # Test prompt
    test_prompt = "What is the meaning of life?"
    response = get_openrouter_response(test_prompt)
    
    if response.status_code == 200:
        logger.info(json.dumps(response.json(), indent=4))
    else:
        logger.error(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    main()



