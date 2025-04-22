# app/cli/llm_utils.py
import asyncio
import argparse
import sys
from typing import List, Dict, Any, Optional

from app.adapters.llm.factory import LLMFactory
from app.utils.logger_util import get_logger

logger = get_logger(__name__)



async def list_models(provider: str = "all") -> None:
    """
    List available models from the specified provider.

    Parameters
    ----------
    provider : str
        Provider to list models from ('mistral', 'huggingface', 'openai', 'anthropic', 'all')
    """
    print(f"Fetching available models from {provider}...")
    models = await LLMFactory.list_available_models(provider)

    if not models:
        print(f"No models found for provider: {provider}")
        return

    print(f"\nAvailable models from {provider} ({len(models)}):")
    print("-" * 50)

    for model in models:
        name = model.get("name", "Unknown")
        provider = model.get("provider", "Unknown")
        size = model.get("size", "Unknown size")
        tags = ", ".join(model.get("tags", []))

        print(f"- {name}")
        print(f"  Provider: {provider}")
        if size != "Unknown size":
            print(f"  Size: {size}")
        if tags:
            print(f"  Tags: {tags}")
        print()

    print("-" * 50)


async def list_local_models() -> None:
    """List all locally registered models."""
    print("Fetching locally registered models...")
    models = await LLMFactory.list_local_models()

    if not models:
        print("No locally registered models found")
        return

    print(f"\nLocally registered models ({len(models)}):")
    print("-" * 50)
    for model in models:
        name = model.get("name", "Unknown")
        provider = model.get("provider", "Unknown provider")
        status = model.get("status", "Unknown status")
        original_name = model.get("original_name", name)

        print(f"- {name}")
        print(f"  Provider: {provider}")
        print(f"  Status: {status}")
        if original_name != name:
            print(f"  Original name: {original_name}")
        print()
    print("-" * 50)


async def download_model(model_name: str, provider: str) -> None:
    """
    Download a model from a provider.

    Parameters
    ----------
    model_name : str
        Name of the model to download
    provider : str
        Provider of the model ('mistral', 'huggingface', 'openai', 'anthropic')
    """
    print(f"Downloading model '{model_name}' from {provider}...")
    result = await LLMFactory.download_model(model_name, provider)

    if result["status"] == "success":
        print(f"Successfully downloaded model: {model_name}")
        if "local_path" in result:
            print(f"Saved to: {result['local_path']}")
    else:
        print(f"Failed to download model: {result.get('message', 'Unknown error')}")


async def test_model(model_name: str, provider: Optional[str] = None, prompt: str = "Hello, how are you?") -> None:
    """
    Test a model by generating text with a simple prompt.

    Parameters
    ----------
    model_name : str
        Name of the model to test
    provider : Optional[str]
        Provider of the model. If None, will be inferred
    prompt : str
        Prompt to use for testing
    """
    print(f"Testing model '{model_name}'...")

    try:
        llm = LLMFactory.get_llm(model_name, provider)
        print(f"Using prompt: '{prompt}'")

        response = await llm.generate(prompt, max_tokens=100)

        print("\nResponse:")
        print("-" * 50)
        print(response.get("text", "No text generated"))
        print("-" * 50)

        # Print usage information if available
        if "usage" in response:
            usage = response["usage"]
            print("\nToken usage:")
            print(f"  Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
            print(f"  Completion tokens: {usage.get('completion_tokens', 'N/A')}")
            print(f"  Total tokens: {usage.get('total_tokens', 'N/A')}")

    except Exception as e:
        print(f"Error testing model: {str(e)}")


def main():
    """Main CLI entry point for LLM management."""
    parser = argparse.ArgumentParser(description="LLM Model Management")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List models command
    list_parser = subparsers.add_parser("list", help="List available models")
    list_parser.add_argument("--provider", default="all",
                             choices=["all", "mistral", "huggingface", "openai", "anthropic"],
                             help="Provider to list models from")

    # List local models command
    subparsers.add_parser("list-local", help="List locally registered models")

    # Download model command
    download_parser = subparsers.add_parser("download", help="Download a model")
    download_parser.add_argument("model_name", help="Name of the model to download")
    download_parser.add_argument("--provider", default="mistral",
                                 choices=["mistral", "huggingface", "openai", "anthropic"],
                                 help="Provider of the model")

    # Test model command
    test_parser = subparsers.add_parser("test", help="Test a model with a simple prompt")
    test_parser.add_argument("model_name", help="Name of the model to test")
    test_parser.add_argument("--provider", help="Provider of the model (optional)")
    test_parser.add_argument("--prompt", default="Hello, how are you?",
                             help="Prompt to use for testing")

    args = parser.parse_args()

    if args.command == "list":
        asyncio.run(list_models(args.provider))
    elif args.command == "list-local":
        asyncio.run(list_local_models())
    elif args.command == "download":
        asyncio.run(download_model(args.model_name, args.provider))
    elif args.command == "test":
        asyncio.run(test_model(args.model_name, args.provider, args.prompt))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()