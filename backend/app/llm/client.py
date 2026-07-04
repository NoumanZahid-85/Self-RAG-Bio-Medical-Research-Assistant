"""
Phase 2: LLM Client
Provider abstraction over Groq — swap models/providers here without touching graph.py.
"""
import logging
import os
from typing import TypeVar

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GradeResult(BaseModel):
    score: bool = Field(description="True if relevant/grounded/useful, False otherwise")
    reasoning: str = Field(description="Brief explanation for the score")


class LLMConfig:
    grader_model: str = "llama-3.1-8b-instant"
    generator_model: str = "llama-3.3-70b-versatile"
    temperature_grade: float = 0.0
    temperature_generate: float = 0.3
    max_tokens_grade: int = 1024
    max_tokens_generate: int = 2048


class LLMClient:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment or .env")

        self._grader = ChatGroq(
            model=self.config.grader_model,
            temperature=self.config.temperature_grade,
            max_tokens=self.config.max_tokens_grade,
            api_key=api_key,
        )
        self._generator = ChatGroq(
            model=self.config.generator_model,
            temperature=self.config.temperature_generate,
            max_tokens=self.config.max_tokens_generate,
            api_key=api_key,
        )

    def grade(self, system_prompt: str, user_prompt: str, model: type[T] = GradeResult) -> T:
        """Grade a document/answer with structured output.

        Args:
            system_prompt: System-level instruction.
            user_prompt: User-level context/question.
            model: Pydantic model class for structured output (default: GradeResult).
        Returns:
            An instance of `model` with parsed fields.
        """
        structured_llm = self._grader.with_structured_output(model)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        result: T = structured_llm.invoke(messages)
        if hasattr(result, 'reasoning'):
            logger.debug("Grade: %s (reasoning: %s)", getattr(result, 'score', 'N/A'), result.reasoning[:80])
        return result

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate an answer from the larger model."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = self._generator.invoke(messages)
        text = response.content.strip()
        logger.debug("Generation length: %d chars", len(text))
        return text

    def generate_raw(self, system_prompt: str, user_prompt: str) -> str:
        """Text-only generation from the grader model (cheaper, used for evaluation scoring)."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = self._grader.invoke(messages)
        text = response.content.strip()
        logger.debug("Raw gen length: %d chars", len(text))
        return text
