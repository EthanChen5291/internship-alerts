"""The alert queue that keeps announcements behind the publish boundary."""

import json

import pytest

from intern_engine import outbox, paths


@pytest.fixture(autouse=True)
def _isolated_outbox(tmp_path, monkeypatch):
    """Point the outbox at a temp file so tests never touch data/outbox.json."""
    monkeypatch.setattr(paths, "OUTBOX_PATH", str(tmp_path / "outbox.json"))


def test_missing_file_is_an_empty_queue():
    assert outbox.load() == []


def test_queue_then_drain_round_trip():
    assert outbox.queue(["a", "b"]) == ["a", "b"]
    assert outbox.load() == ["a", "b"]
    outbox.drain()
    assert outbox.load() == []


def test_partial_drain_keeps_the_unannounced():
    # A run that announced 10 of 25 roles must keep the other 15 queued —
    # clearing the whole queue on any success is how they'd be lost.
    outbox.queue(["a", "b", "c", "d"])
    remaining = outbox.drain(["a", "c"])
    assert remaining == ["b", "d"]
    assert outbox.load() == ["b", "d"]


def test_draining_something_never_queued_is_harmless():
    outbox.queue(["a"])
    assert outbox.drain(["zzz"]) == ["a"]


def test_drain_with_no_argument_clears_everything():
    outbox.queue(["a", "b"])
    assert outbox.drain() == []
    assert outbox.load() == []


def test_queue_accumulates_across_failed_publishes():
    # Run 1 finds "a" but its push fails, so nothing is drained. Run 2 finds
    # "b". Both must go out together on the next successful publish — the
    # whole point of keeping the queue in a committed file.
    outbox.queue(["a"])
    assert outbox.queue(["b"]) == ["a", "b"]


def test_requeueing_the_same_role_does_not_duplicate_it():
    outbox.queue(["a", "b"])
    assert outbox.queue(["b", "c"]) == ["a", "b", "c"]


def test_backlog_is_bounded():
    outbox.queue([str(i) for i in range(outbox._MAX_PENDING + 50)])
    pending = outbox.load()
    assert len(pending) == outbox._MAX_PENDING
    assert pending[-1] == str(outbox._MAX_PENDING + 49)  # newest survive


def test_corrupt_queue_reads_as_empty_rather_than_crashing():
    # Unlike the job store, losing this file costs at most one announcement —
    # it must never take a run down.
    with open(paths.OUTBOX_PATH, "w", encoding="utf-8") as f:
        f.write("{not json")
    assert outbox.load() == []


def test_writes_are_atomic():
    outbox.queue(["a"])
    with open(paths.OUTBOX_PATH, encoding="utf-8") as f:
        assert json.load(f) == {"pending": ["a"]}
