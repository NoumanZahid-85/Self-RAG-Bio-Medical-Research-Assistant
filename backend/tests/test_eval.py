
from backend.app.eval.run_eval import (
    ANSWER_RELEVANCY_THRESHOLD,
    CONTEXT_PRECISION_THRESHOLD,
    CONTEXT_RECALL_THRESHOLD,
    FAITHFULNESS_THRESHOLD,
    FaithfulnessScore,
    RecallScore,
    RelevancyScore,
    compute_context_precision,
)


class TestThresholdConstants:
    def test_faithfulness_threshold(self):
        assert FAITHFULNESS_THRESHOLD == 0.85

    def test_answer_relevancy_threshold(self):
        assert ANSWER_RELEVANCY_THRESHOLD == 0.80

    def test_context_precision_threshold(self):
        assert CONTEXT_PRECISION_THRESHOLD == 0.50

    def test_context_recall_threshold(self):
        assert CONTEXT_RECALL_THRESHOLD == 0.50


class TestComputeContextPrecision:
    def test_all_graded_returns_one(self):
        graded = [{"id": 1}, {"id": 2}]
        retrieved = [{"id": 1}, {"id": 2}]
        assert compute_context_precision(graded, retrieved) == 1.0

    def test_half_graded_returns_half(self):
        graded = [{"id": 1}]
        retrieved = [{"id": 1}, {"id": 2}]
        assert compute_context_precision(graded, retrieved) == 0.5

    def test_no_retrieved_returns_zero(self):
        assert compute_context_precision([], []) == 0.0

    def test_no_graded_returns_zero(self):
        graded = []
        retrieved = [{"id": 1}, {"id": 2}]
        assert compute_context_precision(graded, retrieved) == 0.0

    def test_more_graded_than_retrieved_returns_one(self):
        graded = [{"id": 1}, {"id": 2}, {"id": 3}]
        retrieved = [{"id": 1}]
        assert compute_context_precision(graded, retrieved) == 3.0


class TestDefaultScoreValues:
    def test_empty_faithfulness_returns_zero(self):
        result = FaithfulnessScore(
            total_claims=0, supported_claims=0,
            reasoning="Empty answer or context",
        )
        assert result.total_claims == 0
        assert result.supported_claims == 0

    def test_empty_answer_relevancy_returns_zero(self):
        result = RelevancyScore(score=0.0, reasoning="Empty answer")
        assert result.score == 0.0

    def test_empty_context_recall_returns_zero(self):
        result = RecallScore(score=0.0, reasoning="Empty ground truth or context")
        assert result.score == 0.0
