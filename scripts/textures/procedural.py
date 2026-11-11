"""
Procedural texture recipes. Every generator is wrap-around, so outputs tile seamlessly.

Style target: the hand-painted concept art (concept_art/*.jpg) - flat-lit colour,
soft painterly mottling, crisp unit edges. Albedo carries colour only (no baked sun);
relief goes in the normal map. Foliage is the exception: leaf dabs keep a little
painted under-shading, as in the concept paintings.
"""
import numpy as np
from texlib import (hex_rgb, blur, noise, normal_from_height, wrap_voronoi,
                    poisson_points, match_mean, luminance)

# tile_m = metres covered by one repeat (u, v). u runs along X of the image, v along Y (down).
RECIPES = {
    "limestone_ashlar": dict(tile_m=(3.0, 3.0), roughness=0.85, seed=11),
    "plaster_lime":     dict(tile_m=(3.0, 3.0), roughness=0.95, seed=12),
    "timber_beam":      dict(tile_m=(1.0, 1.0), roughness=0.85, seed=13),
    "plank_board":      dict(tile_m=(2.0, 2.0), roughness=0.88, seed=14),
    "dirt_road":        dict(tile_m=(4.0, 4.0), roughness=0.97, seed=15),
    "grass":            dict(tile_m=(6.0, 6.0), roughness=0.97, seed=16),
    "foliage":          dict(tile_m=(2.0, 2.0), roughness=0.9,  seed=17),
    "copper_patina":    dict(tile_m=(2.0, 2.0), roughness=0.55, seed=18),
    "cobblestone":      dict(tile_m=(3.0, 3.0), roughness=0.9,  seed=19),
    "awning_red":       dict(tile_m=(1.0, 1.0), roughness=0.9,  seed=20, stripe="#B8322B"),
    "awning_blue":      dict(tile_m=(1.0, 1.0), roughness=0.9,  seed=21, stripe="#2F5FA8"),
    "awning_yellow":    dict(tile_m=(1.0, 1.0), roughness=0.9,  seed=22, stripe="#C99A25"),
}


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def lerp_color(a, b, t):
    """t: (H,W) in [0,1]; a, b: hex colours. Returns (H,W,3)."""
    a, b = hex_rgb(a), hex_rgb(b)
    return a + (b - a) * t[..., None]


def palette_map(t, stops):
    """Map scalar field t in [0,1] through a list of (pos, hex) colour stops."""
    out = np.zeros(t.shape + (3,), np.float32)
    pos = [p for p, _ in stops]
    cols = [hex_rgb(c) for _, c in stops]
    for i in range(len(stops) - 1):
        m = (t >= pos[i]) & (t <= pos[i + 1])
        u = ((t - pos[i]) / (pos[i + 1] - pos[i] + 1e-9))[m]
        out[m] = cols[i] + (cols[i + 1] - cols[i]) * u[:, None]
    out[t < pos[0]] = cols[0]
    out[t > pos[-1]] = cols[-1]
    return out


def mottle(shape, rng, scale, amount):
    """Painterly multi-scale light/dark variation multiplier around 1.0."""
    n = noise(shape, scale, rng, octaves=3, persistence=0.55)
    return 1.0 + (n - 0.5) * 2 * amount


def per_id_random(ids, rng, n):
    vals = rng.uniform(0, 1, n).astype(np.float32)
    return vals[ids]

# ------------------------------------------------------------- generators ---

def course_layout(S, courses, blocks_per_course, rng, jitter=0.25):
    """Rectangular units in running courses (ashlar). Returns block id, distance-to-joint (px)."""
    ch = S / courses
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    course = np.minimum((yy / ch).astype(np.int32), courses - 1)
    dy = np.minimum(yy - course * ch, (course + 1) * ch - yy)
    ids = np.zeros((S, S), np.int32)
    dx = np.zeros((S, S), np.float32)
    for c in range(courses):
        w = rng.uniform(1 - jitter, 1 + jitter, blocks_per_course)
        w = w / w.sum() * S
        joints = (np.concatenate([[0], np.cumsum(w)[:-1]]) + rng.uniform(0, S)) % S
        joints.sort()
        rows = course == c
        x = xx[rows]
        d = np.abs(x[:, None] - joints[None, :])
        d = np.minimum(d, S - d)
        dx[rows] = d.min(1)
        # block index: number of joints at or left of x (wrapping)
        k = np.searchsorted(joints, x, side="right") % blocks_per_course
        ids[rows] = c * blocks_per_course + k
    return ids, np.minimum(dx, dy)


def gen_limestone_ashlar(S, rng):
    ids, edge = course_layout(S, courses=10, blocks_per_course=5, rng=rng)  # 60 x 30 cm blocks
    mortar_px = 3.0
    block_tone = per_id_random(ids, rng, ids.max() + 1)
    t = 0.25 + block_tone * 0.5 + (noise((S, S), 18, rng, octaves=3) - 0.5) * 0.45
    col = palette_map(np.clip(t, 0, 1), [(0, "#A8A08E"), (0.5, "#C4BDAE"), (1, "#D9D3C6")])
    col *= mottle((S, S), rng, 40, 0.06)[..., None]
    chisel = noise((S, S), 2.0, rng, aniso=3.0)
    col *= (0.96 + chisel * 0.08)[..., None]
    worn = smoothstep(mortar_px, mortar_px + 7, edge)            # slightly darker, worn arrises
    col *= (0.9 + 0.1 * worn)[..., None]
    mortar = smoothstep(mortar_px + 1.2, mortar_px - 0.3, edge)
    col = col * (1 - mortar[..., None]) + hex_rgb("#B3AA97") * mortar[..., None]
    h = worn * 0.85 + chisel * 0.15
    return col, normal_from_height(h, 5.0)


def gen_plaster_lime(S, rng):
    base = noise((S, S), 60, rng, octaves=4, persistence=0.6)
    col = palette_map(base, [(0, "#C2BBAC"), (0.5, "#D8D2C5"), (1, "#E6E1D6")])
    streak = noise((S, S), 6, rng, aniso=0.15, octaves=2)          # vertical limewash brushing
    col *= (0.97 + streak * 0.06)[..., None]
    # sparse hairline cracks from Voronoi cell borders, masked to a few regions
    pts = rng.uniform(0, S, (40, 2)).astype(np.float32)
    d1, d2, _ = wrap_voronoi((S, S), pts)
    crack = smoothstep(1.4, 0.0, d2 - d1) * smoothstep(0.62, 0.72, noise((S, S), 70, rng))
    col *= (1 - crack * 0.25)[..., None]
    h = blur(base, 2) * 0.6 + noise((S, S), 1.5, rng) * 0.4 - crack * 0.5
    return col, normal_from_height(h, 2.0)


def wood_grain(S, rng, along_x=True, rings=24.0):
    """Long fibrous grain: strongly anisotropic noise plus warped ring bands."""
    an = 25.0 if along_x else 1 / 25.0
    fib = noise((S, S), 1.6, rng, aniso=an, octaves=2)
    warp = noise((S, S), 40, rng, aniso=an * 0.3 if along_x else an * 3, octaves=2)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    coord = (yy if along_x else xx) / S
    bands = 0.5 + 0.5 * np.sin(2 * np.pi * (coord * rings + (warp - 0.5) * 3.0))
    return fib, bands


def gen_timber_beam(S, rng):
    fib, bands = wood_grain(S, rng, along_x=True, rings=10)
    t = np.clip(0.5 + (fib - 0.5) * 1.3 + (bands - 0.5) * 0.25, 0, 1)
    col = palette_map(t, [(0, "#2E241A"), (0.5, "#4A3B2C"), (1, "#66513C")])
    # drying checks: a few long thin dark cracks along the grain
    cracks = smoothstep(0.80, 0.86, noise((S, S), 3, rng, aniso=60))
    col *= (1 - cracks * 0.45)[..., None]
    col *= mottle((S, S), rng, 80, 0.05)[..., None]
    h = fib * 0.6 + bands * 0.2 - cracks * 0.6
    return col, normal_from_height(h, 4.0)


def gen_plank_board(S, rng):
    boards = 10                                                     # 20 cm boards over 2 m
    bw = S / boards
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    bid = (xx / bw).astype(np.int32) % boards
    gap = np.minimum(xx - bid * bw, (bid + 1) * bw - xx)
    fib, bands = wood_grain(S, rng, along_x=False, rings=6)
    tone = per_id_random(bid, rng, boards)
    t = np.clip(0.35 + (fib - 0.5) * 1.1 + (bands - 0.5) * 0.2 + (tone - 0.5) * 0.35, 0, 1)
    col = palette_map(t, [(0, "#4A3A2A"), (0.5, "#6A5440"), (1, "#86704F")])
    groove = smoothstep(2.5, 0.5, gap)
    col *= (1 - groove * 0.65)[..., None]
    # wooden pegs / nail heads near two cross battens
    for yc in (S * 0.18, S * 0.68):
        for b in range(boards):
            cx = (b + 0.5) * bw + rng.uniform(-4, 4)
            r = np.sqrt((xx - cx) ** 2 + (yy - yc - rng.uniform(-3, 3)) ** 2)
            col *= (1 - smoothstep(4.5, 2.5, r) * 0.5)[..., None]
    h = (1 - groove) * 0.7 + fib * 0.3
    return col, normal_from_height(h, 4.0)


def gen_dirt_road(S, rng):
    base = noise((S, S), 50, rng, octaves=4, persistence=0.6)
    col = palette_map(base, [(0, "#5E503F"), (0.5, "#7A6A53"), (1, "#8C7B65")])
    # Painterly speckle at 2-4 px so it survives mipmapping (1 px grain just averages out).
    speck = noise((S, S), 2.2, rng, octaves=2)
    col *= (0.84 + speck * 0.32)[..., None]
    dark = smoothstep(0.62, 0.70, noise((S, S), 3.5, rng))          # damp clods
    col *= (1 - dark * 0.18)[..., None]
    pts = poisson_points((S, S), 22, rng, tries=1500)
    d1, d2, idx = wrap_voronoi((S, S), pts)
    size = per_id_random(idx, rng, len(pts)) * 3.5 + 1.5
    pebble = smoothstep(size, size - 1.5, d1) * (per_id_random(idx, rng, len(pts)) > 0.45)
    col = col * (1 - pebble[..., None] * 0.6) + hex_rgb("#9A9080") * pebble[..., None] * 0.6
    h = blur(base, 3) * 0.5 + pebble * 0.5 + speck * 0.2
    return col, normal_from_height(h, 3.0)


def gen_grass(S, rng):
    # Broad patches kept low-contrast so they don't read as camouflage blobs.
    patches = noise((S, S), 90, rng, octaves=3, persistence=0.5)
    patches = 0.5 + (patches - 0.5) * 0.6
    col = palette_map(patches, [(0, "#414B29"), (0.45, "#556236"), (1, "#6E7845")])
    # Short brush strokes (taller than wide) at a few px, the way the concept art dabs grass.
    blades = noise((S, S), 1.8, rng, aniso=0.35, octaves=2)
    col *= (0.80 + blades * 0.40)[..., None]
    # Scattered darker tufts with a lighter crown.
    pts = poisson_points((S, S), 26, rng, tries=2500)
    d1, _, idx = wrap_voronoi((S, S), pts)
    r = per_id_random(idx, rng, len(pts)) * 4 + 3
    keep = per_id_random(idx, rng, len(pts)) > 0.35
    tuft = smoothstep(r, r * 0.4, d1) * keep
    col = col * (1 - tuft[..., None] * 0.30)
    dry = smoothstep(0.66, 0.78, noise((S, S), 35, rng, octaves=2))  # sun-dried patches
    col = col * (1 - dry[..., None] * 0.3) + hex_rgb("#7E7A4E") * dry[..., None] * 0.3
    h = blades * 0.6 + tuft * 0.4
    return col, normal_from_height(h, 3.0)


def gen_foliage(S, rng):
    col = np.zeros((S, S, 3), np.float32) + hex_rgb("#2C3A1B")
    hgt = np.zeros((S, S), np.float32)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    # Painted leaf dabs: layered back-to-front, each lighter toward the upper-left.
    clump = noise((S, S), 60, rng, octaves=2)
    for _ in range(2600):
        cy, cx = rng.uniform(0, S, 2)
        r = rng.uniform(7, 13)
        y0, y1 = int(cy - r - 1), int(cy + r + 2)
        x0, x1 = int(cx - r - 1), int(cx + r + 2)
        ys = np.arange(y0, y1) % S
        xs = np.arange(x0, x1) % S
        dy = (np.arange(y0, y1) - cy)[:, None]
        dx = (np.arange(x0, x1) - cx)[None, :]
        d = np.sqrt(dx * dx + (dy * 1.15) ** 2) / r
        m = d < 1.0
        shade = np.clip(0.55 - 0.35 * (dx + dy) / r * 0.5 - d * 0.25, 0, 1)
        tone = clump[int(cy) % S, int(cx) % S]
        leaf = palette_map(np.clip(shade * 0.7 + tone * 0.45, 0, 1),
                           [(0, "#33461F"), (0.5, "#55682F"), (1, "#7A9145")])
        sub = col[np.ix_(ys, xs)]
        sub[m] = leaf[m]
        col[np.ix_(ys, xs)] = sub
        hs = hgt[np.ix_(ys, xs)]
        hs[m] = np.sqrt(1 - d[m] ** 2)
        hgt[np.ix_(ys, xs)] = hs
    return col, normal_from_height(blur(hgt, 1.0), 4.0)


def gen_copper_patina(S, rng):
    base = noise((S, S), 30, rng, octaves=3)
    streaks = noise((S, S), 3, rng, aniso=0.06, octaves=2)            # rain streaks run down
    t = np.clip(base * 0.6 + streaks * 0.6 - 0.1, 0, 1)
    col = palette_map(t, [(0, "#2A5A50"), (0.5, "#4E8F80"), (1, "#7DB3A2")])
    bronze = smoothstep(0.74, 0.86, noise((S, S), 12, rng, octaves=2))  # sparse, small
    col = col * (1 - bronze[..., None] * 0.35) + hex_rgb("#5E5A3E") * bronze[..., None] * 0.35
    h = base * 0.5 + streaks * 0.5
    return col, normal_from_height(h, 1.5)


def gen_cobblestone(S, rng):
    pts = poisson_points((S, S), 46, rng, tries=24000)               # ~16 cm stones at 3 m/tile
    warp_y = (noise((S, S), 25, rng) - 0.5) * 18
    warp_x = (noise((S, S), 25, rng) - 0.5) * 18
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    # Domain-warp the Voronoi lookup so stones are rounded and irregular, not polygonal.
    d1, d2, idx = wrap_voronoi((S, S), pts)
    d1w = blur(d1, 0.8); edge = blur(d2 - d1, 1.0)
    edge = edge + warp_x * 0.25 + warp_y * 0.25
    stone = smoothstep(4.0, 9.0, edge)                                # earth-packed gaps ~2-3 cm
    dome = np.clip(edge / 22.0, 0, 1) ** 0.6
    tone = per_id_random(idx, rng, len(pts))
    t = np.clip(0.2 + tone * 0.6 + (noise((S, S), 6, rng, octaves=2) - 0.5) * 0.35, 0, 1)
    stone_col = palette_map(t, [(0, "#7A7466"), (0.5, "#8F887A"), (1, "#ABA393")])
    stone_col *= (0.92 + dome * 0.14)[..., None]                     # painterly crown highlight
    earth = palette_map(noise((S, S), 12, rng, octaves=3),
                        [(0, "#4F4334"), (0.5, "#64553F"), (1, "#7A6A53")])
    col = earth * (1 - stone[..., None]) + stone_col * stone[..., None]
    h = stone * dome
    _ = d1w
    return col, normal_from_height(blur(h, 1.0), 9.0)


def gen_awning(S, rng, stripe_hex):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    stripes = 4                                                       # 25 cm stripes over 1 m
    s = ((xx / (S / stripes)).astype(np.int32) % 2).astype(np.float32)
    soft = blur(s, 1.2)
    col = lerp_color("#E4DCC8", stripe_hex, soft)
    weave = (np.sin(xx * 2 * np.pi / 3.0) * np.sin(yy * 2 * np.pi / 3.0)) * 0.5 + 0.5
    col *= (0.94 + weave * 0.06)[..., None]
    fade = mottle((S, S), rng, 70, 0.07)                              # sun fading, grime
    col *= fade[..., None]
    h = weave * 0.6 + noise((S, S), 30, rng) * 0.4
    return col, normal_from_height(h, 1.5)


GENERATORS = {
    "limestone_ashlar": gen_limestone_ashlar,
    "plaster_lime": gen_plaster_lime,
    "timber_beam": gen_timber_beam,
    "plank_board": gen_plank_board,
    "dirt_road": gen_dirt_road,
    "grass": gen_grass,
    "foliage": gen_foliage,
    "copper_patina": gen_copper_patina,
    "cobblestone": gen_cobblestone,
}


def build(fid, recipe, size):
    rng = np.random.default_rng(recipe["seed"])
    if fid.startswith("awning_"):
        col, nrm = gen_awning(size, rng, recipe["stripe"])
    else:
        col, nrm = GENERATORS[fid](size, rng)
    return np.clip(col, 0, 1).astype(np.float32), nrm
