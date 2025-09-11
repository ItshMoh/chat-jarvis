import requests
import json
import os
from typing import Dict, Any

def search_web_perplexity(query: str, 
                         max_tokens: int = 500, 
                         temperature: float = 0.7,
                         model: str = "sonar") -> Dict[str, Any]:
    """
    Search the web using Perplexity AI API
    
    Args:
        query: The search query
        max_tokens: Maximum tokens in response
        temperature: Response creativity (0.0 to 1.0)
        model: Perplexity model to use
        
    Returns:
        Dictionary containing the search response or error
    """
    try:
        api_key = os.getenv('PPLX_API_KEY')
        if not api_key:
            return {
                "success": False,
                "error": "PERPLEXITY_API_KEY not found in environment variables"
            }
        
        url = "https://api.perplexity.ai/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Be precise and concise. Provide accurate, up-to-date information with relevant sources when possible."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        
        response.raise_for_status()
        response_data = response.json()
        
        # Extract the content from the response
        if "choices" in response_data and len(response_data["choices"]) > 0:
            content = response_data["choices"][0]["message"]["content"]
            return {
                "success": True,
                "content": content,
                "model_used": model,
                "usage": response_data.get("usage", {})
            }
        else:
            return {
                "success": False,
                "error": "No response content found"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}"
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to decode JSON response: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }

