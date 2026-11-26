import pytest

from finreq.llm import FakeLLMClient, LLMError, unwrap_single


def test_unwrap_single_unwraps_one_item_list_of_dict():
    assert unwrap_single([{"a": 1}]) == {"a": 1}


def test_unwrap_single_leaves_dict_and_multi_item_list_alone():
    assert unwrap_single({"a": 1}) == {"a": 1}
    assert unwrap_single([{"a": 1}, {"b": 2}]) == [{"a": 1}, {"b": 2}]
    assert unwrap_single([]) == []


def test_generate_json_parses_clean_json():
    llm = FakeLLMClient(responses=[{"a": 1}])
    assert llm.generate_json("sys", "prompt") == {"a": 1}


def test_generate_json_strips_markdown_fence():
    llm = FakeLLMClient(responses=["```json\n{\"a\": 1}\n```"])
    assert llm.generate_json("sys", "prompt") == {"a": 1}


def test_generate_json_extracts_object_from_surrounding_prose():
    llm = FakeLLMClient(responses=["Sure, here you go: {\"a\": 1} hope that helps"])
    assert llm.generate_json("sys", "prompt") == {"a": 1}


def test_generate_json_retries_on_invalid_json_then_succeeds():
    llm = FakeLLMClient(responses=["not json at all", {"a": 1}])
    assert llm.generate_json("sys", "prompt", max_retries=1) == {"a": 1}
    assert len(llm.calls) == 2


def test_generate_json_raises_after_exhausting_retries():
    llm = FakeLLMClient(responses=["nope", "still nope"])
    with pytest.raises(LLMError):
        llm.generate_json("sys", "prompt", max_retries=1)
