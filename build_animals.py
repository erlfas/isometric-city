#!/usr/bin/env python3
"""
Procedural wildlife models: Lublin Anno Domini 1392
Red deer (stag, hind, fawn) and mallards (drake, duck, duckling) for the Bystrzyca's banks,
drawn and animated by src/engine/wildlife.ts; the stable's horses (palfrey, draught horse, with
tack parts) by src/engine/horses.ts. One GLB per animal, public/models/animal_<name>.glb.

  blender --background --factory-startup --python build_animals.py [-- animal_deer_stag ...]

Format (like the citizen kits, build_characters.py): one mesh object per rigid part, extras
"part" = part name, no node transforms (check_models.py), and scene extras "animal" = JSON
{"pivots": {part: [x, y, z]}, "tags": {tack part: bit}} in glTF coordinates (y up, the animal faces +z). wildlife.ts
merges the parts into one geometry per animal (vertex colour from the material, part id per
vertex) and swings each part about its pivot in the vertex shader; the part hierarchy
(head on neck, shin on thigh, ear on head) and the pose channels live there.

Authoring frame here = glTF frame: x = the animal's left, y = up, z = forward, metres; V()
converts to Blender (Z up, facing -Y) for the shared primitives of build_characters.py.
Waterline of the ducks = y 0 (they float with it at the water surface).
"""

import os
import sys
import json

import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_characters as bc  # noqa: E402  (primitives, create_mat; its main() does not run)

OUTPUT_DIR = "public/models"


def V(p, s=1.0):
    x, y, z = p
    return (x * s, -z * s, y * s)


class Model:
    def __init__(self, name, scale=1.0):
        self.name = name
        self.s = scale
        self.parts = {}
        self.pivots = {}
        self.mats = []
        self.mat_idx = {}

    def bm(self, part):
        if part not in self.parts:
            self.parts[part] = bmesh.new()
        return self.parts[part]

    def mat(self, key, color, roughness=0.85):
        if key not in self.mat_idx:
            rgb = bc.srgb_hex(color)
            self.mat_idx[key] = len(self.mats)
            self.mats.append(bc.create_mat(f"Animal_{self.name}_{key}", rgb, roughness=roughness))
        return self.mat_idx[key]

    def pivot(self, part, p):
        self.pivots[part] = [round(c * self.s, 4) for c in p]

    # primitives in the authoring frame, scaled by the model's scale
    def tube(self, part, pts, mat, segs=8, cap0=True, cap1=True):
        s = self.s
        bc.add_tube(self.bm(part), [(V(p, s), rs * s, rf * s) for p, rs, rf in pts], segs=segs,
                    mat_idx=mat, cap0=cap0, cap1=cap1)

    def ell(self, part, c, r, mat, segs=8, rings=5):
        s = self.s
        rx, ry, rz = r
        bc.add_ellipsoid(self.bm(part), V(c, s), (rx * s, rz * s, ry * s), segs=segs, rings=rings, mat_idx=mat)

    def box(self, part, c, size, mat):
        """Axis-aligned box: centre c, size (x width, y height, z length)."""
        s = self.s
        sx, sy, sz = size
        bc.add_box(self.bm(part), *V(c, s), sx * s, sz * s, sy * s, mat_idx=mat)

    def sheet(self, part, rings, mat, mat_in=None, closed=False):
        """Surface through rings of points (same count each), quads between neighbours; mat_in
        adds the inside (reversed faces) in its own material. closed: last ring point joins the first."""
        bm = self.bm(part)
        vs = [[bm.verts.new(Vector(V(p, self.s))) for p in r] for r in rings]
        n = len(rings[0])
        for a, b in zip(vs, vs[1:]):
            for k in range(n if closed else n - 1):
                q = (a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])
                f = bm.faces.new(q)
                f.material_index = mat
                if mat_in is not None:
                    g = bm.faces.new(tuple(reversed([bm.verts.new(v.co) for v in q])))
                    g.material_index = mat_in


def mirror(fn):
    for sx, side in ((1, "L"), (-1, "R")):
        fn(sx, side)


# ------------------------------------------------------------------ red deer

DEER = {
    # coat, darker neck/mane, pale belly, rump patch
    "stag": dict(scale=1.0, coat="#7c4529", mane="#4e3220", belly="#a77c58", rump="#c7a77c", neck=1.25, antlers=True),
    "hind": dict(scale=0.88, coat="#8c5434", mane="#6e4228", belly="#b48a64", rump="#cfb088", neck=0.9, antlers=False),
    "fawn": dict(scale=0.6, coat="#a1633a", mane="#8a5432", belly="#c8a47a", rump="#d4b88e", neck=0.85, antlers=False,
                 spots=True),
}


def build_deer(name, cfg):
    m = Model(name, cfg["scale"])
    coat = m.mat("coat", cfg["coat"])
    mane = m.mat("mane", cfg["mane"])
    belly = m.mat("belly", cfg["belly"])
    rump = m.mat("rump", cfg["rump"])
    dark = m.mat("dark", "#1e1813", roughness=0.5)
    hoof = m.mat("hoof", "#2c241d", roughness=0.6)
    fawn = name.endswith("fawn")
    nk = cfg["neck"]

    # Body: barrel from rump to chest, deep at the chest, tucked at the flank.
    m.tube("body", [((0, 1.00, -0.80), 0.06, 0.08), ((0, 1.01, -0.72), 0.16, 0.21), ((0, 0.99, -0.45), 0.205, 0.27),
                    ((0, 0.97, -0.05), 0.225, 0.29), ((0, 0.99, 0.30), 0.215, 0.31), ((0, 1.03, 0.55), 0.17, 0.27),
                    ((0, 1.07, 0.66), 0.08, 0.13)], coat, segs=10)
    # Pale belly and the rump patch (slightly proud of the coat).
    m.tube("body", [((0, 0.78, -0.35), 0.15, 0.08), ((0, 0.74, 0.0), 0.17, 0.09), ((0, 0.76, 0.3), 0.15, 0.08)],
           belly, segs=8)
    m.ell("body", (0, 1.03, -0.745), (0.11, 0.14, 0.06), rump, segs=8, rings=5)
    if cfg.get("spots"):
        import math
        for k in range(14):
            z = -0.5 + (k % 7) * 0.15
            sx = 1 if k < 7 else -1
            th = math.radians(38 + (k * 23) % 30)
            rs, rf, yc = 0.22, 0.29, 0.98
            m.ell("body", (sx * rs * math.cos(th) * 0.97, yc + rf * math.sin(th) * 0.97, z), (0.035, 0.03, 0.04),
                  m.mat("spot", "#efe2c0"), segs=6, rings=3)

    # Neck (pivot low in the chest) and head (pivot at the top of the neck).
    m.pivot("neck", (0, 1.05, 0.48))
    m.tube("neck", [((0, 1.0, 0.46), 0.14 * nk, 0.2 * nk), ((0, 1.22, 0.62), 0.12 * nk, 0.15 * nk),
                    ((0, 1.42, 0.76), 0.08, 0.1), ((0, 1.52, 0.82), 0.07, 0.085)], mane if nk > 1 else coat, segs=8)
    if nk > 1:  # stag's shaggy throat mane
        m.tube("neck", [((0, 1.02, 0.6), 0.1, 0.1), ((0, 1.18, 0.74), 0.12, 0.11), ((0, 1.36, 0.84), 0.07, 0.07)],
               mane, segs=6)
    m.pivot("head", (0, 1.5, 0.8))
    hs = 1.18 if fawn else 1.0  # fawns: bigger head and ears for their size
    m.ell("head", (0, 1.56, 0.87), (0.085 * hs, 0.095 * hs, 0.12 * hs), coat, segs=10, rings=6)
    m.tube("head", [((0, 1.57, 0.9), 0.07 * hs, 0.075 * hs), ((0, 1.53, 1.02), 0.055 * hs, 0.06 * hs),
                    ((0, 1.48, 1.13), 0.04 * hs, 0.045 * hs)], coat, segs=8)
    m.ell("head", (0, 1.475, 1.14), (0.038 * hs, 0.03 * hs, 0.025 * hs), dark, segs=6, rings=4)   # nose
    m.tube("head", [((0, 1.47, 0.95), 0.05, 0.03), ((0, 1.47, 1.08), 0.035, 0.02)], belly, segs=6)  # pale chin
    for sx in (1, -1):
        m.ell("head", (sx * 0.072 * hs, 1.59, 0.93), (0.016, 0.02, 0.022), dark, segs=6, rings=4)  # eyes

    def ear(sx, side):
        part = "ear_" + side
        e = 1.3 if fawn else 1.0
        m.pivot(part, (sx * 0.06, 1.63, 0.83))
        m.tube(part, [((sx * 0.055, 1.62, 0.83), 0.022 * e, 0.018 * e), ((sx * 0.12, 1.69, 0.82), 0.04 * e, 0.014 * e),
                      ((sx * (0.12 + 0.05 * e), 1.70 + 0.06 * e, 0.81), 0.006, 0.004)], coat, segs=6)
    mirror(ear)

    if cfg["antlers"]:
        base = m.mat("antler", "#6f5b40", roughness=0.7)
        tip = m.mat("antler_tip", "#e2d6b8", roughness=0.6)

        def antler(sx, side):
            r = 0.028
            beam = [((sx * 0.05, 1.66, 0.85), r, r), ((sx * 0.15, 1.82, 0.81), r * 0.9, r * 0.9),
                    ((sx * 0.25, 2.02, 0.74), r * 0.8, r * 0.8), ((sx * 0.31, 2.22, 0.66), r * 0.7, r * 0.7),
                    ((sx * 0.29, 2.38, 0.64), r * 0.55, r * 0.55)]
            m.tube("head", beam, base, segs=5)
            m.tube("head", [((sx * 0.29, 2.38, 0.64), r * 0.55, r * 0.55), ((sx * 0.24, 2.5, 0.7), 0.006, 0.006)], tip, segs=5)
            m.tube("head", [((sx * 0.29, 2.36, 0.64), r * 0.5, r * 0.5), ((sx * 0.37, 2.47, 0.6), 0.006, 0.006)], tip, segs=5)
            for (a, b) in [(((sx * 0.08, 1.71, 0.85), ), ((sx * 0.12, 1.78, 1.03), )),       # brow tine
                           (((sx * 0.13, 1.79, 0.82), ), ((sx * 0.17, 1.88, 0.98), )),       # bez tine
                           (((sx * 0.27, 2.08, 0.72), ), ((sx * 0.32, 2.2, 0.88), ))]:       # trez tine
                m.tube("head", [(a[0], r * 0.7, r * 0.7), (b[0], 0.006, 0.006)], tip, segs=5)
        mirror(antler)

    # Legs: upper (shoulder/thigh to knee/hock), lower (to the hoof) hung from it.
    def legs(sx, side):
        x = sx * 0.12
        f, h = "F" + side, "B" + side
        m.pivot("legU_" + f, (x, 0.88, 0.42))
        m.tube("legU_" + f, [((x, 0.98, 0.42), 0.075, 0.12), ((x * 0.95, 0.7, 0.44), 0.055, 0.075),
                             ((x * 0.92, 0.46, 0.45), 0.038, 0.045)], coat, segs=7)
        m.pivot("legL_" + f, (x * 0.92, 0.46, 0.45))
        m.tube("legL_" + f, [((x * 0.92, 0.47, 0.45), 0.037, 0.043), ((x * 0.92, 0.1, 0.45), 0.024, 0.026),
                             ((x * 0.92, 0.035, 0.465), 0.03, 0.035)], coat, segs=6)
        m.tube("legL_" + f, [((x * 0.92, 0.05, 0.465), 0.03, 0.036), ((x * 0.92, 0.0, 0.485), 0.032, 0.04)], hoof, segs=6)
        m.pivot("legU_" + h, (x, 0.92, -0.52))
        m.tube("legU_" + h, [((x * 1.05, 1.0, -0.5), 0.1, 0.17), ((x, 0.68, -0.48), 0.07, 0.1),
                             ((x * 0.92, 0.42, -0.62), 0.038, 0.05)], coat, segs=7)
        m.pivot("legL_" + h, (x * 0.92, 0.42, -0.62))
        m.tube("legL_" + h, [((x * 0.92, 0.44, -0.63), 0.037, 0.05), ((x * 0.92, 0.1, -0.56), 0.024, 0.026),
                             ((x * 0.92, 0.035, -0.545), 0.03, 0.035)], coat, segs=6)
        m.tube("legL_" + h, [((x * 0.92, 0.05, -0.545), 0.03, 0.036), ((x * 0.92, 0.0, -0.525), 0.032, 0.04)], hoof, segs=6)
    mirror(legs)

    m.pivot("tail", (0, 1.06, -0.77))
    m.tube("tail", [((0, 1.07, -0.77), 0.045, 0.035), ((0, 0.98, -0.83), 0.04, 0.03), ((0, 0.9, -0.84), 0.02, 0.015)],
           mane, segs=6)
    return m


# ------------------------------------------------------------------ mallards

DUCKS = {
    "drake": dict(scale=1.0),
    "hen": dict(scale=0.95),
}


def build_duck(name, sex, scale):
    m = Model(name, scale)
    drake = sex == "drake"
    flank = m.mat("flank", "#b4b0a6" if drake else "#8e6c48")
    back = m.mat("back", "#6c665a" if drake else "#6a4e34")
    breast = m.mat("breast", "#6e3a24" if drake else "#8a6644")
    wing = m.mat("wing", "#857c6c" if drake else "#74583c")
    spec = m.mat("speculum", "#3449a0", roughness=0.4)
    white = m.mat("white", "#ece9e0")
    black = m.mat("black", "#1a1918", roughness=0.6)
    head_c = m.mat("head", "#1d5a38" if drake else "#7e5c3c", roughness=0.45 if drake else 0.85)
    crown = m.mat("crown", "#1a4a30" if drake else "#4a3424")
    bill = m.mat("bill", "#d6b23c" if drake else "#c27a32", roughness=0.5)

    # Boat-shaped body, waterline at y = 0.
    m.tube("body", [((0, 0.10, -0.30), 0.015, 0.012), ((0, 0.075, -0.24), 0.075, 0.05), ((0, 0.04, -0.12), 0.125, 0.085),
                    ((0, 0.035, 0.04), 0.13, 0.09), ((0, 0.05, 0.15), 0.11, 0.09), ((0, 0.07, 0.22), 0.07, 0.07),
                    ((0, 0.085, 0.255), 0.025, 0.025)], flank, segs=10)
    m.tube("body", [((0, 0.08, 0.06), 0.1, 0.08), ((0, 0.075, 0.17), 0.095, 0.08), ((0, 0.085, 0.235), 0.055, 0.06)],
           breast, segs=8)
    m.tube("body", [((0, 0.11, -0.2), 0.05, 0.03), ((0, 0.12, -0.02), 0.08, 0.035), ((0, 0.11, 0.1), 0.06, 0.03)],
           back, segs=8)
    if drake:  # black rear with white tail and the curled tail feathers
        m.ell("body", (0, 0.085, -0.25), (0.06, 0.055, 0.06), black, segs=8, rings=5)
        m.tube("body", [((0, 0.1, -0.28), 0.04, 0.012), ((0, 0.115, -0.34), 0.03, 0.008), ((0, 0.12, -0.37), 0.005, 0.004)],
               white, segs=6)
        m.tube("body", [((0, 0.13, -0.27), 0.008, 0.008), ((0, 0.17, -0.27), 0.008, 0.008), ((0, 0.175, -0.24), 0.004, 0.004)],
               black, segs=4)
    else:
        m.tube("body", [((0, 0.1, -0.27), 0.045, 0.012), ((0, 0.11, -0.34), 0.03, 0.008), ((0, 0.115, -0.37), 0.005, 0.004)],
               back, segs=6)

    def wings(sx, side):
        part = "wing_" + side
        m.pivot(part, (sx * 0.08, 0.12, 0.1))
        m.tube(part, [((sx * 0.085, 0.12, 0.12), 0.03, 0.02), ((sx * 0.105, 0.125, 0.0), 0.045, 0.025),
                      ((sx * 0.095, 0.125, -0.14), 0.04, 0.02), ((sx * 0.06, 0.13, -0.25), 0.012, 0.008)], wing, segs=6)
        m.tube(part, [((sx * 0.128, 0.115, -0.04), 0.012, 0.02), ((sx * 0.124, 0.115, -0.12), 0.012, 0.018)], spec, segs=4)
        m.tube(part, [((sx * 0.121, 0.112, -0.135), 0.012, 0.012), ((sx * 0.112, 0.11, -0.16), 0.008, 0.008)], white, segs=4)
    mirror(wings)

    m.pivot("head", (0, 0.1, 0.2))
    m.tube("head", [((0, 0.08, 0.2), 0.048, 0.05), ((0, 0.16, 0.215), 0.038, 0.04), ((0, 0.23, 0.235), 0.034, 0.038)],
           head_c if drake else flank, segs=8)
    if drake:
        m.tube("head", [((0, 0.14, 0.212), 0.041, 0.043), ((0, 0.152, 0.214), 0.041, 0.043)], white, segs=8)
    m.ell("head", (0, 0.27, 0.245), (0.045, 0.048, 0.062), head_c, segs=10, rings=6)
    m.ell("head", (0, 0.295, 0.24), (0.03, 0.025, 0.045), crown, segs=8, rings=4)
    m.tube("head", [((0, 0.262, 0.29), 0.022, 0.013), ((0, 0.25, 0.33), 0.021, 0.009), ((0, 0.242, 0.365), 0.017, 0.007)],
           bill, segs=6)
    for sx in (1, -1):
        m.ell("head", (sx * 0.04, 0.282, 0.262), (0.009, 0.009, 0.009), black, segs=6, rings=4)
    return m


def build_duckling(name):
    m = Model(name, 1.0)
    down = m.mat("down", "#5a4630")
    pale = m.mat("pale", "#d6bf72")
    bill = m.mat("bill", "#3a3026", roughness=0.6)
    black = m.mat("black", "#151312", roughness=0.6)
    m.ell("body", (0, 0.035, 0.0), (0.06, 0.05, 0.085), down, segs=10, rings=6)
    m.ell("body", (0, 0.025, 0.02), (0.055, 0.035, 0.07), pale, segs=8, rings=5)
    m.ell("body", (0.05, 0.05, -0.005), (0.014, 0.022, 0.03), pale, segs=6, rings=4)
    m.ell("body", (-0.05, 0.05, -0.005), (0.014, 0.022, 0.03), pale, segs=6, rings=4)
    m.pivot("head", (0, 0.06, 0.06))
    m.tube("head", [((0, 0.05, 0.06), 0.03, 0.03), ((0, 0.09, 0.07), 0.026, 0.026)], down, segs=6)
    m.ell("head", (0, 0.11, 0.078), (0.034, 0.034, 0.038), pale, segs=8, rings=6)
    m.ell("head", (0, 0.13, 0.072), (0.027, 0.02, 0.032), down, segs=8, rings=4)
    m.tube("head", [((0, 0.105, 0.108), 0.012, 0.007), ((0, 0.1, 0.13), 0.009, 0.005)], bill, segs=5)
    for sx in (1, -1):
        m.ell("head", (sx * 0.028, 0.115, 0.095), (0.006, 0.006, 0.006), black, segs=5, rings=3)
    return m


# ------------------------------------------------------------------ horses

# Palfrey ~1.45 m at the withers; the draught horse is scaled up and built heavier. Coat and
# points (mane, tail, lower legs) are recoloured per instance at runtime (horses.ts): materials
# named *_coat and *_points take the instance colours, everything else keeps its own.
HORSES = {
    "horse": dict(scale=1.0, wide=1.0, deep=1.0, leg=1.0, neck=1.0, head=1.0, feather=False),
    "horse_draught": dict(scale=1.07, wide=1.16, deep=1.07, leg=1.32, neck=1.2, head=1.1, feather=True),
}

# Tack parts: bit in the instance's tack mask (horses.ts TACK) that shows them.
TACK_BITS = {"saddle": 1, "bridle": 2, "reins": 2, "halter": 4, "lead": 8, "collar": 16, "harness": 16}


def build_horse(name, cfg):
    import math
    m = Model(name, cfg["scale"])
    coat = m.mat("coat", "#7a4a2a")
    pts = m.mat("points", "#211812")
    muzzle = m.mat("muzzle", "#3a3230", roughness=0.6)
    dark = m.mat("dark", "#141110", roughness=0.4)
    hoof = m.mat("hoof", "#3b332c", roughness=0.6)
    leather = m.mat("leather", "#5a3a22", roughness=0.6)
    cloth = m.mat("cloth", "#7c2a22")
    iron = m.mat("iron", "#5c5a56", roughness=0.45)
    rope = m.mat("rope", "#a88c62")
    pad = m.mat("pad", "#8a6a44", roughness=0.7)
    W, D, L, N, H = cfg["wide"], cfg["deep"], cfg["leg"], cfg["neck"], cfg["head"]

    def loop(part, c, a, b, ra, rb, r, mat, n=12, arc=(0.0, 1.0)):
        """Strap: a tube through n points on the ellipse c + a*cos*ra + b*sin*rb (closed if arc is full)."""
        p = []
        full = arc == (0.0, 1.0)
        steps = n if full else n - 1
        for i in range(n + (1 if full else 0)):
            t = (arc[0] + (arc[1] - arc[0]) * (i % n if full else i) / steps) * math.tau
            p.append(((c[0] + a[0] * math.cos(t) * ra + b[0] * math.sin(t) * rb,
                       c[1] + a[1] * math.cos(t) * ra + b[1] * math.sin(t) * rb,
                       c[2] + a[2] * math.cos(t) * ra + b[2] * math.sin(t) * rb), r, r))
        m.tube(part, p, mat, segs=4, cap0=not full, cap1=not full)

    # Body: barrel from the buttock to the chest; withers and croup on top.
    m.tube("body", [((0, 1.20, -0.84), 0.08 * W, 0.10 * D), ((0, 1.17, -0.76), 0.20 * W, 0.26 * D),
                    ((0, 1.13, -0.56), 0.27 * W, 0.33 * D), ((0, 1.10, -0.25), 0.29 * W, 0.34 * D),
                    ((0, 1.10, 0.10), 0.29 * W, 0.35 * D), ((0, 1.12, 0.40), 0.26 * W, 0.34 * D),
                    ((0, 1.14, 0.58), 0.19 * W, 0.27 * D), ((0, 1.16, 0.68), 0.08 * W, 0.12 * D)], coat, segs=12)
    m.ell("body", (0, 1.40, 0.36), (0.11 * W, 0.08, 0.2), coat, segs=8, rings=5)       # withers
    for sx in (1, -1):  # croup and shoulder: just proud of the barrel, not balls on it
        m.ell("body", (sx * 0.09 * W, 1.29, -0.55), (0.17 * W, 0.17 * D, 0.25), coat, segs=8, rings=5)
        m.ell("body", (sx * 0.12 * W, 1.12, 0.42), (0.135 * W, 0.22 * D, 0.15), coat, segs=8, rings=5)

    # Neck in two parts (pivot low in the chest, so the muzzle reaches the grass, and half way
    # up), the mane along its crest; head on the upper neck, jaw on the head.
    m.pivot("neck", (0, 1.05, 0.50))
    m.tube("neck", [((0, 1.12, 0.44), 0.2 * N, 0.31 * N), ((0, 1.38, 0.68), 0.15 * N, 0.25 * N),
                    ((0, 1.47, 0.76), 0.14 * N, 0.225 * N)], coat, segs=10)
    m.tube("neck", [((0, 1.46, 0.38), 0.03, 0.03), ((0, 1.57, 0.52), 0.045 * N, 0.08 * N),
                    ((0, 1.66, 0.63), 0.043 * N, 0.08 * N)], pts, segs=6)
    m.pivot("neck2", (0, 1.38, 0.68))
    m.tube("neck2", [((0, 1.30, 0.61), 0.155 * N, 0.26 * N), ((0, 1.60, 0.85), 0.11 * N, 0.17 * N),
                     ((0, 1.76, 0.95), 0.085 * N, 0.12 * N)], coat, segs=10)
    m.tube("neck2", [((0, 1.62, 0.58), 0.043 * N, 0.08 * N), ((0, 1.72, 0.70), 0.04 * N, 0.08 * N),
                     ((0, 1.87, 0.88), 0.03, 0.04)], pts, segs=6)
    m.pivot("head", (0, 1.78, 0.95))
    m.tube("head", [((0, 1.84, 0.93), 0.08 * H, 0.10 * H), ((0, 1.76, 1.02), 0.10 * H, 0.12 * H),
                    ((0, 1.62, 1.13), 0.08 * H, 0.09 * H), ((0, 1.50, 1.22), 0.065 * H, 0.075 * H),
                    ((0, 1.43, 1.28), 0.06 * H, 0.065 * H)], coat, segs=10)
    m.ell("head", (0, 1.415, 1.29), (0.066 * H, 0.06 * H, 0.06 * H), muzzle, segs=8, rings=5)
    m.ell("head", (0, 1.70, 1.0), (0.085 * H, 0.1 * H, 0.1 * H), coat, segs=8, rings=5)   # cheek
    m.tube("head", [((0, 1.88, 0.94), 0.04, 0.02), ((0, 1.80, 1.04), 0.05, 0.02), ((0, 1.74, 1.08), 0.02, 0.01)],
           pts, segs=5)  # forelock
    for sx in (1, -1):
        m.ell("head", (sx * 0.085 * H, 1.74, 1.04), (0.018, 0.022, 0.026), dark, segs=6, rings=4)
        m.ell("head", (sx * 0.04 * H, 1.44, 1.33), (0.012, 0.01, 0.012), dark, segs=5, rings=3)  # nostrils
    m.pivot("jaw", (0, 1.66, 1.02))
    m.tube("jaw", [((0, 1.62, 1.03), 0.05 * H, 0.04 * H), ((0, 1.48, 1.17), 0.045 * H, 0.03 * H),
                   ((0, 1.39, 1.25), 0.04 * H, 0.025 * H)], muzzle, segs=6)

    def ear(sx, side):
        part = "ear_" + side
        m.pivot(part, (sx * 0.05, 1.88, 0.93))
        m.tube(part, [((sx * 0.05, 1.87, 0.93), 0.03, 0.022), ((sx * 0.06, 1.95, 0.93), 0.028, 0.016),
                      ((sx * 0.065, 2.01, 0.94), 0.004, 0.003)], coat, segs=6)
    mirror(ear)

    # Tail: the dock, then the hair hung from it.
    m.pivot("tail1", (0, 1.34, -0.82))
    m.tube("tail1", [((0, 1.36, -0.80), 0.05, 0.05), ((0, 1.30, -0.88), 0.055, 0.05), ((0, 1.20, -0.92), 0.06, 0.05)],
           pts, segs=6)
    m.pivot("tail2", (0, 1.20, -0.92))
    m.tube("tail2", [((0, 1.21, -0.92), 0.06, 0.05), ((0, 0.98, -0.97), 0.085, 0.06), ((0, 0.76, -0.98), 0.07, 0.05),
                     ((0, 0.62, -0.97), 0.02, 0.02)], pts, segs=7)

    # Legs: upper (forearm / gaskin), lower (cannon) from the knee or hock, hoof (pastern + hoof)
    # from the fetlock. Lower legs are points colour (black on a bay).
    def legs(sx, side):
        x = sx * 0.15 * W
        f, h = "F" + side, "B" + side
        # front
        m.pivot("legU_" + f, (x, 1.0, 0.45))
        m.tube("legU_" + f, [((x, 1.08, 0.44), 0.09 * L, 0.13 * L), ((x, 0.82, 0.46), 0.075 * L, 0.09 * L),
                             ((x, 0.52, 0.47), 0.05 * L, 0.055 * L)], coat, segs=7)
        m.pivot("legL_" + f, (x, 0.50, 0.47))
        m.ell("legL_" + f, (x, 0.50, 0.475), (0.05 * L, 0.06, 0.055 * L), pts, segs=6, rings=4)   # knee
        m.tube("legL_" + f, [((x, 0.50, 0.47), 0.04 * L, 0.045 * L), ((x, 0.19, 0.47), 0.036 * L, 0.04 * L)], pts, segs=6)
        m.pivot("hoof_" + f, (x, 0.17, 0.47))
        hoof_leg(f, x, 0.47, 1)
        # hind
        m.pivot("legU_" + h, (x, 1.0, -0.55))
        m.tube("legU_" + h, [((x * 1.02, 1.10, -0.56), 0.13 * W, 0.2 * D), ((x, 0.84, -0.52), 0.09 * L, 0.13 * L),
                             ((x, 0.58, -0.66), 0.05 * L, 0.07 * L)], coat, segs=7)
        m.pivot("legL_" + h, (x, 0.56, -0.66))
        m.ell("legL_" + h, (x, 0.57, -0.68), (0.045 * L, 0.06, 0.06 * L), pts, segs=6, rings=4)   # hock
        m.tube("legL_" + h, [((x, 0.57, -0.66), 0.042 * L, 0.05 * L), ((x, 0.19, -0.64), 0.038 * L, 0.042 * L)], pts, segs=6)
        m.pivot("hoof_" + h, (x, 0.17, -0.64))
        hoof_leg(h, x, -0.64, 1)

    def hoof_leg(leg, x, z, _):
        part = "hoof_" + leg
        m.ell(part, (x, 0.17, z + 0.005), (0.048 * L, 0.05, 0.052 * L), pts, segs=6, rings=4)   # fetlock
        m.tube(part, [((x, 0.17, z), 0.036 * L, 0.04 * L), ((x, 0.08, z + 0.04), 0.04 * L, 0.044 * L)], pts, segs=6)
        if cfg["feather"]:  # shaggy hair over the hoof
            m.tube(part, [((x, 0.2, z - 0.01), 0.055 * L, 0.06 * L), ((x, 0.1, z + 0.02), 0.075 * L, 0.08 * L),
                          ((x, 0.05, z + 0.04), 0.07 * L, 0.075 * L)], pts, segs=7)
        m.tube(part, [((x, 0.08, z + 0.045), 0.046 * L, 0.05 * L), ((x, 0.0, z + 0.06), 0.06 * L, 0.066 * L)], hoof, segs=7)
    mirror(legs)

    # ---- tack (parts hidden unless the instance's tack mask has their bit)
    # riding saddle: cloth, seat, pommel and cantle, girth, stirrup leathers and irons
    by = 1.10 + 0.35 * D  # top of the back
    m.pivot("saddle", (0, by, 0.12))
    m.ell("saddle", (0, by - 0.06, 0.1), (0.3 * W, 0.1, 0.28), cloth, segs=10, rings=5)
    m.ell("saddle", (0, by + 0.03, 0.1), (0.17 * W, 0.06, 0.22), leather, segs=8, rings=5)
    m.ell("saddle", (0, by + 0.08, 0.29), (0.1, 0.07, 0.05), leather, segs=6, rings=4)
    m.ell("saddle", (0, by + 0.09, -0.09), (0.12, 0.08, 0.045), leather, segs=6, rings=4)
    loop("saddle", (0, 1.10, 0.24), (1, 0, 0), (0, 1, 0), 0.295 * W, 0.355 * D, 0.018, leather, n=14)
    for sx in (1, -1):
        m.tube("saddle", [((sx * 0.2 * W, by - 0.02, 0.14), 0.012, 0.02), ((sx * 0.3 * W, 0.96, 0.15), 0.01, 0.018)],
               leather, segs=4)
        loop("saddle", (sx * 0.305 * W, 0.92, 0.15), (0, 0, 1), (0, 1, 0), 0.05, 0.045, 0.01, iron, n=8)

    # bridle: headstall, browband, noseband, bit rings; reins along the neck to the pommel
    m.pivot("bridle", (0, 1.78, 0.95))
    for sx in (1, -1):
        m.tube("bridle", [((sx * 0.07 * H, 1.88, 0.92), 0.012, 0.012), ((sx * 0.095 * H, 1.72, 1.04), 0.012, 0.012),
                          ((sx * 0.075 * H, 1.48, 1.22), 0.012, 0.012)], leather, segs=4)
        loop("bridle", (sx * 0.072 * H, 1.45, 1.25), (0, 1, 0), (0, 0, 1), 0.025, 0.025, 0.006, iron, n=6)
    loop("bridle", (0, 1.82, 0.97), (1, 0, 0), (0, 0.6, 0.8), 0.1 * H, 0.08 * H, 0.012, leather, n=10, arc=(-0.1, 0.6))
    loop("bridle", (0, 1.53, 1.18), (1, 0, 0), (0, 0.6, 0.8), 0.085 * H, 0.09 * H, 0.012, leather, n=12)
    m.pivot("reins", (0, 1.22, 0.55))
    for sx in (1, -1):
        m.tube("reins", [((sx * 0.08 * H, 1.45, 1.25), 0.008, 0.008), ((sx * 0.15 * N, 1.40, 0.92), 0.008, 0.008),
                         ((sx * 0.14 * N, 1.44, 0.62), 0.008, 0.008), ((sx * 0.06, by + 0.06, 0.32), 0.008, 0.008)],
               leather, segs=4, cap0=False, cap1=False)

    # rope head collar (halter) and its lead rope, hanging slack from the chin ring
    m.pivot("halter", (0, 1.78, 0.95))
    loop("halter", (0, 1.86, 0.95), (1, 0, 0), (0, 0.3, 0.95), 0.1 * H, 0.06 * H, 0.014, rope, n=10, arc=(-0.05, 0.55))
    for sx in (1, -1):
        m.tube("halter", [((sx * 0.1 * H, 1.86, 0.95), 0.014, 0.014), ((sx * 0.095 * H, 1.62, 1.1), 0.014, 0.014)],
               rope, segs=4)
    loop("halter", (0, 1.57, 1.15), (1, 0, 0), (0, 0.6, 0.8), 0.09 * H, 0.095 * H, 0.015, rope, n=12)
    m.pivot("lead", (0, 1.50, 1.12))
    m.tube("lead", [((0, 1.50, 1.11), 0.012, 0.012), ((0.02, 1.25, 1.14), 0.012, 0.012), ((0.03, 1.08, 1.12), 0.012, 0.012),
                    ((0.05, 1.12, 1.05), 0.012, 0.012), ((0.06, 1.30, 1.02), 0.012, 0.012)], rope, segs=4)

    # draught collar and hames on the neck; back pad, belly band, traces and breeching on the body
    m.pivot("collar", (0, 1.22, 0.55))
    # the collar ring lies across the base of the neck (perpendicular to it), resting on the shoulders
    cc, up, ra, rb = (0, 1.33, 0.63), (0, 0.87, -0.5), 0.2 * N, 0.3 * N
    loop("collar", cc, (1, 0, 0), up, ra, rb, 0.06, pad, n=14)
    wood = m.mat("wood", "#7a5a38")
    for sx in (1, -1):  # hames: bent bars along the collar's sides, their tips above it
        m.tube("collar", [((sx * (ra * math.cos(math.radians(a)) + 0.03), cc[1] + up[1] * rb * t, cc[2] + up[2] * rb * t), 0.02, 0.02)
                          for a, t in ((60, -0.85), (10, -0.2), (-35, 0.6), (-60, 1.15))], wood, segs=5)
    m.pivot("harness", (0, by, 0.1))
    m.ell("harness", (0, by - 0.02, 0.08), (0.16 * W, 0.07, 0.15), leather, segs=8, rings=4)
    loop("harness", (0, 1.10, 0.1), (1, 0, 0), (0, 1, 0), 0.3 * W, 0.36 * D, 0.025, leather, n=14)
    loop("harness", (0, 1.12, -0.5), (1, 0, 0), (0, 1, 0), 0.31 * W, 0.37 * D, 0.02, leather, n=14, arc=(0.0, 0.5))
    for sx in (1, -1):
        m.tube("harness", [((sx * (0.2 * N + 0.04), 1.2, 0.66), 0.022, 0.03), ((sx * 0.3 * W, 1.06, 0.38), 0.022, 0.03),
                           ((sx * 0.31 * W, 1.0, 0.1), 0.022, 0.03),
                           ((sx * 0.31 * W, 0.98, -0.45), 0.022, 0.03), ((sx * 0.3 * W, 0.96, -0.95), 0.02, 0.028)],
               leather, segs=4)
    m.tube("harness", [((0.31 * W, 1.0, -0.45), 0.02, 0.02), ((0.27 * W, 1.0, -0.72), 0.02, 0.02), ((0.0, 1.02, -0.9), 0.02, 0.02),
                       ((-0.27 * W, 1.0, -0.72), 0.02, 0.02), ((-0.31 * W, 1.0, -0.45), 0.02, 0.02)], leather, segs=4)
    m.tags = {p: TACK_BITS[p] for p in TACK_BITS if p in m.parts}
    return m


# ------------------------------------------------------------------ travelling wagon

# Body origin = on the ground midway between the axles; the pole tip (where the team's collars
# hold it) leads. Keep in sync with src/engine/wagon.ts (WAGON).
WAGON = dict(axle_b=-1.35, axle_f=1.35, r_b=0.62, r_f=0.48, track=0.79, pole_tip=4.2)


def build_wagon(name):
    """The stable's travelling wagon: a painted bed under a hooped linen hood, luggage chest on
    the back, perch and rear axle on the body; the front axle with its bolster, hounds, pole and
    splinter bar turns as one part (fore, about the king pin); four spoked wheels spin about
    their hubs (front ones ride on fore)."""
    import math
    W = WAGON
    m = Model(name)
    paint = m.mat("paint", "#7e3324")
    trim = m.mat("trim", "#b8862e")
    wood = m.mat("wood", "#6b4a2c")
    dark = m.mat("dark", "#43301f")
    canvas = m.mat("canvas", "#ddd2b6")
    canvas_in = m.mat("canvas_in", "#a39577")
    iron = m.mat("iron", "#3a3836")
    chest = m.mat("chest", "#5a3a22")
    zb, zf = W["axle_b"], W["axle_f"]

    # bed, side and end boards, rails
    m.box("body", (0, 0.88, -0.05), (1.3, 0.08, 3.9), wood)
    for sx in (1, -1):
        m.box("body", (sx * 0.63, 1.06, -0.05), (0.05, 0.36, 3.9), paint)
        m.box("body", (sx * 0.655, 1.25, -0.05), (0.08, 0.05, 3.96), trim)
        m.box("body", (sx * 0.655, 0.9, -0.05), (0.07, 0.05, 3.94), dark)
    for z in (1.88, -1.98):
        m.box("body", (0, 1.06, z), (1.3, 0.36, 0.05), paint)
        m.box("body", (0, 1.25, z), (1.36, 0.05, 0.08), trim)
    # undercarriage on the body: perch, rear axle and bolster
    m.box("body", (0, 0.7, 0.0), (0.12, 0.1, 3.0), dark)
    m.box("body", (0, W["r_b"], zb), (1.72, 0.1, 0.12), dark)
    m.box("body", (0, 0.76, zb), (1.3, 0.14, 0.14), dark)
    # luggage chest on a rack at the back, iron bands
    m.box("body", (0, 0.86, -2.22), (1.1, 0.05, 0.5), dark)
    m.box("body", (0, 1.1, -2.24), (0.92, 0.42, 0.42), chest)
    for x in (-0.3, 0.3):
        m.box("body", (x, 1.1, -2.24), (0.05, 0.44, 0.44), iron)

    # hood: linen over five hoops, sagging a little between them; puckered at both ends, the
    # back drawn nearly shut
    def arch(z, k=1.0, lift=0.0, n=11):
        """Hood section: sides at y 1.25, crown at 2.25; k shrinks it toward (0, 1.55)."""
        cy = 1.55
        return [(0.67 * k * math.cos(math.pi * i / (n - 1)), cy + (1.25 - cy + math.sin(math.pi * i / (n - 1))) * k + lift, z)
                for i in range(n)]
    hoops = [-1.85, -0.95, -0.05, 0.85, 1.75]
    rings = [arch(-2.02, 0.12), arch(-2.0, 0.5)]
    for a, b in zip(hoops, hoops[1:]):
        rings += [arch(a), arch((a + b) / 2, 0.985, -0.03)]
    rings += [arch(hoops[-1]), arch(1.98, 0.82)]
    m.sheet("body", rings, canvas, canvas_in)
    for z in hoops:  # hoops showing through as ribs
        m.tube("body", [(p, 0.022, 0.022) for p in arch(z, 1.012)], trim, segs=3, cap0=False, cap1=False)

    # fore carriage: front axle, bolster, hounds, pole, splinter bar and the traces' ends
    m.pivot("fore", (0, W["r_f"], zf))
    m.box("fore", (0, W["r_f"], zf), (1.52, 0.1, 0.12), dark)
    m.box("fore", (0, 0.65, zf), (1.1, 0.12, 0.14), dark)
    for sx in (1, -1):
        m.tube("fore", [((sx * 0.42, 0.5, zf), 0.035, 0.035), ((sx * 0.05, 0.56, zf + 0.95), 0.03, 0.03)], dark, segs=4)
    m.tube("fore", [((0, 0.5, zf - 0.1), 0.05, 0.05), ((0, 0.6, zf + 1.0), 0.05, 0.05), ((0, 1.0, W["pole_tip"]), 0.035, 0.035)],
           wood, segs=6)
    m.box("fore", (0, 0.58, zf + 0.6), (1.6, 0.07, 0.08), wood)
    for sx in (1, -1):
        for dx in (0.4, 1.1):
            m.tube("fore", [((sx * dx, 0.6, zf + 0.6), 0.015, 0.015), ((sx * dx, 0.98, zf + 1.25), 0.015, 0.015)], dark, segs=3)

    def wheel(part, x, y, z, R, spokes):
        m.pivot(part, (x, y, z))
        n = 22
        rim = [((x, y + R * math.cos(math.tau * i / n), z + R * math.sin(math.tau * i / n)), 0.045, 0.045) for i in range(n + 1)]
        m.tube(part, rim, wood, segs=4, cap0=False, cap1=False)
        tyre = [((x, y + (R + 0.035) * math.cos(math.tau * i / n), z + (R + 0.035) * math.sin(math.tau * i / n)), 0.012, 0.05)
                for i in range(n + 1)]
        m.tube(part, tyre, iron, segs=4, cap0=False, cap1=False)
        side = 1 if x > 0 else -1
        m.tube(part, [((x - side * 0.14, y, z), 0.05, 0.05), ((x - side * 0.06, y, z), 0.1, 0.1),
                      ((x + side * 0.06, y, z), 0.1, 0.1), ((x + side * 0.12, y, z), 0.05, 0.05)], dark, segs=8)
        for k in range(spokes):
            a = math.tau * (k + 0.5) / spokes
            m.tube(part, [((x, y + 0.09 * math.cos(a), z + 0.09 * math.sin(a)), 0.022, 0.022),
                          ((x, y + (R - 0.03) * math.cos(a), z + (R - 0.03) * math.sin(a)), 0.018, 0.018)],
                   wood, segs=4, cap0=False, cap1=False)
    t = W["track"]
    wheel("wheel_FL", t, W["r_f"], zf, W["r_f"], 8)
    wheel("wheel_FR", -t, W["r_f"], zf, W["r_f"], 8)
    wheel("wheel_BL", t + 0.02, W["r_b"], zb, W["r_b"], 10)
    wheel("wheel_BR", -t - 0.02, W["r_b"], zb, W["r_b"], 10)
    return m


# ------------------------------------------------------------------ export

def export(model):
    bc.clear_scene()
    objs = []
    tris = 0
    for part, bm in model.parts.items():
        bm.normal_update()
        mesh = bpy.data.meshes.new(part)
        bm.to_mesh(mesh)
        bm.free()
        for mt in model.mats:
            mesh.materials.append(mt)
        obj = bpy.data.objects.new(part, mesh)
        obj["part"] = part
        bpy.context.collection.objects.link(obj)
        objs.append(obj)
        tris += sum(len(p.vertices) - 2 for p in mesh.polygons)
    meta = {"pivots": model.pivots}
    if getattr(model, "tags", None):
        meta["tags"] = model.tags
    bpy.context.scene["animal"] = json.dumps(meta)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{model.name}.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_extras=True)
    print(f"Exported animal: {path} ({os.path.getsize(path):,} bytes | {len(objs)} parts | {tris} tris)")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    wanted = {a.removesuffix(".glb") for a in argv}
    builders = [(f"animal_deer_{k}", lambda n, c=c: build_deer(n, c)) for k, c in DEER.items()]
    builders += [(f"animal_duck_{k}", lambda n, k=k, c=c: build_duck(n, k, c["scale"])) for k, c in DUCKS.items()]
    builders.append(("animal_duck_ling", build_duckling))
    builders += [(f"animal_{k}", lambda n, c=c: build_horse(n, c)) for k, c in HORSES.items()]
    builders.append(("vehicle_wagon", build_wagon))
    for name, fn in builders:
        if wanted and name not in wanted:
            continue
        export(fn(name))


if __name__ == "__main__":
    main()
