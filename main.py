import os
import uvicorn
import warnings
from src.api.server import app
from src.config import Config

# Suppress annoying Langchain Pydantic V1 deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

def pre_download_models():
    """
    Downloads required tokenizer config files locally into HF_HOME before starting
    the app. This prevents runtime HF warnings, speeds up the first API request,
    and prevents crashes in offline Docker modes.

    Key design decisions:
    - We skip the download entirely if the tokenizer.json is already on disk.
      This means the first cold boot downloads it once (~100 KB), all subsequent
      restarts are instant — even on HF Spaces where the cache volume is re-mounted.
    - We download ONLY the tokenizer config files (*.json, *.model, tokenizer*),
      NOT the 14 GB model weights, using allow_patterns.
    - The 'e5-mistral-7b-instruct' tokenizer is used because it perfectly aligns
      with the 'mistral-embed' API endpoint token count used in src/config.py.
    """
    hf_home = os.environ.get("HF_HOME", Config.HF_HOME)

    # Fast path: if tokenizer.json already exists anywhere under HF_HOME, skip.
    tokenizer_marker = os.path.join(hf_home, "tokenizer.json")
    if os.path.exists(tokenizer_marker):
        print(f"Tokenizer cache found at {hf_home} — skipping download.")
        return

    try:
        from huggingface_hub import snapshot_download
        print("First boot — downloading tokenizer config files (~100 KB)...")
        model_id = "intfloat/e5-mistral-7b-instruct"

        snapshot_download(
            repo_id=model_id,
            allow_patterns=["*.json", "*.model", "tokenizer*"],
            local_dir=hf_home,
            # Ignore symlinks — some HF Spaces file systems don't support them
            local_files_only=False,
        )
        print("Tokenizer config successfully cached in local storage!")
    except Exception as e:
        # Non-fatal: the app still works without a local tokenizer.
        # LangChain falls back gracefully when the tokenizer is unavailable.
        print(f"Tokenizer pre-load skipped (safe to ignore if using API-only mode): {e}")


def main():
    """
    Main entry point for the SoftMania Chat-Bot API.
    Runs the FastAPI application using Uvicorn.
    """
    # 1. Force all Hugging Face operations to use our designated local directory
    os.environ["HF_HOME"] = Config.HF_HOME
    os.makedirs(Config.HF_HOME, exist_ok=True)

    # 2. Pre-download tokenizer config files (skip if already cached)
    if Config.LOCAL_EMBEDDING_MODEL:
        pre_download_models()

    # 3. Start the production server
    # HF Spaces injects PORT=7860; Config reads it via os.getenv.
    # reload=False is REQUIRED in production — the file watcher wastes ~50 MB RAM
    # and can unexpectedly restart the app when temp files are written to disk.
    uvicorn.run(
        "src.api.server:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
