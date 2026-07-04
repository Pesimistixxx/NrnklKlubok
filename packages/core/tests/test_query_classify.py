"""Tests for conversational query classification."""
from __future__ import annotations

from mkg_core.query_classify import (
    classify_query_intent,
    is_conversational_query,
    retrieval_confidence_ok,
)


def test_greeting_hello():
    assert classify_query_intent("hello") == "greeting"
    assert is_conversational_query("hello")


def test_greeting_privet():
    assert classify_query_intent("привет") == "greeting"
    assert classify_query_intent("Привет!") == "greeting"


def test_domain_nickel_not_conversational():
    assert classify_query_intent("Что такое никель?") is None
    assert not is_conversational_query("Что такое никель?")


def test_mixed_greeting_with_domain_not_conversational():
    assert classify_query_intent("hello, what is nickel?") is None


def test_meta_who_are_you():
    assert classify_query_intent("who are you") == "meta"
    assert classify_query_intent("кто ты?") == "meta"


def test_retrieval_confidence_rejects_conversational():
    hits = [{"score": 0.9, "text": "tectonic faults CAE Fidesys"}]
    assert not retrieval_confidence_ok(hits, "hello")


def test_retrieval_confidence_rejects_weak_short_query():
    hits = [{"score": 0.12, "text": "random chunk"}]
    assert not retrieval_confidence_ok(hits, "foo bar")
