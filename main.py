import os
import uvicorn
import warnings
from src.api.server import app

# Suppress annoying Langchain Pydantic V1 deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

def pre_download_models():
    """
    Downloads required tokenizers and background models locally into a .cache 
    directory before starting the app. This prevents runtime HF warnings, 
    speeds up the first API request, and prevents crashes in offline Docker modes.
    If the files already exist, the huggingface_hub naturally skips downloading.
    """
    try:
        from huggingface_hub import snapshot_download
        print("Verifying and pre-loading Hugging Face dependencies locally...")
        
        # We specify the exact model ID that langchain or other libs implicitly need.
        # Often this is a tokenizer like standard mistral, or sentence-transformers
        model_id = "mistralai/Mistral-7B-Instruct-v0.2" # Adjust if you use a specific local embedding model
        
        # Download only the Tokenizer config to prevent huge 14GB bin downloads
        snapshot_download(
            repo_id=model_id, 
            allow_patterns=["*.json", "*.model", "tokenizer*"], 
            local_dir=os.environ.get("HF_HOME")
        )
        print("Models successfully verified in local cache!")
    except Exception as e:
        print(f"Model pre-load warning (Safe to ignore if using API): {e}")

def main():
    """
    Main Entry Point for the Advanced Multi-Hop RAG API.
    Runs the FastAPI application using Uvicorn.
    """
    # 1. Force all Hugging Face operations to use our local directory
    os.environ["HF_HOME"] = os.path.abspath("./.cache/huggingface")
    os.makedirs(os.environ["HF_HOME"], exist_ok=True)
    
    # 2. Check and Download (Skip if exists)
    pre_download_models()
    
    # 3. Start Server
    port = int(os.environ.get("PORT", 9000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # We pass the application instance string for hot-reloading 
    uvicorn.run("main:app", host=host, port=port)

if __name__ == "__main__":
    main()
