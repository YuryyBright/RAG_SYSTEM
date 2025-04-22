# app/modules/llm/__init__.py
from app.modules.llm.factory import LLMFactory
from app.modules.llm.gguf import GGUFLLM
from app.modules.llm.huggingface import HuggingFaceLLM
from app.modules.llm.onnx import ONNXLLM

# Register all the LLM handlers
LLMFactory.register_handler("gguf", GGUFLLM)
LLMFactory.register_handler("hf", HuggingFaceLLM)
LLMFactory.register_handler("bin", HuggingFaceLLM)  # .bin files are also typically HuggingFace format
LLMFactory.register_handler("safetensors", HuggingFaceLLM)  # .safetensors files are also HuggingFace format
LLMFactory.register_handler("onnx", ONNXLLM)

# Export the factory
__all__ = ["LLMFactory"]