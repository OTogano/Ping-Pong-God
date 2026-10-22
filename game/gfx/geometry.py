"""Small maths helpers for moving things around the screen."""


def lerp(a, b, t):
    """The value t (0..1) of the way from a to b."""
    return a + (b - a) * t


def lerp_pt(p, q, t):
    """The point t (0..1) of the way from p to q."""
    return (lerp(p[0], q[0], t), lerp(p[1], q[1], t))


def curve(p0, p1, p2, t):
    """Point t (0..1) along a quadratic Bezier curve: from p0 to p2, pulled toward p1."""
    u = 1 - t
    return (
        u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
        u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
    )


def bezier(p0, p1, p2, p3, t):
    """Point t (0..1) along a cubic Bezier curve: starts at p0, ends at p3, pulled toward p1 and p2."""
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
    )
