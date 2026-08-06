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
        # Per-channel shape: each channel owns its own pending list.
        assert json.load(f) == {"pending": {"discord": ["a"], "telegram": ["a"]}}


class TestPerChannelQueues:
    """One channel failing must not drop or duplicate another channel's alert."""

    def test_queue_fans_out_to_every_channel(self):
        outbox.queue(["a", "b"])
        for channel in outbox.CHANNELS:
            assert outbox.load(channel) == ["a", "b"], channel

    def test_draining_one_channel_leaves_the_others(self):
        # The exact failure adding Telegram introduced: Discord delivers, the
        # Telegram push times out. Draining a shared list would have lost the
        # Telegram alert; not draining would have re-sent the Discord one.
        outbox.queue(["a", "b"])
        outbox.drain(["a", "b"], "discord")
        assert outbox.load("discord") == []
        assert outbox.load("telegram") == ["a", "b"]

    def test_union_load_reports_anything_still_owed(self):
        # The union is a set of "still owed somewhere" — channel order, not
        # queue order, decides how it lists.
        outbox.queue(["a", "b"])
        outbox.drain(["a"], "discord")
        assert set(outbox.load()) == {"a", "b"}   # 'a' still owed to telegram
        outbox.drain(["a"], "telegram")
        assert outbox.load() == ["b"]

    def test_legacy_single_list_migrates_to_every_channel(self):
        # Files written before channels existed hold {"pending": [...]}. Those
        # ids were never delivered anywhere but Discord, so every channel must
        # inherit them rather than the upgrade silently swallowing them.
        with open(paths.OUTBOX_PATH, "w", encoding="utf-8") as f:
            json.dump({"pending": ["old1", "old2"]}, f)
        for channel in outbox.CHANNELS:
            assert outbox.load(channel) == ["old1", "old2"], channel

    def test_drain_without_a_channel_clears_all(self):
        outbox.queue(["a"])
        outbox.drain()
        assert outbox.load() == []
