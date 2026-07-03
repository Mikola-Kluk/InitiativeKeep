import random

import pytest

from app.services import dice

pytestmark = pytest.mark.anyio


async def test_roll_expr_bounds():
    for _ in range(200):
        v = dice.roll_expr("2d6")
        assert 2 <= v <= 12


async def test_roll_expr_with_modifier():
    for _ in range(200):
        v = dice.roll_expr("18d10+36")
        assert 18 + 36 <= v <= 180 + 36


async def test_roll_expr_no_count_defaults_to_one():
    for _ in range(100):
        assert 1 <= dice.roll_expr("d20") <= 20


async def test_roll_expr_negative_modifier_clamped_to_one():
    # "1d4-10" would be negative; clamped to minimum 1
    for _ in range(100):
        assert dice.roll_expr("1d4-10") == 1


async def test_roll_expr_unparseable_returns_default():
    assert dice.roll_expr("garbage", default=7) == 7
    assert dice.roll_expr(None, default=5) == 5
    assert dice.roll_expr("") == 1


async def test_roll_expr_deterministic_with_seed():
    random.seed(42)
    a = dice.roll_expr("3d8+2")
    random.seed(42)
    b = dice.roll_expr("3d8+2")
    assert a == b


async def test_roll_initiative_bounds():
    for _ in range(200):
        assert 1 + 3 <= dice.roll_initiative(3) <= 20 + 3
