# scripts/setup_embedding_model.py

import os
import argparse
from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv()

def patch_env(key: str, value: str, env_path: str = ".env"):
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
    print(f"✅ .env updated: {key}={value}")

def download_instructor_offline(model_name: str, local_dir: str):
    if os.path.exists(local_dir):
        print(f"✅ Model already exists at: {local_dir}")
        return

    print(f"⬇️ Downloading instructor model '{model_name}' to '{local_dir}' (no auth)...")
    snapshot_download(repo_id=model_name, local_dir=local_dir, local_dir_use_symlinks=False)
    print(f"✅ Model downloaded to: {local_dir}")

def main():
    parser = argparse.ArgumentParser(description="Download embedding models")
    parser.add_argument("--type", required=True, choices=["instructor", "sentence_transformer"], help="Model type")
    parser.add_argument("--model-name", required=False, help="Model name or path")
    args = parser.parse_args()

    model_type = args.type
    model_name = args.model_name

    if model_type == "instructor":
        model_name = model_name or "hkunlp/instructor-large"
        local_path = os.path.join("models", model_name.split("/")[-1])
        download_instructor_offline(model_name, local_path)
        patch_env("INSTRUCTOR_MODEL_NAME", local_path)
        patch_env("EMBEDDING_SERVICE", "instructor")

    elif model_type == "sentence_transformer":
        from sentence_transformers import SentenceTransformer
        model_name = model_name or "all-MiniLM-L6-v2"
        SentenceTransformer(model_name)
        patch_env("SENTENCE_TRANSFORMER_MODEL_NAME", model_name)
        patch_env("EMBEDDING_SERVICE", "sentence_transformer")

if __name__ == "__main__":
    main()
