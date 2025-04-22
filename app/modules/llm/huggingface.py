# app/modules/llm/huggingface.py
import os
import torch
from typing import Dict, Any, List, Optional

from app.modules.llm.base import BaseLLM
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class HuggingFaceLLM(BaseLLM):
    """
    Handler for HuggingFace Transformers models.
    """

    def _load_model(self) -> None:
        """Load a model using HuggingFace Transformers."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            # Check if model directory exists
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model directory not found: {self.model_path}")

            # Check if CUDA is available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device} for model: {self.model_name}")

            # Load model with optimizations for inference
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map=device,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
                local_files_only=True
            )

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                local_files_only=True
            )

            # Create generation pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if device == "cuda" else -1
            )

            logger.info(f"Successfully loaded HuggingFace model: {self.model_name}")
        except ImportError:
            logger.error("transformers package not installed. Required for HuggingFace models.")
            raise ImportError("Please install transformers: pip install transformers torch")
        except Exception as e:
            logger.error(f"Failed to load HuggingFace model: {str(e)}")
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
        """Generate text using the HuggingFace model."""
        try:
            if self.pipeline is None:
                raise RuntimeError("HuggingFace pipeline not properly initialized")

            # Prepare generation parameters
            gen_kwargs = {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": temperature > 0,
                "pad_token_id": self.tokenizer.eos_token_id,
                "num_return_sequences": 1,
            }

            # Add stop sequences if provided
            if stop_sequences:
                gen_kwargs["stopping_criteria"] = self._create_stopping_criteria(stop_sequences, prompt)

            # Generate text
            outputs = self.pipeline(
                prompt,
                **gen_kwargs
            )

            # Extract generated text (removing the input prompt)
            generated_text = outputs[0]["generated_text"]
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):]

            # Get token counts
            prompt_tokens = len(self.tokenizer.encode(prompt))
            completion_tokens = len(self.tokenizer.encode(generated_text))

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
            logger.error(f"Error generating text with HuggingFace model {self.model_name}: {str(e)}")
            return {"text": f"Error: {str(e)}", "error": str(e)}

    def _create_stopping_criteria(self, stop_sequences: List[str], prompt: str):
        """Create stopping criteria for the generation based on stop sequences."""
        from transformers.generation.stopping_criteria import StoppingCriteriaList, StoppingCriteria

        class StopSequenceCriteria(StoppingCriteria):
            def __init__(self, tokenizer, stop_sequences, prompt_length):
                self.tokenizer = tokenizer
                self.stop_sequences = stop_sequences
                self.prompt_length = prompt_length

            def __call__(self, input_ids, scores, **kwargs):
                generated = self.tokenizer.decode(input_ids[0][self.prompt_length:])
                for stop_seq in self.stop_sequences:
                    if stop_seq in generated:
                        return True
                return False

        prompt_token_count = len(self.tokenizer.encode(prompt))
        return StoppingCriteriaList([
            StopSequenceCriteria(self.tokenizer, stop_sequences, prompt_token_count)
        ])

    def estimate_tokens(self, text: str) -> int:
        """Get the exact token count for HuggingFace models."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return super().estimate_tokens(text)