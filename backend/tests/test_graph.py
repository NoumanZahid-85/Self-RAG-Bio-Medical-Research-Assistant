from unittest.mock import MagicMock, patch

from backend.app.llm.client import GradeResult
from backend.app.rag.graph import (
    SelfRAGState,
    abstain_node,
    build_graph,
    inc_generation_retry,
    inc_retrieval_retry,
    route_after_answer_grade,
    route_after_grade,
    route_after_hallucination,
    route_after_rewrite,
)


def make_state(**overrides) -> SelfRAGState:
    defaults: SelfRAGState = {
        "question": "Does aspirin reduce cardiovascular risk?",
        "documents": [],
        "graded_documents": [],
        "generation": "",
        "retrieval_retries": 0,
        "generation_retries": 0,
        "abstained": False,
        "graph_path": [],
        "hallucination_passed": False,
        "answer_useful": False,
    }
    defaults.update(overrides)
    return defaults


class TestRouteAfterGrade:
    def test_relevant_docs_goes_to_generate(self):
        state = make_state(graded_documents=[{"id": 1, "text": "relevant doc"}])
        assert route_after_grade(state) == "generate"

    def test_no_relevant_docs_goes_to_no_relevant(self):
        state = make_state(graded_documents=[])
        assert route_after_grade(state) == "no_relevant_docs"


class TestRouteAfterHallucination:
    def test_grounded_passes_through(self):
        state = make_state(hallucination_passed=True)
        assert route_after_hallucination(state) == "grounded"

    def test_not_grounded_with_retries_left_retries(self):
        state = make_state(hallucination_passed=False, generation_retries=0)
        assert route_after_hallucination(state) == "retry_generate"

    def test_not_grounded_max_retries_exhausted_abstains(self):
        state = make_state(hallucination_passed=False, generation_retries=2)
        assert route_after_hallucination(state) == "abstain"

    def test_not_grounded_at_retry_boundary(self):
        state = make_state(hallucination_passed=False, generation_retries=1)
        assert route_after_hallucination(state) == "retry_generate"


class TestRouteAfterAnswerGrade:
    def test_useful_ends(self):
        state = make_state(answer_useful=True)
        assert route_after_answer_grade(state) == "useful"

    def test_not_useful_with_retries_left_retries_retrieval(self):
        state = make_state(answer_useful=False, retrieval_retries=0)
        assert route_after_answer_grade(state) == "retry_retrieval"

    def test_not_useful_max_retries_exhausted_abstains(self):
        state = make_state(answer_useful=False, retrieval_retries=2)
        assert route_after_answer_grade(state) == "abstain"


class TestRouteAfterRewrite:
    def test_retries_left_retries_retrieve(self):
        state = make_state(retrieval_retries=0)
        assert route_after_rewrite(state) == "retry_retrieve"

    def test_max_retries_exhausted_abstains(self):
        state = make_state(retrieval_retries=2)
        assert route_after_rewrite(state) == "abstain"

    def test_at_boundary(self):
        state = make_state(retrieval_retries=1)
        assert route_after_rewrite(state) == "retry_retrieve"


class TestPureNodes:
    def test_abstain_node_sets_correct_values(self):
        state = make_state()
        result = abstain_node(state)
        assert result["abstained"] is True
        assert "Insufficient evidence" in result["generation"]
        assert result["hallucination_passed"] is False
        assert result["answer_useful"] is False

    def test_inc_retrieval_retry(self):
        state = make_state(retrieval_retries=0)
        result = inc_retrieval_retry(state)
        assert result["retrieval_retries"] == 1

    def test_inc_generation_retry(self):
        state = make_state(generation_retries=1)
        result = inc_generation_retry(state)
        assert result["generation_retries"] == 2


class TestBuildGraph:
    def test_build_graph_compiles(self):
        mock_llm = MagicMock()
        mock_llm.grade.return_value = GradeResult(score=True, reasoning="mock")
        mock_llm.generate.return_value = "Mock answer"
        graph = build_graph(mock_llm)
        assert graph is not None

    @patch("backend.app.rag.graph.hybrid_search")
    def test_graph_invoke_returns_expected_keys(self, mock_search):
        mock_search.return_value = [
            {"id": 1, "source_pmid": "123", "text": "Aspirin reduces risk."}
        ]
        mock_llm = MagicMock()
        mock_llm.grade.return_value = GradeResult(score=True, reasoning="mock")
        mock_llm.generate.return_value = (
            "Aspirin reduces cardiovascular risk [PMID:12345]."
        )
        graph = build_graph(mock_llm)
        result = graph.invoke(make_state())
        assert "question" in result
        assert "generation" in result
        assert "abstained" in result
        assert "graph_path" in result

    @patch("backend.app.rag.graph.hybrid_search")
    def test_graph_path_is_recorded(self, mock_search):
        mock_search.return_value = [
            {"id": 1, "source_pmid": "123", "text": "Aspirin reduces risk."}
        ]
        mock_llm = MagicMock()
        mock_llm.grade.return_value = GradeResult(score=True, reasoning="mock")
        mock_llm.generate.return_value = "Mock answer with citation [PMID:1]."
        graph = build_graph(mock_llm)
        result = graph.invoke(make_state())
        assert len(result["graph_path"]) >= 3
        assert "retrieve" in result["graph_path"]
        assert "grade_documents" in result["graph_path"]
