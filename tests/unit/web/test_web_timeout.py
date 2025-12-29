from src import web


def test_deadline_from_seconds_uses_now_reference():
    base = 100.0
    deadline = web._deadline_from_seconds(30, now=base)
    assert deadline == base + 30


def test_remaining_seconds_clamps_to_zero():
    deadline = 120.0
    assert web._remaining_seconds(deadline, now=110.0) == 10.0
    assert web._remaining_seconds(deadline, now=130.0) == 0.0
