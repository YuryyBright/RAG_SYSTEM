# app/modules/llm/gguf.py
import os
from typing import Dict, Any, List, Optional

from app.modules.llm.base import BaseLLM
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class GGUFLLM(BaseLLM):
    """
    Handler for GGUF format models using llama-cpp-python.
    """

    def _load_model(self) -> None:
        """Load the GGUF model using llama-cpp-python."""
        try:
            # Import here to avoid dependency if not needed
            from llama_cpp import Llama

            # Check if model file exists
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")

            # Determine number of CPU threads to use
            n_threads = os.cpu_count() or 4

            # Load the GGUF model
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=2048,  # Context window size
                n_threads=n_threads,  # Use available CPU threads
                n_gpu_layers=-1  # Use GPU if available
            )
            logger.info(f"Loaded GGUF model: {self.model_path}")

        except ImportError:
            logger.error("llama-cpp-python package not installed. Required for GGUF models.")
            raise ImportError("Please install llama-cpp-python: pip install llama-cpp-python")
        except Exception as e:
            logger.error(f"Failed to load GGUF model: {str(e)}")
            raise

    async def generate(
            self,
            prompt: str,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """Generate text using the GGUF model."""
        try:
            if self.model is None:
                raise RuntimeError("GGUF Model not loaded properly")

            # Prepare parameters
            params = {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p
            }

            # Add stop sequences if provided
            if stop_sequences:
                params["stop"] = stop_sequences

            # Generate completion
            result = self.model(prompt, **params)

            # Extract generated text
            generated_text = result["choices"][0]["text"] if isinstance(result, dict) and "choices" in result else \
                result.choices[0].text

            # Get token counts
            prompt_tokens = self.estimate_tokens(prompt)
            completion_tokens = self.estimate_tokens(generated_text)

            return {
                "text": generated_text,
                "model": self.model_name,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }
        except Exception as e:
            logger.error(f"Error generating text with GGUF model {self.model_name}: {str(e)}")
            return {"text": f"Error: {str(e)}", "error": str(e)}

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens for GGUF models."""
        if self.model and hasattr(self.model, "tokenize"):
            try:
                return len(self.model.tokenize(text.encode('utf-8')))
            except:
                pass

        # Fallback: rough estimate based on characters
        return len(text) // 4