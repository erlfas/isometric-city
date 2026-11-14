#!/usr/bin/env python3
"""
Procedural wildlife models: Lublin Anno Domini 1392
Red deer (stag, hind, fawn) and mallards (drake, duck, duckling) for the Bystrzyca's banks:
one GLB per animal, public/models/animal_<name>.glb. Drawn and animated by src/engine/wildlife.ts.

  blender --background --factory-startup --python build_animals.py [-- animal_deer_stag ...]

Format (like the citizen kits, build_characters.py): one mesh object per rigid part, extras
"part" = part name, no node transforms (check_models.py), and scene extras "animal" = JSON
{"pivots": {part: [x, y, z]}} in glTF coordinates (y up, the animal faces +z). wildlife.ts
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
    bpy.context.scene["animal"] = json.dumps({"pivots": model.pivots})
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
    for name, fn in builders:
        if wanted and name not in wanted:
            continue
        export(fn(name))


if __name__ == "__main__":
    main()
