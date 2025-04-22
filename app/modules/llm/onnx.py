# app/modules/llm/onnx.py
import os
from typing import Dict, Any, List, Optional

from app.modules.llm.base import BaseLLM
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class ONNXLLM(BaseLLM):
    """
    Handler for ONNX format models.
    """

    def _load_model(self) -> None:
        """Load the ONNX model using onnxruntime."""
        try:
            import onnxruntime as ort
            import numpy as np
            from transformers import AutoTokenizer

            # Check if model file exists
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")

            # Use parent directory as model directory to find tokenizer
            model_dir = os.path.dirname(self.model_path)
            if os.path.isfile(model_dir):  # If model_path is a file
                model_dir = os.path.dirname(model_dir)

            # Create ONNX Runtime session
            self.session = ort.InferenceSession(
                self.model_path,
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )

            # Try to load tokenizer from the model directory
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            except Exception as e:
                logger.warning(f"Could not load tokenizer from {model_dir}: {str(e)}")
                # Try to load a default tokenizer
                self.tokenizer = AutoTokenizer.from_pretrained("gpt2")

            # Get model metadata
            self.input_names = [input_meta.name for input_meta in self.session.get_inputs()]
            self.output_names = [output_meta.name for output_meta in self.session.get_outputs()]

            logger.info(f"Loaded ONNX model: {self.model_path}")
            logger.info(f"Input names: {self.input_names}")
            logger.info(f"Output names: {self.output_names}")

        except ImportError:
            logger.error("onnxruntime package not installed. Required for ONNX models.")
            raise ImportError("Please install onnxruntime: pip install onnxruntime")
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {str(e)}")
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
        """Generate text using the ONNX model."""
        try:
            if self.session is None:
                raise RuntimeError("ONNX model not loaded properly")

            import numpy as np

            def generate_text(
                    input_ids,
                    attention_mask=None,
                    max_length=max_tokens,
                    temperature=temperature,
                    top_p=top_p
            ):
                # Simple greedy token generation for ONNX models
                for _ in range(max_length):
                    # Prepare input feed
                    feed = {"input_ids": input_ids}
                    if "attention_mask" in self.input_names and attention_mask is not None:
                        feed["attention_mask"] = attention_mask

                    # Run inference
                    outputs = self.session.run(self.output_names, feed)

                    # Get next token probabilities
                    next_token_logits = outputs[0][:, -1, :]

                    # Apply temperature
                    if temperature > 0:
                        next_token_logits = next_token_logits / temperature

                    # Apply top-p sampling
                    if top_p < 1.0:
                        sorted_logits, sorted_indices = torch.sort(torch.tensor(next_token_logits), descending=True)
                        cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
                        sorted_indices_to_remove = cumulative_probs > top_p
                        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                        sorted_indices_to_remove[..., 0] = 0
                        indices_to_remove = sorted_indices[sorted_indices_to_remove]
                        next_token_logits[0][indices_to_remove] = -float('Inf')

                    # Sample
                    probs = np.exp(next_token_logits) / np.sum(np.exp(next_token_logits))
                    next_token = np.random.choice(probs.shape[-1], p=probs.flatten())

                    # Add the token to input_ids
                    input_ids = np.append(input_ids, [[next_token]], axis=1)

                    # Update attention mask if needed
                    if attention_mask is not None:
                        attention_mask = np.append(attention_mask, [[1]], axis=1)

                    # Check for stop sequences
                    if stop_sequences:
                        generated_text = self.tokenizer.decode(input_ids[0])
                        for stop_seq in stop_sequences:
                            if stop_seq in generated_text:
                                return input_ids

                return input_ids

            # Tokenize prompt
            inputs = self.tokenizer(prompt, return_tensors="np")
            input_ids = inputs["input_ids"]
            attention_mask = inputs.get("attention_mask", None)

            # Generate text
            output_ids = generate_text(
                input_ids,
                attention_mask,
                max_length=max_tokens,
                temperature=temperature,
                top_p=top_p
            )

            # Decode output
            decoded_output = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

            # Remove prompt from output
            if decoded_output.startswith(prompt):
                generated_text = decoded_output[len(prompt):]
            else:
                generated_text = decoded_output

            # Get token counts
            prompt_tokens = len(input_ids[0])
            output_tokens = len(output_ids[0]) - prompt_tokens

            return {
                "text": generated_text,
                "model": self.model_name,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": prompt_tokens + output_tokens
                }
            }
        except Exception as e:
            logger.error(f"Error generating text with ONNX model {self.model_name}: {str(e)}")
            return {"text": f"Error: {str(e)}", "error": str(e)}

    def estimate_tokens(self, text: str) -> int:
        """Get the token count using the tokenizer."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return super().estimate_tokens(text)