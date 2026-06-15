import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[3]
REPO_DIR = BACKEND_DIR.parent


@dataclass(frozen=True)
class LlmConfig:
    provider: str

    ollama_url: str
    ollama_model: str

    llamacpp_base_url: str
    llamacpp_host: str
    llamacpp_port: int
    llamacpp_server_path: Path
    llamacpp_model_path: Path
    llamacpp_model: str
    llamacpp_ctx_size: int | None
    llamacpp_gpu_layers: int | None
    llamacpp_threads: int | None
    llamacpp_start_timeout_seconds: int
    llamacpp_log_path: Path


def _load_env_files() -> None:
    load_dotenv(REPO_DIR / ".env", override=False)
    load_dotenv(BACKEND_DIR / ".env", override=False)


def _optional_int(name: str) -> int | None:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return None

    return int(value)


def _path_env(name: str, default: str, *, base_dir: Path | None = None) -> Path:
    path = Path(os.getenv(name, default))

    if path.is_absolute() or base_dir is None:
        return path

    return base_dir / path


def load_llm_config() -> LlmConfig:
    _load_env_files()

    llamacpp_host = os.getenv("LLAMACPP_HOST", "127.0.0.1")
    llamacpp_port = int(os.getenv("LLAMACPP_PORT", "8080"))
    llamacpp_model_path = _path_env(
        "LLAMACPP_MODEL_PATH",
        r"D:\llama\models\qwen3-14b.gguf",
    )

    return LlmConfig(
        provider=os.getenv("LLM_PROVIDER", "ollama").strip().lower(),
        ollama_url=os.getenv(
            "OLLAMA_URL",
            "http://localhost:11434/api/generate",
        ),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:14b"),
        llamacpp_base_url=os.getenv(
            "LLAMACPP_BASE_URL",
            f"http://{llamacpp_host}:{llamacpp_port}",
        ).rstrip("/"),
        llamacpp_host=llamacpp_host,
        llamacpp_port=llamacpp_port,
        llamacpp_server_path=_path_env(
            "LLAMACPP_SERVER_PATH",
            r"D:\llama\llamacpp\llama-server.exe",
        ),
        llamacpp_model_path=llamacpp_model_path,
        llamacpp_model=os.getenv(
            "LLAMACPP_MODEL",
            llamacpp_model_path.stem,
        ),
        llamacpp_ctx_size=_optional_int("LLAMACPP_CTX_SIZE"),
        llamacpp_gpu_layers=_optional_int("LLAMACPP_GPU_LAYERS"),
        llamacpp_threads=_optional_int("LLAMACPP_THREADS"),
        llamacpp_start_timeout_seconds=int(
            os.getenv("LLAMACPP_START_TIMEOUT_SECONDS", "120")
        ),
        llamacpp_log_path=_path_env(
            "LLAMACPP_LOG_PATH",
            "logs/llama_cpp_server.log",
            base_dir=BACKEND_DIR,
        ),
    )
