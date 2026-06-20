import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

def get_llm_config() -> Dict[str, Any]:
    """
    Parses environment variables and returns a dictionary containing 
    the baseline kwargs (model, api_base, api_key) required by LiteLLM.
    """
    provider = os.getenv("LLM_PROVIDER", "llamacpp").lower().strip()
    config: Dict[str, Any] = {}

    if provider == "llamacpp":
        base_url = os.getenv("LLAMACPP_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
        config["model"] = "openai/llamacpp"
        config["api_base"] = f"{base_url}/v1"  # Uses modern llama-server OpenAI endpoint proxy
        config["api_key"] = "local-no-key"

    elif provider == "groq":
        # Supports your .env typo (GROG) or standard spelling
        groq_key = os.getenv("GROG_KEY") or os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("Groq API key missing in environment variables.")
        
        config["model"] = os.getenv("GROQ_MODEL", "groq/llama-3.3-70b-versatile")
        config["api_key"] = groq_key

    elif provider == "ollama":
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        # Cleans up the raw endpoint url if it contains the generate path
        if "/api/generate" in ollama_url:
            ollama_url = ollama_url.split("/api/generate")[0]
            
        config["model"] = f"ollama/{os.getenv('OLLAMA_MODEL', 'qwen3:14b')}"
        config["api_base"] = ollama_url
        
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER specified: {provider}")

    return config