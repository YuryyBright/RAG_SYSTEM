# app/adapters/llm/local.py
from typing import Dict, Any, List, Optional
import os
import torch
from app.core.interfaces.llm import LLMInterface
from app.config import settings
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class LocalLLM(LLMInterface):
    """
    Adapter for working with locally downloaded LLM models.
    Supports both HuggingFace Transformers and GGUF models.
    """

    def __init__(self, model_name: str, model_path: Optional[str] = None):
        """
        Initialize the Local LLM adapter.

        Parameters
        ----------
        model_name : str
            Name of the model to use
        model_path : Optional[str]
            Path to the model. If None, will use default path from settings
        """
        self.model_name = model_name
        self.models_dir = os.path.join(settings.MODELS_BASE_DIR, "llm")

        # If model_path not provided, try different extensions
        if model_path is None:
            # Check for GGUF file
            gguf_path = os.path.join(self.models_dir, f"{model_name}.gguf")
            if os.path.exists(gguf_path):
                self.model_path = gguf_path
                self.model_type = "gguf"
            else:
                # Check for directory (HuggingFace style)
                hf_path = os.path.join(self.models_dir, model_name)
                if os.path.exists(hf_path) and os.path.isdir(hf_path):
                    self.model_path = hf_path
                    self.model_type = "huggingface"
                else:
                    # Try without extension as fallback
                    self.model_path = os.path.join(self.models_dir, model_name)
                    self.model_type = "huggingface"
        else:
            self.model_path = model_path
            self.model_type = "gguf" if model_path.endswith(".gguf") else "huggingface"

        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the model based on its type."""
        try:
            logger.info(f"Loading local model from {self.model_path}")
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model path does not exist: {self.model_path}")

            if self.model_type == "gguf":
                self._load_gguf_model()
            else:
                self._load_huggingface_model()

            logger.info(f"Successfully loaded model {self.model_name}")

        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {str(e)}")
            raise RuntimeError(f"Failed to load local model: {str(e)}")

    def _load_gguf_model(self) -> None:
        """Load a GGUF model using llama-cpp-python."""
        try:
            # Import here to avoid dependency if not needed
            from llama_cpp import Llama

            # Load the GGUF model
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=2048,  # Context window size
                n_threads=os.cpu_count(),  # Use available CPU threads
                n_gpu_layers=-1  # Use GPU if available
            )
            logger.info(f"Loaded GGUF model: {self.model_path}")

        except ImportError:
            logger.error("llama-cpp-python package not installed. Required for GGUF models.")
            raise ImportError("Please install llama-cpp-python: pip install llama-cpp-python")

    def _load_huggingface_model(self) -> None:
        """Load a model using HuggingFace Transformers."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            # Check if CUDA is available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")

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
        """
        Generate text using the local model.

        Parameters
        ----------
        prompt : str
            The prompt to generate from
        max_tokens : int
            Maximum number of tokens to generate
        temperature : float
            Sampling temperature (higher = more random)
        top_p : float
            Nucleus sampling probability
        stop_sequences : Optional[List[str]]
            Sequences that will stop generation when encountered

        Returns
        -------
        Dict[str, Any]
            Generated text and metadata
        """
        if self.model_type == "gguf":
            return await self._generate_with_gguf(
                prompt, max_tokens, temperature, top_p, stop_sequences, **kwargs
            )
        else:
            return await self._generate_with_huggingface(
                prompt, max_tokens, temperature, top_p, stop_sequences, **kwargs
            )

    async def _generate_with_gguf(
            self,
            prompt: str,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """Generate text using llama-cpp (GGUF) model."""
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

            # Estimate token counts (llama-cpp doesn't easily expose this)
            prompt_tokens = len(prompt) // 4  # Rough estimate
            completion_tokens = len(generated_text) // 4  # Rough estimate

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

    async def _generate_with_huggingface(
            self,
            prompt: str,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """Generate text using HuggingFace model."""
        if self.pipeline is None:
            raise RuntimeError("HuggingFace model not loaded properly")

        try:
            # Prepare generation parameters
            gen_kwargs = {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": temperature > 0,
                "pad_token_id": self.pipeline.tokenizer.eos_token_id,
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

            return {
                "text": generated_text,
                "model": self.model_name,
                "usage": {
                    "prompt_tokens": len(self.pipeline.tokenizer.encode(prompt)),
                    "completion_tokens": len(self.pipeline.tokenizer.encode(generated_text)),
                    "total_tokens": len(self.pipeline.tokenizer.encode(prompt + generated_text))
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