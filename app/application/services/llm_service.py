# app/core/services/llm_service.py
from typing import Dict, Any, List, Optional, Union, AsyncIterable
from app.modules.llm.factory import LLMFactory
from domain.interfaces.llm import LLMInterface
from app.config import settings
from app.utils.logger_util import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    Service for interfacing with LLM models.
    Provides high-level text generation functionality for use in the application.
    """

    def __init__(self, llm_interface):
        self._llm_instances = {}  # Cache of loaded LLM instances

    async def generate_text(
            self,
            prompt: str,
            model_name: Optional[str] = None,
            max_tokens: int = 1024,
            temperature: float = 0.7,
            top_p: float = 0.9,
            stop_sequences: Optional[List[str]] = None,
            streaming: bool = False,
            user_id: Optional[str] = None,
            **kwargs
    ) -> Union[Dict[str, Any], AsyncIterable[Dict[str, Any]]]:
        """
        Generate text using the specified model (or default model if not specified).

        Parameters
        ----------
        prompt : str
            The prompt to generate text from
        model_name : Optional[str]
            Name of the model to use. If None, uses the default model from settings
        max_tokens : int
            Maximum number of tokens to generate
        temperature : float
            Sampling temperature (higher = more random)
        top_p : float
            Nucleus sampling probability
        stop_sequences : Optional[List[str]]
            Sequences that will stop generation when encountered
        streaming : bool
            Whether to stream the response tokens
        user_id : Optional[str]
            User ID for attribution/billing (if applicable)
        **kwargs
            Additional model-specific parameters

        Returns
        -------
        Union[Dict[str, Any], AsyncIterable[Dict[str, Any]]]
            Generated text and metadata, or an async iterator if streaming is True
        """
        # Use default model if not specified
        model_name = model_name or settings.LLM_DEFAULT_MODEL

        # Get or create the LLM instance
        llm = await self._get_llm_instance(model_name)

        # Log the generation request
        logger.info(f"Generating text with model '{model_name}' (user: {user_id})")

        # Generate text
        if streaming:
            return self._generate_streaming(llm, prompt, max_tokens, temperature, top_p, stop_sequences, **kwargs)
        else:
            return await llm.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop_sequences,
                **kwargs
            )

    async def _generate_streaming(
            self,
            llm: LLMInterface,
            prompt: str,
            max_tokens: int,
            temperature: float,
            top_p: float,
            stop_sequences: Optional[List[str]] = None,
            **kwargs
    ):
        """
        Generate streaming response if the model supports it.
        Falls back to non-streaming if not supported.

        Returns an async generator that yields partial responses.
        """
        # Check if the model supports streaming
        if hasattr(llm, "generate_streaming"):
            # Use native streaming
            async for chunk in llm.generate_streaming(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stop_sequences=stop_sequences,
                    **kwargs
            ):
                yield chunk
        else:
            # Fall back to non-streaming for models that don't support it
            logger.warning(
                f"Streaming requested but model {llm.model_name} doesn't support it. Falling back to non-streaming.")
            result = await llm.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop_sequences,
                **kwargs
            )
            yield result

    async def _get_llm_instance(self, model_name: str) -> LLMInterface:
        """
        Get or create an LLM instance for the specified model.
        Caches instances for reuse.

        Parameters
        ----------
        model_name : str
            Name of the model to get

        Returns
        -------
        LLMInterface
            The LLM interface for the requested model
        """
        if model_name not in self._llm_instances:
            # Create a new instance
            self._llm_instances[model_name] = LLMFactory.get_llm(model_name)

        return self._llm_instances[model_name]

    async def estimate_tokens(self, text: str, model_name: Optional[str] = None) -> int:
        """
        Estimate the number of tokens in the provided text.

        Parameters
        ----------
        text : str
            The text to estimate tokens for
        model_name : Optional[str]
            Name of the model to use for estimation. If None, uses the default model

        Returns
        -------
        int
            Estimated number of tokens
        """
        model_name = model_name or settings.LLM_DEFAULT_MODEL
        llm = await self._get_llm_instance(model_name)
        return llm.estimate_tokens(text)

    async def summarize_text(
            self,
            text: str,
            max_length: int = 200,
            model_name: Optional[str] = None
    ) -> str:
        """
        Summarize the provided text using the specified model.

        Parameters
        ----------
        text : str
            The text to summarize
        max_length : int
            Target maximum length for the summary
        model_name : Optional[str]
            Name of the model to use. If None, uses the default model

        Returns
        -------
        str
            Summarized text
        """
        prompt = f"""Please summarize the following text in a concise way, keeping the most important information.
The summary should be no more than {max_length} words.

TEXT TO SUMMARIZE:
{text}

SUMMARY:"""

        result = await self.generate_text(
            prompt=prompt,
            model_name=model_name,
            max_tokens=512,
            temperature=0.3  # Lower temperature for more focused summaries
        )

        return result.get("text", "").strip()

    async def extract_key_points(
            self,
            text: str,
            num_points: int = 5,
            model_name: Optional[str] = None
    ) -> List[str]:
        """
        Extract key points from the provided text.

        Parameters
        ----------
        text : str
            The text to extract key points from
        num_points : int
            Number of key points to extract
        model_name : Optional[str]
            Name of the model to use. If None, uses the default model

        Returns
        -------
        List[str]
            List of extracted key points
        """
        prompt = f"""Please extract the {num_points} most important key points from the text below.
Format each point as a single sentence.

TEXT:
{text}

KEY POINTS:"""

        result = await self.generate_text(
            prompt=prompt,
            model_name=model_name,
            max_tokens=512,
            temperature=0.3
        )

        # Parse the result to extract key points
        response_text = result.get("text", "").strip()
        lines = response_text.split('\n')

        # Filter out empty lines and lines without content
        key_points = [line.strip() for line in lines if line.strip()]

        # Try to extract numbered points if present
        cleaned_points = []
        for point in key_points:
            # Remove numbering if present (like "1.", "2.", etc.)
            if point and point[0].isdigit() and len(point) > 2 and point[1:3] in ['. ', '- ', ') ']:
                point = point[3:].strip()
            cleaned_points.append(point)

        return cleaned_points[:num_points]  # Limit to requested number of points

    def clear_cache(self):
        """Clear the cached LLM instances to free memory."""
        self._llm_instances.clear()




