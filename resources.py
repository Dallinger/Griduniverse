"""Creators vs. protectors."""


def step(r, V_w):
    """Equation 6."""
    return 2 * r * (1 - r * (1 + V_w) / 2.0)

r = 1.0
v_W = 0.5
for i in range(100):
    r = step(r, v_W)
    print(r)
