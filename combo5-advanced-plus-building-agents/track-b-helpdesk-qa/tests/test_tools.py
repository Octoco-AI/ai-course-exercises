"""Tool tests — Track B."""

from __future__ import annotations


# ---- search_kb ----


def test_search_kb_returns_relevant_hits(sandbox):
    hits = sandbox["tools"].search_kb("how do I enable two factor authentication")
    assert len(hits) >= 1
    assert any("TOTP" in h["text"] for h in hits)
    assert all(0.0 <= h["score"] <= 1.0 for h in hits)


def test_search_kb_empty_query(sandbox):
    hits = sandbox["tools"].search_kb("")
    assert len(hits) == 1
    assert hits[0]["text"].startswith("ERROR:")


# ---- read_article ----


def test_read_article_reads(sandbox):
    content = sandbox["tools"].read_article("account-security.md")
    assert "Two-factor authentication" in content


def test_read_article_missing(sandbox):
    assert sandbox["tools"].read_article("nope.md").startswith("ERROR:")


def test_read_article_escape_attempt(sandbox):
    result = sandbox["tools"].read_article("../../../etc/passwd")
    assert result.startswith("ERROR:")
    assert "outside the sandbox" in result


# ---- create_draft_reply ----


def test_create_draft_reply_writes_file(sandbox):
    result = sandbox["tools"].create_draft_reply(
        subject="Re: How do I enable 2FA",
        body="Hi! Go to Settings → Account → Two-factor authentication. See account-security.md.",
        tags=["security", "2fa"],
    )
    assert result.startswith("OK:")
    drafts = list(sandbox["draft_replies"].glob("*.md"))
    assert len(drafts) == 1
    content = drafts[0].read_text()
    assert "subject: Re: How do I enable 2FA" in content
    assert "tags: [security, 2fa]" in content
    assert "Go to Settings" in content


def test_create_draft_reply_rejects_empty_fields(sandbox):
    result = sandbox["tools"].create_draft_reply(subject="", body="x")
    assert result.startswith("ERROR:")
    assert "subject" in result

    result = sandbox["tools"].create_draft_reply(subject="x", body="   ")
    assert result.startswith("ERROR:")
    assert "body" in result


# ---- escalate_to_human ----


def test_escalate_writes_ticket(sandbox):
    result = sandbox["tools"].escalate_to_human(
        category="billing",
        summary="User claims duplicate charge of $49. Needs a human to check Apple receipts.",
        priority="high",
    )
    assert result.startswith("OK:")
    tickets = list(sandbox["escalations"].glob("*.md"))
    assert len(tickets) == 1
    content = tickets[0].read_text()
    assert "category: billing" in content
    assert "priority: high" in content
    assert "duplicate charge" in content


def test_escalate_rejects_unknown_category(sandbox):
    result = sandbox["tools"].escalate_to_human(
        category="nonsense",
        summary="whatever",
    )
    assert result.startswith("ERROR:")
    assert "unknown category" in result


def test_escalate_rejects_invalid_priority(sandbox):
    result = sandbox["tools"].escalate_to_human(
        category="billing",
        summary="whatever",
        priority="super-urgent",
    )
    assert result.startswith("ERROR:")
    assert "priority" in result


def test_escalate_rejects_empty_summary(sandbox):
    result = sandbox["tools"].escalate_to_human(
        category="billing",
        summary="   ",
    )
    assert result.startswith("ERROR:")


def test_escalate_filename_encodes_priority_and_category(sandbox):
    sandbox["tools"].escalate_to_human(
        category="security",
        summary="suspicious login from unknown device",
        priority="urgent",
    )
    tickets = list(sandbox["escalations"].glob("*.md"))
    assert len(tickets) == 1
    name = tickets[0].name
    assert "urgent" in name
    assert "security" in name
