# app/adapters/llm/base_llm_service.py
from core.interfaces.llm import LLMInterface

class BaseLLMService(LLMInterface):
    """
    Base class for LLM adapters; inherits default generate_text().
    All concrete adapters just need to implement `generate(...)`.
    """
    # No extra code needed here unless you have helper methods shared
    ...
