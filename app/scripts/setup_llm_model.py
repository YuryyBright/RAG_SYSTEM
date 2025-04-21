# scripts/setup_llm_model.py

import os
import subprocess
import argparse
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_url
from dotenv import load_dotenv

load_dotenv()

def patch_env(key: str, value: str, env_path: str = ".env"):
    """Patch or add a key-value pair inside .env file."""
    if not os.path.exists(env_path):
        print("❌ .env file not found.")
        return

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(env_path, "w", encoding="utf-8") as f:
        updated = False
        for line in lines:
            if line.startswith(key + "="):
                f.write(f"{key}={value}\n")
                updated = True
            else:
                f.write(line)
        if not updated:
            f.write(f"{key}={value}\n")

    print(f"✅ Patched {key}={value} in {env_path}")

def download_hf_model(model_name: str, local_dir: str, file_types: list[str] = None):
    """Download model from HuggingFace Hub."""
    if os.path.exists(local_dir):
        print(f"✅ Model already exists locally at: {local_dir}")
        return

    print(f"⬇️ Downloading '{model_name}' to '{local_dir}'...")
    kwargs = {"local_dir_use_symlinks": False, "resume_download": True}

    if file_types:
        kwargs["allow_patterns"] = [f"*.{ext}" for ext in file_types]

    snapshot_download(
        repo_id=model_name,
        local_dir=local_dir,
        **kwargs
    )
    print(f"✅ Download complete: {local_dir}")

def download_ollama_model(model_name: str):
    """Download model from Ollama."""
    print(f"⬇️ Pulling '{model_name}' via Ollama...")
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"✅ Ollama pull complete: {model_name}")
    except Exception as e:
        print(f"❌ Failed to pull from Ollama: {e}")
        raise

def check_model_size(path: str, threshold_gb: float = 16.0):
    """Check model size and warn if large."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)

    size_gb = total_size / (1024 ** 3)
    print(f"📦 Model size: {size_gb:.2f} GB")

    if size_gb > threshold_gb:
        print("⚠️ WARNING: Model size exceeds 16GB. Ensure your server has enough memory.")

def verify_model_compatibility(local_dir: str, backend: str) -> bool:
    """Verify if the downloaded model is compatible with backend (mock implementation)."""
    if backend == "ollama":
        # Ollama expects .gguf models
        for file in Path(local_dir).rglob("*.gguf"):
            return True
        print("❌ No .gguf file found for Ollama backend.")
        return False
    elif backend == "transformers":
        # Transformers expect config.json and model weights
        config = Path(local_dir) / "config.json"
        if config.exists():
            return True
        print("❌ No config.json found for Transformers backend.")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Setup LLM model for local inference.")
    parser.add_argument("--source", required=True, choices=["hf", "ollama"], help="Source platform (Huggingface or Ollama)")
    parser.add_argument("--model-name", required=True, help="Model repo name or Ollama model tag")
    parser.add_argument("--env-key", required=False, help=".env key to patch with model path")
    parser.add_argument("--file-types", nargs="+", required=False, help="Only download specific file types (e.g. gguf, safetensors)")
    parser.add_argument("--backend", required=False, choices=["ollama", "transformers"], help="Target inference backend")

    args = parser.parse_args()

    if args.source == "hf":
        model_name = args.model_name
        local_path = os.path.join("models", model_name.split("/")[-1])
        download_hf_model(model_name, local_path, file_types=args.file_types)
        check_model_size(local_path)

        if args.backend:
            compatible = verify_model_compatibility(local_path, args.backend)
            if not compatible:
                print("❌ Model may not be usable by backend. Fix manually!")

        if args.env_key:
            patch_env(args.env_key, local_path.replace("\\", "/"))

    elif args.source == "ollama":
        download_ollama_model(args.model_name)
        # Ollama manages models internally, no local path needed

if __name__ == "__main__":
    main()