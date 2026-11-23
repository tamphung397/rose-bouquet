# Rose bouquet in ASCII
# @dwcminh.ascii, 2026
#
#   pip install numpy pygame-ce
#   python rose_bouquet.py
#
# A bouquet grows like a plant, glittering where it grows: the stems rise and branch up to where
# the flowers will be, leaves sprout from them and a bed of foliage spreads out; then, one after
# another, nineteen rosebuds pop on, silver paper wraps round from the back, a gold ribbon and
# bow snap on and baby's breath lights up flower by flower. The roses open one by one, each with
# a flash and a burst of sparks, "F O R   Y O U   <3" is typed out underneath, the <3 beating red;
# a gleam runs over the ribbon and petals fall as the bouquet turns gently from
# side to side. All the while stars twinkle round it and dew glints on the open roses.
#
# Space pause, R restart, S screenshot, Esc quit

import asyncio
import sys
import time
from pathlib import Path

import numpy as np
import pygame

CREDIT = "@dwcminh.ascii"
MESSAGE = "F O R   Y O U   <3"                    # typed out under the bouquet; the <3 is red and beats

TAU = np.pi * 2
LOOP = 20.0                                     # length of one run (s)

# timeline (s)
T_GROW = (0.5, 3.0)                             # the green: stems rise and branch, leaves sprout, foliage spreads
T_BUDS = (2.5, 3.6)                             # the rosebuds pop on, as the stems reach them
T_PAPER = (2.9, 4.1)                            # the silver paper wraps round, from the back to the front
T_RIBBON = 4.25                                 # the ribbon and bow snap on
T_BLOSSOM = (4.4, 5.1)                          # baby's breath lights up, flower by flower
GROWN = T_BLOSSOM[1]                            # everything is there
T_OPEN = 5.0                                    # the first bud starts to open...
STAGGER = 0.38                                  # ...the next one this much later...
OPEN = 2.6                                      # ...and each takes this long to open fully
T_GLEAM = (14.6, 15.8)                          # a band of light runs across the ribbon and bow
T_FALL = 15.2                                   # petals start to fall
T_MSG = 13.0                                    # the message is typed out, 10 letters a second
FLASH = 0.6                                     # how long something new glows white (s)

POOLS = ["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"]   # fill letters, dark -> bright
C = lambda ch: ord(ch) - 32                     # character -> glyph index
FILL = np.array([[C(p[k % len(p)]) for k in range(12)] for p in POOLS])

# what each point is, and its colour
(STEM, LEAF, SEPAL, PETAL, EDGE, GLINT, PAPER, PAPER_IN, RIBBON, DUST, GOLD, FOLIAGE, BLOSSOM,
 STAR_PINK, STAR_BLUE) = range(15)
COLORS = np.array([[70, 200, 96], [52, 196, 84], [80, 206, 100], [255, 34, 64], [255, 120, 146], [255, 255, 255],
                   [212, 220, 236], [128, 136, 156], [255, 190, 80], [220, 228, 245], [255, 214, 150],
                   [34, 130, 62], [255, 244, 248], [255, 150, 190], [170, 205, 255]], np.float32) / 255   # the paper is silver
WHITE = np.array([1.0, 1.0, 1.0], np.float32)
# the shades a rose can be (petal colour, rim colour), and which one each rose is: the middle one,
# the ring of six round it, the ring of twelve outside; neighbours differ, so each rose stands apart
SHADES = np.array([
    [[255, 22, 52], [255, 90, 112]],            # deep red
    [[255, 70, 140], [255, 150, 190]],          # pink
    [[255, 34, 64], [255, 110, 130]],           # red
    [[255, 120, 176], [255, 186, 214]],         # pale pink
    [[255, 50, 76], [255, 126, 144]],           # light red
], np.float32) / 255
ROSE_COLOURS = SHADES[[0] + [1, 2] * 3 + [3, 4, 0] * 4]
N_ROSES = len(ROSE_COLOURS)
PAPER_LIGHT, PAPER_IN_LIGHT = 0.66, 0.40        # the paper is held back, so the roses are the stars


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def normals_of(p, axis_u, axis_v, outward):
    # surface normals of a grid of points, turned to face `outward`
    n = np.cross(np.gradient(p, axis=axis_u), np.gradient(p, axis=axis_v))
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
    return n * np.sign((n * outward).sum(-1, keepdims=True) + 1e-9)


def turn_to(d):
    # the rotation that takes the y axis to direction d
    y = np.array([0.0, 1.0, 0.0])
    d = d / np.linalg.norm(d)
    v, c = np.cross(y, d), y @ d
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def spin_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)


# one rose: the well-known parametric rose, a single surface that spirals in round one axis and is
# cut into petals as it goes round; base at the origin, opening upwards. `spread` opens it; a bud
# is the same spiral drawn in close and tall

SPIRAL, ACROSS = 300, 10                        # points round the spiral, and across each petal
ANGLE, ALONG = np.meshgrid(np.linspace(2.2 * np.pi, 20 * np.pi, SPIRAL), np.linspace(0, 1, ACROSS))
INWARD = (ANGLE - ANGLE.min()) / (ANGLE.max() - ANGLE.min())       # 0 outermost petal .. 1 the heart
PETAL_ID = (np.floor(3.6 * ANGLE / TAU).astype(int) - int(np.floor(3.6 * ANGLE.min() / TAU))).ravel()
OUTER = 1 - INWARD.ravel()                      # 0 the heart .. 1 the outermost petal
STEPS = 50                                      # a rose opens in this many steps, each shape made once
_PETALS = {}


def petals(open_):
    # points, normals and rim flags of the flower at an opening of 0 (bud) .. 1 (full bloom)
    key = round(float(open_) * STEPS) / STEPS
    if key not in _PETALS:
        spread = 1.4 + 4.2 * key                        # how fast the spiral leans out on its way out
        lean = (np.pi / 2) * np.exp(-ANGLE / (spread * np.pi))
        width = 1 - 0.5 * (1.25 * (1 - np.mod(3.6 * ANGLE, TAU) / np.pi) ** 2 - 0.25) ** 2
        cup = 1.95653 * ALONG ** 2 * (1.27689 * ALONG - 1) ** 2 * np.sin(lean)
        r = width * (ALONG * np.sin(lean) + cup * np.cos(lean))
        y = width * (ALONG * np.cos(lean) - cup * np.sin(lean))
        p = np.stack([r * np.sin(ANGLE), y, r * np.cos(ANGLE)], -1) * 0.8
        wrap = smooth(key / 0.7)                        # a bud: petals wrapped close round the heart...
        p[..., [0, 2]] *= 0.72 + 0.28 * wrap
        p[..., 1] *= 0.66 + 0.34 * wrap                 # ...and short, like an egg
        out = np.stack([np.sin(ANGLE), np.full_like(ANGLE, 0.3), np.cos(ANGLE)], -1)
        n = normals_of(p, 1, 0, out)
        _PETALS[key] = (p.reshape(-1, 3).astype(np.float32), n.reshape(-1, 3).astype(np.float32), (ALONG > 0.92).ravel())
    return _PETALS[key]


N_SEPAL, SEP_LEN, SEP_ACROSS = 5, 10, 3
_sl, _sw = np.meshgrid(np.linspace(0, 1, SEP_LEN), np.linspace(-1, 1, SEP_ACROSS))


_SEPALS = {}


def sepals(open_):
    # five narrow green leaflets under the flower: each a curve from the base, out and down, that
    # droops further as the flower opens; narrow at the base, widest a third of the way, pointed
    open_ = round(float(open_) * 10) / 10
    if open_ in _SEPALS:
        return _SEPALS[open_]
    P, N = [], []
    reach, droop = 0.24 + 0.06 * open_, 0.10 + 0.14 * open_
    for i in range(N_SEPAL):
        a = TAU * i / N_SEPAL + 0.6
        out = np.array([np.sin(a), 0.0, np.cos(a)])
        side = np.array([np.cos(a), 0.0, -np.sin(a)])
        b0, b1, b2 = np.array([0, 0.03, 0]) + 0.03 * out, 0.16 * out + [0, 0.10 - 0.10 * open_, 0], reach * out - [0, droop, 0]
        u = _sl[..., None]
        mid = (1 - u) ** 2 * b0 + 2 * (1 - u) * u * b1 + u ** 2 * b2           # a quadratic curve
        half = 0.05 * np.sin(np.pi * np.minimum(_sl * 1.5, 1) / 2) * (1 - _sl) ** 0.7
        pts = mid + side * (half * _sw)[..., None]
        P.append(pts.reshape(-1, 3))
        N.append(normals_of(pts, 1, 0, np.array([0.0, 1.0, 0.0])).reshape(-1, 3))
    _SEPALS[open_] = (np.concatenate(P).astype(np.float32), np.concatenate(N).astype(np.float32))
    return _SEPALS[open_]


# the bouquet: where each rose sits, and the order they open in (the middle one first)

ROSE_SIZE = 0.30                                # an open rose is about 0.44 across: wider than the gap to the next
WAIST = np.array([0.0, -0.62, 0.0])             # where the ribbon ties the stems together
BOTTOM_Y = -1.10                                # where the stems are cut
DOME, DOME_R = np.array([0.0, -0.38, 0.0]), 0.64   # the roses sit on a dome: its centre and radius
RING_TILT = 0.47                                # how far each ring of roses leans out from the one inside it (rad)


def on_dome(tilt, around):
    # the direction from the dome's centre, `tilt` from straight up, `around` from the front
    return np.array([np.sin(tilt) * np.sin(around), np.cos(tilt), np.sin(tilt) * np.cos(around)])


def layout():
    # packed like a real bouquet: one rose on top, six round it, twelve round those, every one
    # facing straight out of the dome, close enough that the open flowers touch and no gap is left
    lean = [on_dome(0.0, 0.0)]
    lean += [on_dome(RING_TILT, TAU * k / 6 + TAU / 12) for k in range(6)]
    lean += [on_dome(2 * RING_TILT, TAU * k / 12) for k in range(12)]
    pos = [DOME + DOME_R * d for d in lean]
    rng = np.random.default_rng(5)
    turns = [turn_to(d) @ spin_y(rng.uniform(0, TAU)) for d in lean]
    # opening order: the top, then the inner ring and the outer ring, each jumping from side to side
    order = [0] + [1, 4, 2, 5, 3, 6] + [7 + (5 * j) % 12 for j in range(12)]
    starts = np.empty(N_ROSES)
    starts[order] = T_OPEN + STAGGER * np.arange(N_ROSES)
    return pos, lean, turns, starts


ROSE_POS, ROSE_DIR, ROSE_TURN, ROSE_START = layout()
ROSE_POS = [p.astype(np.float32) for p in ROSE_POS]
ROSE_TURN = [R.astype(np.float32) for R in ROSE_TURN]


STEM_TOP = max(float(q[1]) for q in ROSE_POS)    # the highest rose sits here


def grow_time(y):
    # when the stems reach height y: from the cut ends at the start of T_GROW to the top rose at its end
    return T_GROW[0] + (T_GROW[1] - T_GROW[0]) * np.clip((y - BOTTOM_Y) / (STEM_TOP - BOTTOM_Y), 0, 1)


# each bud pops on a little after its stem reaches it, spread over T_BUDS
_bud = np.random.default_rng(23).random(N_ROSES)
BUD_POP = np.array([T_BUDS[0] + (T_BUDS[1] - T_BUDS[0] - 0.35) * (float(q[1]) - (-0.01)) / (STEM_TOP + 0.01)
                    for q in ROSE_POS]) + 0.35 * _bud


def opening(t):
    # 0 bud .. 1 full bloom, for every rose: eased in and out, a little quicker at the start
    e = smooth((t - ROSE_START) / OPEN)
    return e * (1.35 - 0.35 * e)


def tube(curve, radius, around=10):
    # a round tube along a polyline of points
    d = np.gradient(curve, axis=0)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    side = np.cross(d, [0.0, 0.0, 1.0])
    side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-9
    up = np.cross(side, d)
    a = np.linspace(0, TAU, around, endpoint=False)
    n = np.cos(a)[None, :, None] * side[:, None] + np.sin(a)[None, :, None] * up[:, None]
    return (curve[:, None] + radius * n).reshape(-1, 3), n.reshape(-1, 3)


def stems():
    # the stems: gathered at the waist and splaying a little down to the cut, and above the waist
    # each one curving up to its own rose (inside the paper, so seen only while the bouquet grows)
    P, N = [], []
    for k in range(9):
        spot = np.array([0.026 * np.sin(1.7 * k), 0.0, 0.026 * np.cos(1.7 * k)]) * (k > 0)
        top = WAIST + spot + [0.0, 0.10, 0.0]
        end = WAIST + spot * 2.4 + [0.0, BOTTOM_Y - WAIST[1], 0.0]
        p_, n_ = tube(top + (end - top) * np.linspace(0, 1, 40)[:, None], 0.013, 6)
        P.append(p_)
        N.append(n_)
    for k in range(N_ROSES):
        base = ROSE_POS[k] - ROSE_DIR[k] * 0.02
        start = WAIST + [0.0, 0.10, 0.0] + np.array([0.026 * np.sin(1.7 * k), 0.0, 0.026 * np.cos(1.7 * k)])
        bend = np.array([0.35 * base[0], 0.5 * (start[1] + base[1]), 0.35 * base[2]])
        u = np.linspace(0, 1, 30)[:, None]
        p_, n_ = tube((1 - u) ** 2 * start + 2 * (1 - u) * u * bend + u ** 2 * base, 0.011, 5)
        P.append(p_)
        N.append(n_)
    return np.concatenate(P), np.concatenate(N)


def foliage():
    # a deep green dome just under the flowers, so nothing but leaf shows between the buds
    tilt, a = np.meshgrid(np.linspace(0, 1.25, 20), np.linspace(0, TAU, 90, endpoint=False))
    r = 0.60 + 0.012 * np.sin(7 * a + 14 * tilt)
    p = DOME + r[..., None] * np.stack([np.sin(tilt) * np.sin(a), np.cos(tilt), np.sin(tilt) * np.cos(a)], -1)
    start = grow_time(0.0)                              # the bed spreads out from the middle once the stems are that high
    appear = start + (T_GROW[1] - start) * tilt / 1.25
    return p.reshape(-1, 3), normals_of(p, 1, 0, np.array([0.0, 1.0, 0.0])).reshape(-1, 3), appear.ravel()


N_BLOSSOM = 110
_bl = np.random.default_rng(41).random((N_BLOSSOM, 3))


def blossoms():
    # baby's breath: little white flowers in a collar round the outer roses, just inside the paper
    tilt, a = 2 * RING_TILT + 0.12 + 0.30 * _bl[:, 0], _bl[:, 1] * TAU
    p = DOME + (DOME_R + 0.10) * np.stack([np.sin(tilt) * np.sin(a), np.cos(tilt), np.sin(tilt) * np.cos(a)], 1)
    return p.astype(np.float32), _bl[:, 2]


BLOSSOM_P, BLOSSOM_PHASE = blossoms()


def leaf(base, d, length):
    # a leaf: a slim blade, round at the base and pointed at the tip, with a small saw edge; it is
    # creased along the middle (a V) and curls down towards the tip
    s, w = np.meshgrid(np.linspace(0, 1, 34), np.linspace(-1, 1, 11))
    d = d / np.linalg.norm(d)
    wide = np.cross(d, [0.0, 1.0, 0.0])
    wide /= np.linalg.norm(wide)
    up = np.cross(wide, d)
    half = 0.30 * length * np.sqrt(s) * (1 - s) ** 0.8 * 1.9 * (1 + 0.06 * np.sin(s * 40))
    crease = 0.10 * length * w ** 2
    curl = -0.28 * length * s ** 1.8
    p = base + d * (s * length)[..., None] + wide * (w * half)[..., None] + up * (crease + curl)[..., None]
    return p.reshape(-1, 3), normals_of(p, 1, 0, up).reshape(-1, 3), s.ravel()


def leaves():
    # leaves poking out over the rim of the paper, all the way round under the outer roses
    P, N, part, appear = [], [], [], []
    for j in range(1, 7):                               # none in front, where they would hide the bow
        a = TAU * j / 8 + TAU / 16
        base = np.array([0.60 * np.sin(a), -0.17, 0.60 * np.cos(a)])
        d = np.array([np.sin(a), 0.05, np.cos(a)])
        p, n, along = leaf(base, d, 0.30 + 0.03 * np.sin(5 * a))
        P.append(p)
        N.append(n)
        part.append(np.full(len(p), 20 + j))
        appear.append(grow_time(base[1]) + 0.12 * j + 0.5 * along)     # each sprouts out from its base over 0.5 s
    return np.concatenate(P), np.concatenate(N), np.concatenate(part), np.concatenate(appear)


def paper():
    # the wrapping: a pleated cone from the waist, higher at the back so the roses show in front.
    # a = 0 is the side facing the camera
    a, v = np.meshgrid(np.linspace(0, TAU, 150, endpoint=False), np.linspace(0, 1, 28))
    top = -0.15 + 0.60 * (1 - np.cos(a)) / 2 + 0.03 * np.cos(9 * a)
    r = (0.075 + (0.645 + 0.20 * (1 - np.cos(a)) / 2) * v ** 0.75) * (1 + 0.07 * v * np.sin(9 * a))   # a bowl, wide enough for the dome
    y = WAIST[1] + v * (top - WAIST[1])
    p = np.stack([r * np.sin(a), y, r * np.cos(a)], -1)
    n = normals_of(p, 1, 0, np.stack([np.sin(a), np.zeros_like(a), np.cos(a)], -1))
    rim = v > 0.965
    wrap = (1 + np.cos(a)) / 2                          # 0 at the back .. 1 in front
    appear = T_PAPER[0] + (T_PAPER[1] - T_PAPER[0]) * (0.6 * wrap + 0.4 * v)
    return p.reshape(-1, 3), n.reshape(-1, 3), rim.ravel(), appear.ravel()


def ribbon():
    # a gold band round the waist, a bow in front of it (two loops, a knot) and two tails
    P, N, part = [], [], []

    def add(p, n, k):
        P.append(p.reshape(-1, 3))
        N.append(n.reshape(-1, 3))
        part.append(np.full(len(P[-1]), k))

    a, w = np.meshgrid(np.linspace(0, TAU, 120, endpoint=False), np.linspace(-1, 1, 6))
    band = np.stack([0.09 * np.sin(a), WAIST[1] + 0.022 * w, 0.09 * np.cos(a)], -1)
    add(band, np.stack([np.sin(a), 0 * a, np.cos(a)], -1), 70)
    knot = WAIST + [0.0, 0.0, 0.10]
    for side, k in ((-1, 71), (1, 72)):
        u, q = np.meshgrid(np.linspace(0, TAU, 80), np.linspace(0, 1, 9))
        rx, ry = 0.03 + 0.055 * q, 0.010 + 0.036 * q           # a loop: an oval ring, tipped up a little
        x, y = side * (0.02 + rx + rx * np.cos(u + np.pi)), ry * np.sin(u)
        tip = side * 0.30
        x, y = x * np.cos(tip) - y * np.sin(tip), x * np.sin(tip) + y * np.cos(tip)
        z = 0.03 * np.sin(u / 2) ** 2 + 0.015 * q
        p = knot + np.stack([x, y, z], -1)
        add(p, normals_of(p, 1, 0, np.array([0.0, 0.3, 1.0])), k)
    for side, k in ((-1, 73), (1, 74)):
        s, w = np.meshgrid(np.linspace(0, 1, 40), np.linspace(-1, 1, 7))
        keep = s < 1 - 0.10 * (1 - np.abs(w))                  # the end is cut in a V
        centre = np.stack([side * (0.03 + 0.08 * s), -0.02 - 0.22 * s, 0.03 + 0.03 * np.sin(3 * s)], -1)
        across = np.stack([0.030 * np.cos(0.4 * side) + 0 * s, 0.030 * np.sin(0.4 * side) + 0 * s, 0 * s], -1)
        p = knot + centre + across * w[..., None]
        n = normals_of(p, 1, 0, np.array([0.0, 0.0, 1.0]))
        add(p[keep], n[keep], k)
    u, q = np.meshgrid(np.linspace(0, TAU, 40, endpoint=False), np.linspace(0, 1, 6))
    p = knot + np.stack([0.032 * q * np.cos(u), 0.028 * q * np.sin(u), 0.035 - 0.02 * q ** 2], -1)
    add(p, normals_of(p, 1, 0, np.array([0.0, 0.0, 1.0])), 75)
    return np.concatenate(P), np.concatenate(N), np.concatenate(part)


class Bouquet:
    # everything that does not move on its own: stems, leaves, paper and ribbon
    def __init__(self):
        sp, sn = stems()
        fp, fn, f_appear = foliage()
        lp, ln, lpart, l_appear = leaves()
        pp, pn, prim, p_appear = paper()
        rp, rn, rpart = ribbon()
        self.p = np.concatenate([sp, fp, lp, pp, rp]).astype(np.float32)      # float32: half the work per frame
        self.n = np.concatenate([sn, fn, ln, pn, rn]).astype(np.float32)
        self.tag = np.concatenate([np.full(len(sp), STEM), np.full(len(fp), FOLIAGE), np.full(len(lp), LEAF),
                                   np.full(len(pp), PAPER), np.full(len(rp), RIBBON)])
        self.part = np.concatenate([np.full(len(sp), 1), np.full(len(fp), 50), lpart, np.full(len(pp), 60), rpart])
        self.rim = np.concatenate([np.zeros(len(sp) + len(fp) + len(lp), bool), prim, np.zeros(len(rp), bool)])
        self.ribbon = self.tag == RIBBON
        # when each point shows up, and which ones pop on as a whole (swelling, white-hot) instead
        # of growing: the ribbon pops on round its knot, the band round the waist
        self.appear = np.concatenate([grow_time(sp[:, 1]), f_appear, l_appear, p_appear,
                                      np.full(len(rp), T_RIBBON)]).astype(np.float32)
        self.pop = np.concatenate([np.zeros(len(sp) + len(fp) + len(lp) + len(pp), bool), np.ones(len(rp), bool)])
        knot = WAIST + [0.0, 0.0, 0.10]
        self.centre = self.p.copy()
        self.centre[self.pop] = np.where((rpart == 70)[:, None], WAIST, knot)


BOUQUET = Bouquet()
ROSE_APPEAR = None                              # filled in once rose() exists: each bud pops on whole
BLOSSOM_APPEAR = T_BLOSSOM[0] + (T_BLOSSOM[1] - T_BLOSSOM[0]) * np.random.default_rng(43).random(N_BLOSSOM)


# falling petals: each tumbles down from a random rose, drawn in a few letters that change as it
# turns: face on, tilted one way, edge on, tilted the other way

N_FALL = 18
FALL = np.random.default_rng(17).random((N_FALL, 8))
FALL_PERIOD = 5.0                               # each petal falls again this often (s)
FALL_POSES = [("(", ")"), ("/", ""), ("-", ""), ("\\", ""), ("{", "}"), ("<", ">")]
FALL_TURN = [0, 1, 2, 3, 4, 3, 2, 1]            # the order the poses come round in as it tumbles
FALL_FROM = [k for k in range(N_ROSES) if ROSE_DIR[k][2] > -0.3]     # not the roses at the back


def falling(t):
    # every petal in the air: where it is, which rose it came from, and its pose
    out = []
    for k, (a, b, c, d, e, f, g, h) in enumerate(FALL):
        since = t - T_FALL - k * FALL_PERIOD / N_FALL
        if since < 0:
            continue
        age = since % FALL_PERIOD
        rose = FALL_FROM[int(a * len(FALL_FROM))]
        start = ROSE_POS[rose] + ROSE_TURN[rose] @ (np.array([np.cos(b * TAU), 0.10, np.sin(b * TAU)]) * ROSE_SIZE * 0.35)
        drift = np.array([0.20 * (c - 0.5) * age + 0.06 * np.sin(age * (2 + 2 * d) + e * TAU),
                          -0.30 * age, 0.25 * age * f + 0.05 * np.cos(age * (2 + g) + h * TAU)])
        pose = FALL_TURN[int(age * (3 + 3 * d) + e * 8) % len(FALL_TURN)]
        fade = smooth(age / 0.3) * smooth((FALL_PERIOD - age) / 0.6)
        out.append((start + drift, rose, pose, fade))
    return out


# particles: sparks thrown out as each rose opens fully, and the stars round the bouquet

POP = np.random.default_rng(13).random((N_ROSES, 14, 4))
N_STARS = 460
STARS = np.random.default_rng(21).random((N_STARS, 6))
STAR_FLARES = 6                                 # how many of the brightest stars throw rays at once


def pops(t, op):
    P, S, T = [], [], []
    for k in range(N_ROSES):
        age = t - (ROSE_START[k] + 0.85 * OPEN)
        if not 0 < age < 1.4:
            continue
        g = POP[k]
        a, up = g[:, 0] * TAU, 0.4 + 0.8 * g[:, 1]
        speed = 0.45 + 0.5 * g[:, 2]
        v = np.stack([np.cos(a) * speed, up, np.sin(a) * speed], 1)
        head = ROSE_POS[k] + ROSE_DIR[k] * 0.12
        P.append(head + v * age - np.array([0, 0.9, 0]) * age ** 2)
        S.append((1 - age / 1.4) ** 1.2 * (0.8 + 0.5 * g[:, 3]))
        T.append(np.where(g[:, 3] > 0.5, GLINT, GOLD))
    if not P:
        return np.zeros((0, 3)), np.zeros(0), np.zeros(0, int)
    return np.concatenate(P), np.concatenate(S), np.concatenate(T)


def stars(t):
    # stars hanging in the air all round the bouquet, drifting a little: each is faint most of the
    # time and flares up for a moment on its own beat. They stay put while the bouquet turns
    g = STARS
    x = 2.5 * g[:, 0] - 1.25 + 0.04 * np.sin(t * 0.5 + g[:, 5] * TAU)
    y = -1.75 + 3.1 * ((g[:, 1] + t * 0.006 * (0.5 + g[:, 3])) % 1.0)          # rising very slowly
    z = -1.3 + 2.2 * g[:, 2]                                                    # behind, beside and in front
    beat = 2.5 + 4.5 * g[:, 3]                                                  # seconds between its flares
    peak = np.clip(1 - np.abs((t / beat + g[:, 4]) % 1.0 - 0.5) * beat / 0.24, 0, 1)   # each lasts about half a second
    glow = 0.30 + 0.35 * g[:, 5] + peak ** 1.5
    kind = np.select([g[:, 2] % 0.25 < 0.045, g[:, 2] % 0.25 < 0.08, g[:, 2] % 0.25 < 0.105], [STAR_PINK, STAR_BLUE, GOLD], GLINT)
    return np.stack([x, y, z], 1), glow, kind


# light, motion, camera

def lights(t):
    # a key light from the upper right, and a soft sheen that sweeps from side to side
    key = np.array([0.45, 0.80, 0.55])
    sheen = np.array([0.9 * np.sin(t * 0.5), 0.35, 0.6])
    return key / np.linalg.norm(key), sheen / np.linalg.norm(sheen)


def sway(t):
    # the bouquet turns gently from side to side
    return 0.38 * np.sin(TAU * t / LOOP) * smooth(t / 1.5)


EYE, TARGET = np.array([0.0, 1.75, 4.0]), np.array([0.0, -0.28, 0.0])
_FWD = (TARGET - EYE) / np.linalg.norm(TARGET - EYE)
_RIGHT = np.cross(_FWD, [0, 1.0, 0])
_RIGHT /= np.linalg.norm(_RIGHT)
_UP = np.cross(_RIGHT, _FWD)
VIEW = (-_FWD).astype(np.float32)
_RIGHT, _UP, _FWD = (v.astype(np.float32) for v in (_RIGHT, _UP, _FWD))
EYE32 = EYE.astype(np.float32)


def look(P):
    rel = P - EYE32
    return rel @ _RIGHT, rel @ _UP, rel @ _FWD


_ROSES, _ROSE_LOOKS = {}, {}


def rose(k, open_, flash):
    # rose k in place in the bouquet: petals then sepals (kept until that rose changes)
    key = (open_, flash)
    if k not in _ROSES or _ROSES[k][0] != key:
        p, n, rim = petals(open_)
        sp, sn = sepals(open_)
        if k not in _ROSE_LOOKS:                                # what never changes: kind, colour, part
            _ROSE_LOOKS[k] = (
                np.concatenate([np.where(rim, EDGE, PETAL), np.full(len(sp), SEPAL)]),
                np.concatenate([np.where(rim[:, None], ROSE_COLOURS[k, 1], ROSE_COLOURS[k, 0]),
                                np.broadcast_to(COLORS[SEPAL], (len(sp), 3))]),
                np.concatenate([1000 + 100 * k + PETAL_ID, np.full(len(sp), 40 + k)]))   # rose k, petal j; its sepals
        size = np.float32(ROSE_SIZE * (1 + 0.12 * flash))     # puffs up a little as it starts to open
        R = ROSE_TURN[k]
        _ROSES[k] = (key, (ROSE_POS[k] + (np.concatenate([p, sp]) * size) @ R.T, np.concatenate([n, sn]) @ R.T)
                     + _ROSE_LOOKS[k])
    return _ROSES[k][1]


_BUILT = {}


def assemble(states):
    # everything about the points that the light and the turning do not change, for one set of
    # roses (which, how far open, how much each flashes); kept until one of them changes
    if _BUILT.get("key") != states:
        b = BOUQUET
        P, N, T, K, tone = [b.p], [b.n], [b.tag], [b.part], [COLORS[b.tag]]
        W, gain, appear = [np.zeros(len(b.p), np.float32)], [np.where(b.tag == FOLIAGE, 0.55, 1.0)], [b.appear]
        pop, centre = [b.pop], [b.centre]
        at, n = {}, len(b.p)
        for k, open_, flash in states:
            rp, rn, rt, rtone, rk = rose(k, open_, flash)
            at[k], n = n, n + len(rp)
            P.append(rp)
            N.append(rn)
            T.append(rt)
            K.append(rk)
            tone.append(rtone)
            W.append(np.where(rt == SEPAL, 0.0, 0.75 * flash))
            gain.append(np.concatenate([HEART, np.ones(len(rp) - len(HEART))]))    # darker at its heart
            appear.append(ROSE_APPEAR[k])
            pop.append(np.ones(len(rp), bool))
            centre.append(np.broadcast_to(ROSE_POS[k], rp.shape))
        v = {"P": np.concatenate(P), "N": np.concatenate(N), "T": np.concatenate(T), "K": np.concatenate(K),
             "tone": np.concatenate(tone).astype(np.float32), "W": np.concatenate(W).astype(np.float32),
             "gain": np.concatenate(gain).astype(np.float32), "appear": np.concatenate(appear), "at": at,
             "pop": np.concatenate(pop), "centre": np.concatenate(centre).astype(np.float32)}
        v["lit"] = np.flatnonzero(v["W"] > 0)
        v["gloss"] = np.where(v["T"] == RIBBON, 0.9, 0.3).astype(np.float32)
        v["paper"] = np.flatnonzero(v["T"] == PAPER)
        v["paper_rim"] = b.rim[v["paper"]]
        v["ribbon"] = np.flatnonzero(v["T"] == RIBBON)
        _BUILT.update(key=states, value=v)
    return _BUILT["value"]


def scene(t):
    # every point of the bouquet at time t: where, how bright, what colour, which part
    global ROSE_APPEAR, BLOSSOM_APPEAR
    if ROSE_APPEAR is None:
        ROSE_APPEAR = [np.full(len(rose(k, 0.0, 0.0)[0]), BUD_POP[k], np.float32) for k in range(N_ROSES)]
    op = opening(t)
    yaw = sway(t)
    Ry = spin_y(yaw)

    # the roses: those at the back of the dome, facing away, are hidden by the others and left out
    states, heads = [], []
    for k in range(N_ROSES):
        if (Ry @ ROSE_DIR[k]) @ VIEW < -0.3:
            continue
        flash = np.clip(1 - (t - ROSE_START[k]) / FLASH, 0, 1) ** 2 if t >= ROSE_START[k] else 0.0
        states.append((k, round(float(op[k]) * STEPS) / STEPS, round(float(flash), 1)))
        heads.append(((ROSE_POS[k] + ROSE_DIR[k] * 0.10 * (0.5 + op[k])) @ Ry.T, flash))
    v = assemble(tuple(states))
    P = v["P"]
    growing = t < GROWN + FLASH
    if growing:
        # a part that pops on starts small, swells a little past its size and settles (0.2 s)
        age = t - v["appear"]
        pf = np.flatnonzero(v["pop"] & (age >= 0) & (age < FLASH))
        if len(pf):
            g = smooth(age[pf] / 0.2) * (1 + 0.35 * np.clip(1 - age[pf] / FLASH, 0, 1) ** 2)
            P = P.copy()
            P[pf] = v["centre"][pf] + (P[pf] - v["centre"][pf]) * g[:, None].astype(np.float32)
    P, N, K = P @ Ry.T, v["N"] @ Ry.T, v["K"]
    T, rgb = v["T"].copy(), v["tone"].copy()

    # light: a key light and a sweeping sheen; a surface seen from behind (the inside of the
    # paper) is lit as if from the front
    key, sheen = (x.astype(np.float32) for x in lights(t))
    half_k = ((key + VIEW) / np.linalg.norm(key + VIEW)).astype(np.float32)
    half_s = ((sheen + VIEW) / np.linalg.norm(sheen + VIEW)).astype(np.float32)
    back = N @ VIEW < 0
    side = np.where(back, np.float32(-1), np.float32(1))
    diff = np.clip(side * (N @ key), 0, 1)
    a2 = np.clip(side * (N @ half_k), 0, 1) ** 2
    b2 = np.clip(side * (N @ half_s), 0, 1) ** 2
    a8, b8 = (a2 * a2) ** 2, (b2 * b2) ** 2
    shade = (0.62 + 0.60 * diff + v["gloss"] * (a8 * a8 * a8 + 0.7 * b8 * b8 * b2)) * v["gain"]      # powers 24 and 18
    # silver: a broad sheen on every pleat that faces the light, travelling as the light sweeps
    pp = v["paper"]
    shade[pp] = 0.40 + 0.45 * diff[pp] + 1.1 * (a2[pp] ** 3 + b2[pp] ** 3)
    inside = pp[back[pp] & ~v["paper_rim"]]
    T[inside], rgb[inside] = PAPER_IN, COLORS[PAPER_IN]

    # the gleam: a band of light running across the ribbon and bow
    if T_GLEAM[0] < t < T_GLEAM[1] + 0.3:
        rb = v["ribbon"]
        at = -0.35 + 0.70 * (t - T_GLEAM[0]) / (T_GLEAM[1] - T_GLEAM[0])
        g = np.exp(-((look(P[rb])[0] - at) / 0.05) ** 2)
        shade[rb] += 1.45 * g
        rgb[rb] += (WHITE - rgb[rb]) * (0.7 * g)[:, None]

    # dew on the open roses: drops on the outer petals, each catching the light on its own beat
    for k, start in v["at"].items():
        if op[k] < 0.85:
            continue
        idx = start + DEW_AT
        beat = np.clip(1 - np.abs((t + DEW_OFF + 0.7 * k) % DEW_EVERY - 0.25) / 0.25, 0, 1)
        on = idx[beat > 0.3]
        T[on], rgb[on] = GLINT, WHITE
        shade[idx] = np.maximum(shade[idx], 0.6 + 0.7 * beat)

    # a rose flashes white as it starts to open
    lit = v["lit"]
    if len(lit):
        w = v["W"][lit]
        rgb[lit] += (WHITE - rgb[lit]) * w[:, None]
        shade[lit] += 0.8 * w

    # growing: only what has appeared is there. The growing edge glitters white; a part that pops
    # on glows white-hot and cools to its own colour
    if growing:
        fresh = ~v["pop"] & (age >= 0) & (age < 0.14)
        T[fresh], shade[fresh], rgb[fresh] = GLINT, 1.2, WHITE
        hot = v["pop"] & (age >= 0) & (age < FLASH)
        f = (np.clip(1 - age[hot] / FLASH, 0, 1) ** 2).astype(np.float32)
        rgb[hot] += (WHITE - rgb[hot]) * f[:, None]
        shade[hot] += 1.3 * f
        seen = age >= 0
        P, shade, rgb, T, K = P[seen], shade[seen], rgb[seen], T[seen], K[seen]

    fall = falling(t)
    gp, gs, gt = stars(t)
    sp, ss, st = pops(t, op)
    lit_up = np.clip(1 - (t - BLOSSOM_APPEAR) / FLASH, 0, 1) ** 2 * (t >= BLOSSOM_APPEAR)   # each flares as it lights
    bs = (0.55 + 0.35 * np.clip(np.sin(t * 1.3 + BLOSSOM_PHASE * 40), 0, 1) ** 4 + 0.9 * lit_up) * (t >= BLOSSOM_APPEAR)
    extra = np.concatenate([np.concatenate([BLOSSOM_P, sp]) @ Ry.T, gp])   # the stars do not turn with the bouquet
    info = {"open": int((op > 0.98).sum()), "falling": len(fall), "deg": float(np.degrees(yaw)),
            "grown": float(np.clip((t - T_GROW[0]) / (GROWN - T_GROW[0]), 0, 1))}
    fall = [(pos @ Ry.T, rose_k, pose, fade) for pos, rose_k, pose, fade in fall]
    fx_shade = np.concatenate([bs, ss, gs])
    fx_tag = np.concatenate([np.full(N_BLOSSOM, BLOSSOM), st, gt])
    return (P, shade, rgb, T, K), (extra, fx_shade, fx_tag), heads, fall, info


N_DEW = 14                                      # dewdrops on each open rose
_dew = np.random.default_rng(31)
DEW_AT = np.flatnonzero((OUTER > 0.6) & (ALONG.ravel() > 0.6))[_dew.integers(0, 300, N_DEW)]
DEW_OFF, DEW_EVERY = _dew.uniform(0, 10, N_DEW), _dew.uniform(2.0, 4.0, N_DEW)
HEART = (0.66 + 0.34 * OUTER ** 0.8).astype(np.float32)      # a rose is darker at its heart


# points -> letters

def outline_letter(gx, gy):
    ax, ay = np.abs(gx), np.abs(gy)
    c = np.where(ax > 2 * ay, C("|"), np.where(ay > 2 * ax, np.where(gy > 0, C("_"), C("-")),
                 np.where(gx * gy > 0, C("/"), C("\\"))))
    return np.where((ax + ay) == 0, C("+"), c)


def rays(char, col, cy, cx, reach, rgb, strength=1.0, over=1.0):
    # a four-pointed flare: long arms sideways and up/down, short diagonals. An arm only shows
    # where it outshines what is there; `over` lets it show across brighter letters too (petals)
    rows, cols = char.shape
    for dist in range(1, reach + 1):
        fade = (1 - dist / (reach + 1)) * strength
        arms = [(0, 1, "-"), (0, -1, "-"), (1, 0, "|"), (-1, 0, "|")]
        if dist <= reach // 2:
            arms += [(1, 1, "\\"), (-1, -1, "\\"), (1, -1, "/"), (-1, 1, "/")]
        for dy, dx, stroke in arms:
            yy, xx = cy + dy * dist, cx + dx * dist * (2 if dy == 0 else 1)
            k = fade * (0.7 if dx and dy else 1.0)
            if 0 <= yy < rows and 0 <= xx < cols and col[yy, xx].max() < k * over:
                char[yy, xx], col[yy, xx] = C(stroke), rgb * k
    if 0 <= cy < rows and 0 <= cx < cols:
        char[cy, cx], col[cy, cx] = C("*"), rgb * 1.3 * strength


FOCAL = 3.3                                     # how much of the frame the bouquet fills
MIDDLE = 0.50                                   # where the camera's aim sits, down the frame
FOLD = 0.12                                     # a petal this far in front of its neighbour gets a stroke


def frame(t, cols, rows, cw, ch):
    (P, shade, rgb, T, K), (fx_p, fx_s, fx_t), heads, fall, info = scene(t)
    aspect = (cols * cw) / (rows * ch)
    x, y, z = look(P)
    zz = np.maximum(z, 0.2)
    sx = (0.5 + x / zz * FOCAL * 0.5 / aspect) * cols
    sy = (MIDDLE - y / zz * FOCAL * 0.5) * rows
    order = np.argsort(-z)                                      # far to near: the nearest wins each cell
    ix, iy = sx[order].astype(int), sy[order].astype(int)
    ok = (ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows) & (z[order] > 0.2)
    o = order[ok]
    ix, iy = ix[ok], iy[ok]

    part = np.full((rows, cols), -1)
    depth = np.full((rows, cols), 99.0)
    lum = np.zeros((rows, cols))
    tag = np.zeros((rows, cols), int)
    tint = np.zeros((rows, cols, 3), np.float32)
    part[iy, ix], depth[iy, ix], lum[iy, ix], tag[iy, ix], tint[iy, ix] = K[o], z[o], shade[o], T[o], rgb[o]
    body = part >= 0

    # outlines: next to empty space, or to another part further back
    pp = np.pad(part, 1, constant_values=-1)
    pd = np.pad(depth, 1, constant_values=99)
    edge = np.zeros_like(body)
    gx, gy = np.zeros((rows, cols)), np.zeros((rows, cols))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == dy == 0:
                continue
            nb = pp[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx]
            nz = pd[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx]
            other_rose = (nb // 100 != part // 100) & (nb >= 1000) & (part >= 1000) & (nz >= depth)
            out = body & ((nb < 0) | ((nb != part) & (nz > depth + FOLD)) | other_rose)
            gx += dx * out
            gy += dy * out
            if dx == 0 or dy == 0:
                edge |= out

    # letters: outline strokes, the inside filled by brightness and changing slowly
    r, c = np.mgrid[0:rows, 0:cols]
    h = (r * 7919 + c * 104729) % 9973
    level = np.clip((lum * 3.2).astype(int), 0, 3)
    inside = FILL[level, (h + (t * 4 + h % 11).astype(int)) % 12]
    sparkle = body & (tag == GLINT)
    char = np.where(body, np.where(edge, outline_letter(gx, gy), inside), 0)
    char = np.where(sparkle, C("*"), char)
    light = np.where(body, np.where(edge, np.maximum(0.85, lum), np.clip(0.45 + 0.55 * lum / 0.9, 0.45, 1.25)), 0)
    light = np.where(tag == PAPER, light * PAPER_LIGHT, np.where(tag == PAPER_IN, light * PAPER_IN_LIGHT, light))
    col = tint * light[..., None]
    steady = body.copy()

    # particles in front of the black (or of the bouquet, when they are nearer)
    if len(fx_p):
        px, py, pz = look(fx_p)
        qx = ((0.5 + px / np.maximum(pz, 0.2) * FOCAL * 0.5 / aspect) * cols).astype(int)
        qy = ((MIDDLE - py / np.maximum(pz, 0.2) * FOCAL * 0.5) * rows).astype(int)
        m = (qx >= 0) & (qx < cols) & (qy >= 0) & (qy < rows) & (fx_s > 0.04) & (pz > 0.2)
        far = (fx_t == BLOSSOM) & (body[np.clip(qy, 0, rows - 1), np.clip(qx, 0, cols - 1)]
                                   & (pz > depth[np.clip(qy, 0, rows - 1), np.clip(qx, 0, cols - 1)] + 0.01))
        m &= ~far                                               # a blossom behind a rose stays hidden
        qx, qy, pz, s, k = qx[m], qy[m], pz[m], fx_s[m], fx_t[m]
        # in front of the bouquet a star only shows while it flares, so the roses stay clean
        front = ~body[qy, qx] | ((pz < depth[qy, qx] - 0.05) & ((k == BLOSSOM) | (s > 0.6)))
        qx, qy, s, k = qx[front], qy[front], s[front], k[front]
        bloss = k == BLOSSOM
        char[qy, qx] = np.where(bloss, np.where(s > 0.8, C("*"), C("o")),
                                np.where(s > 0.7, C("*"), np.where(s > 0.35, C("+"), C("."))))
        col[qy, qx] = COLORS[k] * np.clip(np.where(bloss, s, 0.25 + s), 0, 1.3)[:, None]
        steady[qy, qx] = bloss                                  # baby's breath is part of the bouquet: no trail
        # the brightest stars throw four-pointed rays that grow and shrink with their flare
        hot = np.flatnonzero(~bloss & (s > 0.8))
        for j in hot[np.argsort(-s[hot])[:STAR_FLARES]]:
            rays(char, col, int(qy[j]), int(qx[j]), int(1 + 4 * min(s[j], 1.3) ** 2 / 1.3), COLORS[k[j]], 0.75 * min(s[j], 1.2))

    # falling petals, in the colour of the rose they came from; hidden behind anything nearer
    for pos, rose_k, pose, fade in fall:
        fx_, fy_, fz_ = look(pos[None])
        cx = int((0.5 + fx_[0] / fz_[0] * FOCAL * 0.5 / aspect) * cols)
        cy = int((MIDDLE - fy_[0] / fz_[0] * FOCAL * 0.5) * rows)
        for j, letter in enumerate(FALL_POSES[pose]):
            x_ = cx + j
            if letter and 0 <= cy < rows and 0 <= x_ < cols and (not body[cy, x_] or fz_[0] < depth[cy, x_]):
                char[cy, x_] = C(letter)
                col[cy, x_] = ROSE_COLOURS[rose_k, 0] * (1.15 * fade)
                steady[cy, x_] = False                         # tumbling: it leaves a trail

    # flares: on each rose as it starts to open, and on the brightest dew
    for (hp, f) in heads:
        if f > 0.15:
            hx, hy, hz = look(hp[None])
            cx = int((0.5 + hx[0] / hz[0] * FOCAL * 0.5 / aspect) * cols)
            cy = int((MIDDLE - hy[0] / hz[0] * FOCAL * 0.5) * rows)
            rays(char, col, cy, cx, int(3 + 5 * f), WHITE, 0.6 + 0.6 * f)
    score = np.where(sparkle, lum + (h % 7) * 0.01, 0)
    for n, idx in enumerate(np.argsort(score.ravel())[::-1][:4]):
        if score.ravel()[idx] <= 0:
            break
        cy, cx = divmod(int(idx), cols)
        rays(char, col, cy, cx, int(3 + 5 * (0.5 + 0.5 * np.sin(t * 6 + n * 1.9))), WHITE, 1.0, over=2.2)
    if T_RIBBON <= t < T_RIBBON + FLASH:                       # the knot flares as the ribbon snaps on
        kx, ky, kz = look((WAIST + [0.0, 0.0, 0.13])[None] @ spin_y(sway(t)).T)
        g = (1 - (t - T_RIBBON) / FLASH) ** 2
        rays(char, col, int((MIDDLE - ky[0] / kz[0] * FOCAL * 0.5) * rows),
             int((0.5 + kx[0] / kz[0] * FOCAL * 0.5 / aspect) * cols), int(2 + 6 * g), WHITE, 0.6 + 0.6 * g)
    if T_GLEAM[1] - 0.2 < t < T_GLEAM[1] + 0.6:                # the knot flashes as the gleam leaves it
        kx, ky, kz = look((WAIST + [0.0, 0.0, 0.13])[None] @ spin_y(sway(t)).T)
        g = np.exp(-((t - T_GLEAM[1] - 0.15) / 0.2) ** 2)
        rays(char, col, int((MIDDLE - ky[0] / kz[0] * FOCAL * 0.5) * rows),
             int((0.5 + kx[0] / kz[0] * FOCAL * 0.5 / aspect) * cols), int(2 + 5 * g), COLORS[GOLD], 0.5 + 0.7 * g)

    info["message"] = message(char, col, t, cw, ch) if t > T_MSG else None
    info["letters"] = int((char > 0).sum())
    return char, col, steady, info


PINK = np.array([1.0, 0.74, 0.86], np.float32)
LOVE_RED = np.array([1.0, 0.16, 0.30], np.float32)


MESSAGE_PX = 15                                 # the message's letter size at a frame 792 px wide (as the tree's)


def message_px(width):
    # the message is drawn bigger than the bouquet's letters: as big, for the frame, as the tree's
    return max(8, round(MESSAGE_PX * width / 792))


def message(char, col, t, cw, ch):
    # "F O R   Y O U   <3" typed out under the bouquet, ten letters a second, shimmering pink and
    # white; the <3 is red and beats, a strong beat and a soft one, like a heart. Its letters are
    # bigger than the grid's, so they are only worked out here and drawn by the Renderer; here the
    # grid under them is cleared
    rows, cols = char.shape
    _, y_, z_ = look(np.array([[0.0, BOTTOM_Y - 0.28, 0.0]], np.float32))
    row = int((MIDDLE - y_[0] / z_[0] * FOCAL * 0.5) * rows)
    size = message_px(cols * cw)
    advance = 0.6 * size                                       # px per letter, as a monospace font at that size
    x0 = (cols * cw - advance * len(MESSAGE)) / 2
    c0, c1 = int(x0 // cw) - 2, int((x0 + advance * len(MESSAGE)) // cw) + 3
    reach = int(np.ceil(0.75 * size / ch))
    char[max(row - reach, 0):row + reach + 1, max(c0, 0):c1] = 0              # a clear band behind the text
    col[max(row - reach, 0):row + reach + 1, max(c0, 0):c1] = 0
    shown = min(len(MESSAGE), int((t - T_MSG) * 10))
    love = MESSAGE.index("<3")
    ph = (t - T_MSG - love / 10 + 0.6) % 1.1
    beat = np.exp(-(ph / 0.06) ** 2) + 0.55 * np.exp(-((ph - 0.24) / 0.06) ** 2)
    letters = []
    for i, letter in enumerate(MESSAGE[:shown]):
        if letter == " ":
            continue
        new = np.clip(1 - ((t - T_MSG) * 10 - i) / 3, 0, 1)                # the newest letter is white-hot
        if i >= love:
            tint = (LOVE_RED + (WHITE - LOVE_RED) * new) * (1.0 + 0.5 * beat)
        else:
            shimmer = np.clip(np.sin(t * 2.6 - i * 0.55), 0, 1) ** 6
            tint = PINK + (WHITE - PINK) * max(new, 0.8 * shimmer)
        letters.append((letter, x0 + advance * (i + 0.5), np.clip(tint, 0, 1)))
    return {"size": size, "y": (row + 0.5) * ch, "letters": letters}


# window

TITLE = "Rose bouquet in ASCII"
CW, CH, FONT_PX = 7, 10, 11                     # small letters: each rose needs about 22 of them across
COLS, ROWS = 113, 105
W, H = COLS * CW, ROWS * CH
HINT = "Space pause · R restart · S screenshot · Esc quit"
DIM, ACCENT, SIGN = (110, 104, 120), (255, 122, 182), (176, 168, 196)
TRAIL = 0.45                                    # how much of the last frame stays behind (motion trails)
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
GREYS = [(i, i, i) for i in range(256)]
_ATLAS = {}


def glyph_atlas(cw, ch, font_px):
    # every printable character drawn into a cell: (95, ch, cw), 0..255
    if (cw, ch, font_px) not in _ATLAS:
        pygame.font.init()
        font = pygame.font.SysFont(MONO, font_px)
        cells = []
        for code in range(32, 127):
            s = pygame.Surface((cw, ch))
            g = font.render(chr(code), True, (255, 255, 255))
            s.blit(g, ((cw - g.get_width()) // 2, (ch - g.get_height()) // 2))
            cells.append(pygame.surfarray.array3d(s).transpose(1, 0, 2)[..., 0])
        _ATLAS[cw, ch, font_px] = np.stack(cells)
    return _ATLAS[cw, ch, font_px]


class Renderer:
    def __init__(self, cols=COLS, rows=ROWS, cw=CW, ch=CH, font_px=FONT_PX, hud_px=15, hint=True):
        self.cols, self.rows, self.cw, self.ch = cols, rows, cw, ch
        self.w, self.h = cols * cw, rows * ch
        self.atlas = glyph_atlas(cw, ch, font_px)               # glyph, CH, CW (grey: coloured later)
        self.art = pygame.Surface((self.w, self.h))
        self.trail = pygame.Surface((self.w, self.h))
        self.out = pygame.Surface((self.w, self.h))
        self.tint = pygame.Surface((cols, rows))
        self.moving, self.still = pygame.Surface((self.w, self.h)), pygame.Surface((self.w, self.h))
        self.small = pygame.font.SysFont(MONO, hud_px)
        self.big = pygame.font.SysFont(MONO, message_px(self.w))           # the message, bigger than the grid
        self.hud_gap = int(hud_px * 1.45)
        self.hint = hint
        self.last_t = None

    @staticmethod
    def blur(src, size, radius):
        small = pygame.transform.smoothscale(src, size)
        if hasattr(pygame.transform, "gaussian_blur"):
            small = pygame.transform.gaussian_blur(small, max(1, radius))
        return small

    def glow(self, src):
        # a tight glow and a wide one; the wide one is made from the tight one
        w, h = self.w, self.h
        tight = self.blur(src, (w // 4, h // 4), 2)
        wide = self.blur(tight, (w // 8, h // 8), 3)
        for layer, amount in ((tight, 0.75), (wide, 0.45)):
            layer = pygame.transform.smoothscale(layer, (w, h))
            layer.fill((int(255 * amount),) * 3, special_flags=pygame.BLEND_MULT)
            self.out.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def tinted(self, col, into):
        # the frame's letters (white, in self.art) in their colours
        pygame.surfarray.blit_array(self.tint, (np.clip(col, 0, 1) * 255).astype(np.uint8).transpose(1, 0, 2))
        pygame.transform.scale(self.tint, (self.w, self.h), into)
        into.blit(self.art, (0, 0), special_flags=pygame.BLEND_MULT)
        return into

    def draw(self, t):
        w, h = self.w, self.h
        char, col, steady, info = frame(t, self.cols, self.rows, self.cw, self.ch)
        grey = pygame.image.frombuffer(self.atlas[char].transpose(0, 2, 1, 3).tobytes(), (w, h), "P")
        grey.set_palette(GREYS)
        self.art.blit(grey, (0, 0))                             # the white letters, coloured by tinted()
        if self.last_t is None or t < self.last_t:
            self.trail.fill((0, 0, 0))                          # restarted: no trails from before
        self.last_t = t
        self.trail.fill((int(TRAIL * 255),) * 3, special_flags=pygame.BLEND_MULT)
        self.trail.blit(self.tinted(col * ~steady[..., None], self.moving), (0, 0), special_flags=pygame.BLEND_MAX)
        self.out.blit(self.trail, (0, 0))
        self.out.blit(self.tinted(col * steady[..., None], self.still), (0, 0), special_flags=pygame.BLEND_MAX)
        if info["message"]:                                     # drawn before the glow, so it glows too
            m = info["message"]
            for letter, x, rgb in m["letters"]:
                g = self.big.render(letter, True, tuple(int(255 * v) for v in rgb))
                self.out.blit(g, (int(x - g.get_width() / 2), int(m["y"] - g.get_height() / 2)))
        self.glow(self.out)
        first = (f"growing {info['grown'] * 100:5.1f}%" if info["grown"] < 1
                 else f"roses open {info['open']:>2}/{N_ROSES}      petals falling {info['falling']:>2}")
        lines = [first, f"letters {info['letters']:,}"]
        if self.hint:
            lines.append(HINT)
        g = self.hud_gap
        for i, text in enumerate(lines):
            self.out.blit(self.small.render(text, True, DIM), (24, h - 18 - g * (len(lines) - i)))
        self.out.blit(self.small.render(CREDIT, True, SIGN), (24, h - 18 - g * (len(lines) + 1) - g // 3))
        tt = self.small.render(f"{'●' if int(t * 2) % 2 == 0 else ' '} t {t:05.2f}s", True, ACCENT)
        self.out.blit(tt, (w - 24 - tt.get_width(), 20))
        return self.out


def window_size():
    info = pygame.display.Info()
    k = 1.0
    if info.current_w > 0 and info.current_h > 0:
        k = min(1.0, 0.88 * info.current_h / H, 0.95 * info.current_w / W)
    return int(W * k), int(H * k)


async def main():
    pygame.init()
    size = window_size()
    window = pygame.display.set_mode(size)
    pygame.display.set_caption(TITLE)
    renderer, clock = Renderer(), pygame.time.Clock()
    t, paused = 0.0, False
    screen = renderer.draw(t)
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return 0
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                paused = not paused
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                t = 0.0
            if e.type == pygame.KEYDOWN and e.key == pygame.K_s:
                pygame.image.save(screen, str(Path(__file__).with_name(f"bouquet_{int(time.time())}.png")))
        dt = clock.tick(30) / 1000
        if not paused:
            t += min(dt, 1 / 15)
            if t > LOOP:
                t = 0.0
            screen = renderer.draw(t)
        window.blit(screen if size == (W, H) else pygame.transform.smoothscale(screen, size), (0, 0))
        pygame.display.flip()
        await asyncio.sleep(0)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
