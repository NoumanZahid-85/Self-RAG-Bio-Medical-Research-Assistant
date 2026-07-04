import os
from unittest.mock import patch

import pytest
from backend.app.llm.client import GradeResult, LLMClient, LLMConfig


class TestLLMConfig:
    def test_default_grader_model(self):
        config = LLMConfig()
        assert config.grader_model == "llama-3.1-8b-instant"

    def test_default_generator_model(self):
        config = LLMConfig()
        assert config.generator_model == "llama-3.3-70b-versatile"

    def test_default_temperatures(self):
        config = LLMConfig()
        assert config.temperature_grade == 0.0
        assert config.temperature_generate == 0.3

    def test_default_max_tokens(self):
        config = LLMConfig()
        assert config.max_tokens_grade == 1024
        assert config.max_tokens_generate == 2048


class TestLLMClient:
    def test_init_raises_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GROQ_API_KEY not set"):
                LLMClient()

    def test_init_succeeds_with_api_key(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key-123"}):
            client = LLMClient()
            assert client.config.grader_model == "llama-3.1-8b-instant"
            assert client.config.generator_model == "llama-3.3-70b-versatile"


class TestGradeResult:
    def test_default_values(self):
        result = GradeResult(score=True, reasoning="Works")
        assert result.score is True
        assert result.reasoning == "Works"

    def test_false_score(self):
        result = GradeResult(score=False, reasoning="Not relevant")
        assert result.score is False
