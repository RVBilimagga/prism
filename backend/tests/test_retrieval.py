from finreq.retrieval import KnowledgeBase


def test_loads_all_sample_kb_documents():
    kb = KnowledgeBase()
    assert not kb.is_empty()
    assert len(kb.documents) >= 5
    for doc in kb.documents:
        assert doc.jurisdiction != "unknown"
        assert doc.effective_date != "unknown"


def test_retrieve_ranks_relevant_document_first():
    kb = KnowledgeBase()
    evidence = kb.retrieve("step-up authentication for large transactions", top_k=3)
    assert evidence
    assert evidence[0].source_id == "transaction_security_policy"
    # results are sorted by descending similarity
    sims = [e.similarity for e in evidence]
    assert sims == sorted(sims, reverse=True)


def test_retrieve_returns_no_evidence_for_unrelated_query():
    kb = KnowledgeBase()
    evidence = kb.retrieve("recipe for chocolate cake", top_k=3)
    # Either empty, or only very weak matches — none should score high.
    assert all(e.similarity < 0.3 for e in evidence)


def test_empty_directory_is_handled_gracefully(tmp_path):
    kb = KnowledgeBase(directory=str(tmp_path))
    assert kb.is_empty()
    assert kb.retrieve("anything") == []
