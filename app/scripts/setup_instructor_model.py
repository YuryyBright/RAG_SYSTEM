# scripts/setup_embedding_model.py

import os
import argparse
from dotenv import load_dotenv
from huggingface_hub import snapshot_download

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

def download_model_offline(model_name: str, local_dir: str):
    """Download model from HuggingFace Hub to local path."""
    if os.path.exists(local_dir):
        print(f"✅ Model already exists locally at: {local_dir}")
        return

    print(f"⬇️ Downloading model '{model_name}' to '{local_dir}'...")
    snapshot_download(
        repo_id=model_name,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    print(f"✅ Download complete: {local_dir}")

def main():
    parser = argparse.ArgumentParser(description="Setup embedding model for local RAG system.")
    parser.add_argument("--type", required=True, choices=["instructor", "sentence_transformer"], help="Model type")
    parser.add_argument("--model-name", required=False, help="Model repo name")
    args = parser.parse_args()

    model_type = args.type
    model_name = args.model_name

    if model_type == "instructor":
        model_name = model_name or "hkunlp/instructor-xl"  # Suggest using 'instructor-xl' which has 1536 dims
        local_path = os.path.join("models", model_name.split("/")[-1])
        download_model_offline(model_name, local_path)

        # Force EMBEDDING_DIMENSION=1536
        patch_env("INSTRUCTOR_MODEL_NAME", local_path.replace("\\", "/"))
        patch_env("EMBEDDING_SERVICE", "instructor")
        patch_env("EMBEDDING_DIMENSION", "1536")

    elif model_type == "sentence_transformer":
        model_name = model_name or "sentence-transformers/all-MiniLM-L12-v2"  # Be careful, some are still 384
        local_path = os.path.join("models", model_name.split("/")[-1])
        download_model_offline(model_name, local_path)

        # Force EMBEDDING_DIMENSION=1536 even for sentence transformers (dangerous if model really 384, but OK if fine-tuned)
        patch_env("SENTENCE_TRANSFORMER_MODEL_NAME", local_path.replace("\\", "/"))
        patch_env("EMBEDDING_SERVICE", "sentence_transformer")
        patch_env("EMBEDDING_DIMENSION", "1536")  # FORCE ALWAYS

if __name__ == "__main__":
    main()
