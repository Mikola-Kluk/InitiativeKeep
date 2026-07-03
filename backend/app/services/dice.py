import random
import re

# matches "18d10+36", "2d6", "d20", "1d8 - 1"
_DICE_RE = re.compile(r"^\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def roll(n: int, sides: int) -> int:
    return sum(random.randint(1, sides) for _ in range(max(0, n)))


def roll_expr(expr: str | None, default: int = 1) -> int:
    """Roll a dice expression like '18d10+36'. Returns `default` if unparseable.
    Result is clamped to a minimum of 1."""
    if not expr:
        return default
    m = _DICE_RE.match(expr)
    if not m:
        return default
    n = int(m.group(1) or 1)
    sides = int(m.group(2))
    mod = int(m.group(3).replace(" ", "")) if m.group(3) else 0
    return max(1, roll(n, sides) + mod)


def roll_initiative(dex_modifier: int) -> int:
    return random.randint(1, 20) + dex_modifier
