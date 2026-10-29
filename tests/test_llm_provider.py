import io
import json
from urllib.error import HTTPError
import pytest
from app import llm


def test_groq_uses_authorized_context_and_endpoint(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": "Allowed answer [chunk 7]"}}]}).encode())

    monkeypatch.setattr(llm, "urlopen", fake_urlopen)
    result = llm.answer("What is allowed?", [{"id": 7, "content": "Authorized source text"}])

    assert result == "Allowed answer [chunk 7]"
    assert requests[0].full_url == "https://api.groq.com/openai/v1/chat/completions"
    assert requests[0].get_header("Authorization") == "Bearer test-groq-key"
    payload = json.loads(requests[0].data)
    assert payload["model"] == "openai/gpt-oss-20b"
    assert "Authorized source text" in payload["messages"][1]["content"]


def test_no_provider_key_uses_local_answer(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert "[chunk 7]" in llm.answer("question", [{"id": 7, "content": "Allowed text"}])


def test_provider_rejection_has_safe_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setattr(llm, "urlopen", lambda request, timeout: (_ for _ in ()).throw(HTTPError(request.full_url, 401, "Unauthorized", {}, None)))
    with pytest.raises(llm.ProviderError, match="Groq rejected the API key") as exc:
        llm.answer("question", [{"id": 7, "content": "Allowed text"}])
    assert "test-secret" not in str(exc.value)
