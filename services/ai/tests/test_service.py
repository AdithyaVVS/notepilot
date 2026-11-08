import json

from sqlalchemy import select

from app.config import settings
from app.main import app
from app.models import AnalysisCache, UsageLog
from app.providers import get_provider
from tests.conftest import SAMPLE_NOTE, BrokenLLM, TestSession, auth_headers

EVIDENCE = "Priya will send the budget by Friday."
NOTE = EVIDENCE + "\nWe talked about the offsite."


def good_reply():
    return json.dumps(
        {
            "summary": "Budget sync",
            "action_items": [
                {
                    "task": "Send the budget",
                    "owner": "Priya",
                    "deadline_text": "by Friday",
                    "priority": "medium",
                    "evidence": EVIDENCE,
                }
            ],
        }
    )


def analyze(client, note=NOTE, user=1, **extra):
    body = {"note": note, "today": "2026-11-04", **extra}
    return client.post("/ai/analyze", json=body, headers=auth_headers(user))


def usage_rows():
    with TestSession() as db:
        return list(db.scalars(select(UsageLog).order_by(UsageLog.id)))


def cache_rows():
    with TestSession() as db:
        return list(db.scalars(select(AnalysisCache)))


def test_repeat_note_is_served_from_cache(client, llm):
    llm.replies.append(good_reply())
    first = analyze(client)
    second = analyze(client)
    assert first.status_code == second.status_code == 200
    assert len(llm.calls) == 1
    assert first.json()["source"] == "ai"
    assert second.json()["source"] == "cache"
    assert first.json()["action_items"] == second.json()["action_items"]
    rows = usage_rows()
    assert [r.outcome for r in rows] == ["ok", "cache"]
    assert [r.requests for r in rows] == [1, 0]


def test_cache_is_per_user(client, llm):
    llm.replies.extend([good_reply(), good_reply()])
    analyze(client, user=1)
    analyze(client, user=2)
    assert len(llm.calls) == 2


def test_cached_result_resolves_deadline_for_todays_date(client, llm):
    llm.replies.append(good_reply())
    first = analyze(client, today="2026-11-04")
    second = analyze(client, today="2026-11-09")
    assert first.json()["action_items"][0]["deadline"] == "2026-11-06"
    assert second.json()["action_items"][0]["deadline"] == "2026-11-13"
    assert len(llm.calls) == 1


def test_user_daily_limit_blocks_further_requests(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "user_daily_limit", 2)
    llm.replies.extend([good_reply(), good_reply()])
    assert analyze(client, note=NOTE + "\nOne").status_code == 200
    assert analyze(client, note=NOTE + "\nTwo").status_code == 200
    assert analyze(client, note=NOTE + "\nThree").status_code == 429
    assert len(llm.calls) == 2


def test_retries_are_limited_by_remaining_quota(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "user_daily_limit", 1)
    llm.replies.extend(["not json", good_reply()])
    first = analyze(client)
    assert first.status_code == 502
    assert len(llm.calls) == 1  # no second attempt: no quota left for it
    [row] = usage_rows()
    assert (row.requests, row.outcome) == (1, "invalid")
    assert analyze(client, note=NOTE + "\nMore").status_code == 429


def test_global_limit_protects_the_shared_key(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "global_daily_limit", 1)
    llm.replies.append(good_reply())
    assert analyze(client, user=1).status_code == 200
    assert analyze(client, user=2).status_code == 503
    assert len(llm.calls) == 1


def test_sample_mode_uses_no_llm_and_no_quota(client, llm):
    response = analyze(client, note=SAMPLE_NOTE, mode="sample")
    assert response.status_code == 200
    assert response.json()["source"] == "sample"
    assert len(response.json()["action_items"]) == 3
    assert llm.calls == []
    assert usage_rows() == []


def test_provider_error_is_logged_and_counted(client):
    app.dependency_overrides[get_provider] = lambda: BrokenLLM()
    assert analyze(client).status_code == 502
    [row] = usage_rows()
    assert (row.requests, row.outcome) == (1, "provider_error")


def test_invalid_output_is_not_cached(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "max_attempts", 2)
    llm.replies.extend(["bad", "bad"])
    assert analyze(client).status_code == 502
    assert cache_rows() == []
    [row] = usage_rows()
    assert (row.requests, row.outcome) == (2, "invalid")


def test_usage_endpoint_reports_todays_count(client, llm):
    before = client.get("/ai/usage", headers=auth_headers())
    assert before.json() == {
        "used_today": 0,
        "daily_limit": settings.user_daily_limit,
    }
    llm.replies.append(good_reply())
    analyze(client)
    after = client.get("/ai/usage", headers=auth_headers())
    assert after.json()["used_today"] == 1
