
from backend.app.retrieval.hybrid_search import HybridSearcher


def make_doc(doc_id: int, source_pmid: str, rank: int, method: str, score: float = 1.0):
    return {
        "id": doc_id,
        "source_pmid": source_pmid,
        "text": f"Abstract content for {source_pmid}",
        "score": score,
        "rank": rank,
        "method": method,
    }


class TestReciprocalRankFusion:
    def setup_method(self):
        self.searcher = HybridSearcher()

    def test_empty_inputs(self):
        result = self.searcher.reciprocal_rank_fusion([], [], k_final=10)
        assert result == []

    def test_only_dense_results(self):
        dense = [make_doc(1, "pmid_1", rank=1, method="dense")]
        result = self.searcher.reciprocal_rank_fusion(dense, [], k_final=10)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_only_keyword_results(self):
        keyword = [make_doc(2, "pmid_2", rank=1, method="keyword")]
        result = self.searcher.reciprocal_rank_fusion([], keyword, k_final=10)
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_same_doc_in_both_lists(self):
        doc = make_doc(1, "pmid_1", rank=1, method="dense")
        result = self.searcher.reciprocal_rank_fusion([doc], [doc], k_final=10)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_rrf_score_increases_for_overlapping_docs(self):
        dense = [make_doc(1, "pmid_1", rank=1, method="dense")]
        keyword = [make_doc(1, "pmid_1", rank=2, method="keyword")]
        result = self.searcher.reciprocal_rank_fusion(dense, keyword, k_final=10)
        expected = round(1.0 / (60 + 1) + 1.0 / (60 + 2), 6)
        assert result[0]["rrf_score"] == expected

    def test_respects_k_limit(self):
        dense = [make_doc(i, f"pmid_{i}", rank=i, method="dense") for i in range(1, 11)]
        keyword = [make_doc(i, f"pmid_{i}", rank=i, method="keyword") for i in range(1, 11)]
        result = self.searcher.reciprocal_rank_fusion(dense, keyword, k_final=3)
        assert len(result) == 3

    def test_ordering_by_rrf_score(self):
        dense = [
            make_doc(1, "pmid_1", rank=1, method="dense"),
        ]
        keyword = [
            make_doc(2, "pmid_2", rank=1, method="keyword"),
        ]
        result = self.searcher.reciprocal_rank_fusion(dense, keyword, k_final=10)
        assert len(result) == 2
        assert result[0]["rrf_score"] >= result[1]["rrf_score"]

    def test_non_overlapping_docs_merged(self):
        dense = [make_doc(1, "pmid_A", rank=1, method="dense")]
        keyword = [make_doc(2, "pmid_B", rank=1, method="keyword")]
        result = self.searcher.reciprocal_rank_fusion(dense, keyword, k_final=10)
        ids = {r["id"] for r in result}
        assert ids == {1, 2}

    def test_rrf_metadata_present(self):
        dense = [make_doc(1, "pmid_X", rank=1, method="dense")]
        result = self.searcher.reciprocal_rank_fusion(dense, [], k_final=10)
        r = result[0]
        assert "rrf_score" in r
        assert "dense_rank" in r
        assert "keyword_rank" in r
        assert r["dense_rank"] == 1
        assert r["keyword_rank"] is None
