# app/cli/llm_manager.py
import asyncio
import argparse
import sys
import os
import json
from tabulate import tabulate
from termcolor import colored
import yaml

from app.modules.llm.factory import LLMFactory
from app.modules.llm.gguf import GGUFLLM
from app.modules.llm.huggingface import HuggingFaceLLM
from app.modules.llm.onnx import ONNXLLM
from app.application.services.llm_service import LLMService
from app.config import settings
from app.utils.logger_util import get_logger

logger = get_logger(__name__)

# Register model handlers
# LLMFactory.register_handler("gguf", GGUFLLM)
# LLMFactory.register_handler("hf", HuggingFaceLLM)
# LLMFactory.register_handler("onnx", ONNXLLM)


class LLMManager:
    """CLI tool for managing LLM models in the application."""

    def __init__(self):
        self.llm_service = LLMService()

    async def list_models(self, format_output: str = "table") -> None:
        """
        List all available models.

        Parameters
        ----------
        format_output : str
            Output format: 'table', 'json', or 'yaml'
        """
        models = LLMFactory.list_available_models()

        if not models:
            print(colored("No models found in the system.", "yellow"))
            return

        # Format model size
        for model in models:
            if "size" in model and isinstance(model["size"], int):
                model["size_human"] = self._format_size(model["size"])

        # Output according to format
        if format_output == "json":
            print(json.dumps({"models": models}, indent=2))
        elif format_output == "yaml":
            print(yaml.dump({"models": models}))
        else:  # Default to table
            table_data = []
            for model in models:
                row = [
                    colored(model.get("name", "Unknown"), "cyan"),
                    model.get("type", "Unknown"),
                    model.get("size_human", "Unknown"),
                    "✓" if model.get("loaded", False) else "✗"
                ]
                table_data.append(row)

            headers = [
                colored("Name", "green"),
                colored("Type", "green"),
                colored("Size", "green"),
                colored("Loaded", "green")
            ]

            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            print(f"\nTotal models: {len(models)}")

    async def test_model(
            self,
            model_name: str,
            prompt: str = "What are the key features of a Retrieval Augmented Generation system?",
            max_tokens: int = 512,
            temperature: float = 0.7,
            verbose: bool = False
    ) -> None:
        """
        Test a model with the specified prompt.

        Parameters
        ----------
        model_name : str
            Name of the model to test
        prompt : str
            Prompt to use for testing
        max_tokens : int
            Maximum tokens to generate
        temperature : float
            Temperature for generation
        verbose : bool
            Whether to show detailed information
        """
        print(colored(f"Testing model: {model_name}", "cyan"))
        print(colored("Prompt:", "green"))
        print(f"{prompt}\n")

        try:
            start_time = asyncio.get_event_loop().time()

            # Generate response
            response = await self.llm_service.generate_text(
                prompt=prompt,
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Calculate elapsed time
            elapsed_time = asyncio.get_event_loop().time() - start_time

            # Display results
            print(colored("Response:", "green"))
            print(f"{response.get('text', 'No text generated')}\n")

            if verbose or "usage" in response:
                print(colored("Stats:", "green"))
                if "usage" in response:
                    usage = response["usage"]
                    print(f"  Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
                    print(f"  Completion tokens: {usage.get('completion_tokens', 'N/A')}")
                    print(f"  Total tokens: {usage.get('total_tokens', 'N/A')}")
                print(f"  Time taken: {elapsed_time:.2f}s")
                if "usage" in response and "completion_tokens" in response["usage"]:
                    tokens_per_second = response["usage"]["completion_tokens"] / elapsed_time
                    print(f"  Generation speed: {tokens_per_second:.2f} tokens/sec")

        except Exception as e:
            print(colored(f"Error testing model: {str(e)}", "red"))
            if verbose:
                import traceback
                traceback.print_exc()

    async def benchmark_model(
            self,
            model_name: str,
            prompt: str = "Explain the concept of retrieval augmented generation in detail.",
            runs: int = 3,
            max_tokens: int = 256
    ) -> None:
        """
        Benchmark a model's performance.

        Parameters
        ----------
        model_name : str
            Name of the model to benchmark
        prompt : str
            Prompt to use for benchmarking
        runs : int
            Number of benchmark runs
        max_tokens : int
            Maximum tokens to generate
        """
        print(colored(f"Benchmarking model: {model_name}", "cyan"))
        print(f"Running {runs} iterations with {max_tokens} tokens each...\n")

        times = []
        token_speeds = []

        for i in range(runs):
            print(f"Run {i + 1}/{runs}...")
            start_time = asyncio.get_event_loop().time()

            try:
                response = await self.llm_service.generate_text(
                    prompt=prompt,
                    model_name=model_name,
                    max_tokens=max_tokens,
                    temperature=0.7
                )

                elapsed_time = asyncio.get_event_loop().time() - start_time
                times.append(elapsed_time)

                if "usage" in response and "completion_tokens" in response["usage"]:
                    tokens = response["usage"]["completion_tokens"]
                    token_speed = tokens / elapsed_time
                    token_speeds.append(token_speed)
                    print(f"  Generated {tokens} tokens in {elapsed_time:.2f}s ({token_speed:.2f} tokens/sec)")
                else:
                    print(f"  Completed in {elapsed_time:.2f}s")

            except Exception as e:
                print(colored(f"  Error in run {i + 1}: {str(e)}", "red"))

        # Report benchmark results
        if times:
            avg_time = sum(times) / len(times)
            print(colored("\nBenchmark Results:", "green"))
            print(f"  Average completion time: {avg_time:.2f}s")

            if token_speeds:
                avg_speed = sum(token_speeds) / len(token_speeds)
                print(f"  Average generation speed: {avg_speed:.2f} tokens/sec")

            if len(times) > 1:
                print(f"  Time variance: {max(times) - min(times):.2f}s")
        else:
            print(colored("\nNo successful benchmark runs completed.", "yellow"))

    async def model_info(self, model_name: str) -> None:
        """
        Display detailed information about a model.

        Parameters
        ----------
        model_name : str
            Name of the model to get info for
        """
        models = LLMFactory.list_available_models()
        model_info = None

        for model in models:
            if model.get("name") == model_name:
                model_info = model
                break

        if not model_info:
            print(colored(f"Model '{model_name}' not found.", "red"))
            return

        print(colored(f"Model Information: {model_name}", "cyan"))
        print("-" * 50)

        # Format size
        if "size" in model_info and isinstance(model_info["size"], int):
            model_info["size_human"] = self._format_size(model_info["size"])

        # Display model information
        for key, value in model_info.items():
            if key not in ["size_human"] and key != "size" and "size_human" in model_info:
                if key == "file_path":
                    print(f"{key.title()}: {os.path.abspath(value)}")
                else:
                    print(f"{key.title()}: {value}")
            elif key == "size" and "size_human" not in model_info:
                print(f"{key.title()}: {value}")

        # Try to get additional model metadata if available
        try:
            # This is a placeholder - you'd implement model-specific metadata extraction
            # For example, for HuggingFace models you might try to load and extract config
            print("\nAdditional Information:")
            print("  No additional metadata available")
        except Exception as e:
            if isinstance(e, ImportError):
                print("\nAdditional Information:")
                print("  Cannot extract additional metadata (missing dependencies)")
            else:
                print("\nAdditional Information:")
                print(f"  Failed to extract additional metadata: {str(e)}")

    async def set_default_model(self, model_name: str) -> None:
        """
        Set the default model for the application.

        Parameters
        ----------
        model_name : str
            Name of the model to set as default
        """
        # Check if model exists
        models = LLMFactory.list_available_models()
        model_exists = any(model.get("name") == model_name for model in models)

        if not model_exists:
            print(colored(f"Model '{model_name}' not found.", "red"))
            return

        # Here you would normally update your settings
        # This is a simplified example - in a real app you'd persist this
        settings.LLM_DEFAULT_MODEL = model_name

        print(colored(f"Default model set to: {model_name}", "green"))
        print("Note: This setting will be reset when the application restarts.")
        print("To make this permanent, update your config file or environment variables.")

    async def interactive_test(self, model_name: str) -> None:
        """
        Start an interactive testing session with a model.

        Parameters
        ----------
        model_name : str
            Name of the model to test interactively
        """
        print(colored(f"Interactive testing session with model: {model_name}", "cyan"))
        print("Type your prompts and press Enter. Type 'exit', 'quit', or Ctrl+C to end the session.\n")

        history = []

        while True:
            try:
                # Get user input
                user_input = input(colored("You: ", "green"))

                # Check for exit command
                if user_input.lower() in ["exit", "quit"]:
                    break

                # Skip empty inputs
                if not user_input.strip():
                    continue

                # Add to history
                history.append({"role": "user", "content": user_input})

                # Format prompt with history if needed
                if len(history) > 1:
                    # Create a conversational prompt with history
                    prompt = "\n".join([
                        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                        for msg in history
                    ])
                else:
                    prompt = user_input

                # Generate response
                start_time = asyncio.get_event_loop().time()
                response = await self.llm_service.generate_text(
                    prompt=prompt,
                    model_name=model_name,
                    max_tokens=1024,
                    temperature=0.7
                )
                elapsed_time = asyncio.get_event_loop().time() - start_time

                # Get response text
                response_text = response.get("text", "").strip()

                # Add to history
                history.append({"role": "assistant", "content": response_text})

                # Print response
                print(colored("Assistant: ", "blue") + response_text)

                # Print stats
                if "usage" in response:
                    tokens = response["usage"].get("completion_tokens", 0)
                    speed = tokens / elapsed_time if elapsed_time > 0 else 0
                    print(colored(f"[{tokens} tokens, {elapsed_time:.2f}s, {speed:.2f} t/s]", "grey"))
                else:
                    print(colored(f"[{elapsed_time:.2f}s]", "grey"))
                print()

            except KeyboardInterrupt:
                print("\nExiting interactive session...")
                break
            except Exception as e:
                print(colored(f"Error: {str(e)}", "red"))

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes into a human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024 or unit == 'TB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024


async def main():
    """Main CLI entry point for LLM management."""
    parser = argparse.ArgumentParser(description="LLM Model Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List models command
    list_parser = subparsers.add_parser("list", help="List available models")
    list_parser.add_argument("--format", choices=["table", "json", "yaml"], default="table",
                             help="Output format")

    # Model info command
    info_parser = subparsers.add_parser("info", help="Show detailed info about a model")
    info_parser.add_argument("model_name", help="Name of the model")

    # Test model command
    test_parser = subparsers.add_parser("test", help="Test a model with a prompt")
    test_parser.add_argument("model_name", help="Name of the model to test")
    test_parser.add_argument("--prompt", default="What are the key features of a RAG system?",
                             help="Prompt to use for testing")
    test_parser.add_argument("--max-tokens", type=int, default=512,
                             help="Maximum tokens to generate")
    test_parser.add_argument("--temperature", type=float, default=0.7,
                             help="Temperature for generation")
    test_parser.add_argument("--verbose", action="store_true",
                             help="Show detailed output")

    # Benchmark model command
    benchmark_parser = subparsers.add_parser("benchmark", help="Benchmark model performance")
    benchmark_parser.add_argument("model_name", help="Name of the model to benchmark")
    benchmark_parser.add_argument("--prompt",
                                  default="Explain the concept of retrieval augmented generation in detail.",
                                  help="Prompt to use for benchmarking")
    benchmark_parser.add_argument("--runs", type=int, default=3,
                                  help="Number of benchmark runs")
    benchmark_parser.add_argument("--max-tokens", type=int, default=256,
                                  help="Maximum tokens to generate per run")

    # Set default model command
    default_parser = subparsers.add_parser("set-default", help="Set the default model")
    default_parser.add_argument("model_name", help="Name of the model to set as default")

    # Interactive test command
    interactive_parser = subparsers.add_parser("interactive", help="Start interactive testing session")
    interactive_parser.add_argument("model_name", help="Name of the model to test")

    args = parser.parse_args()

    # Create manager instance
    manager = LLMManager()

    # Run the appropriate command
    if args.command == "list":
        await manager.list_models(args.format)
    elif args.command == "info":
        await manager.model_info(args.model_name)
    elif args.command == "test":
        await manager.test_model(
            args.model_name,
            args.prompt,
            args.max_tokens,
            args.temperature,
            args.verbose
        )
    elif args.command == "benchmark":
        await manager.benchmark_model(
            args.model_name,
            args.prompt,
            args.runs,
            args.max_tokens
        )
    elif args.command == "set-default":
        await manager.set_default_model(args.model_name)
    elif args.command == "interactive":
        await manager.interactive_test(args.model_name)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())