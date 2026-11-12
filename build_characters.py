#!/usr/bin/env python3
"""
Procedural 3D Medieval Character Pipeline: Lublin Anno Domini 1392
Builds the citizen character kits: one GLB per trade (public/models/char_<trade>.glb).
Each kit is characters/char_<trade>.py defining build(kit); the shared body, heads, primitives,
palettes and the export live here ("Kit pipeline (v2)" below).

  blender --background --factory-startup --python build_characters.py [-- char_tanner ...]
"""

import os
import sys
import math

import bpy
import bmesh
from mathutils import Vector, Matrix, Color

OUTPUT_DIR = "public/models"

def clear_scene():
    """Prunes scene objects and meshes while preserving materials in memory."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def create_mat(name, color, roughness=0.8, metallic=0.0):
    """color is sRGB (as picked by eye); Blender/glTF store linear, so convert."""
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            rgba = (*(srgb_to_linear(v) for v in color[:3]), 1.0)
            bsdf.inputs["Base Color"].default_value = rgba
            bsdf.inputs["Roughness"].default_value = roughness
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = metallic
    return mat

# -------------------------------------------------------------
# Procedural Bmesh Geometry Helpers
# -------------------------------------------------------------

def add_box(bm, cx, cy, cz, w, d, h, mat_idx=0):
    w2, d2, h2 = w * 0.5, d * 0.5, h * 0.5
    v0 = bm.verts.new(Vector((cx - w2, cy - d2, cz - h2)))
    v1 = bm.verts.new(Vector((cx + w2, cy - d2, cz - h2)))
    v2 = bm.verts.new(Vector((cx + w2, cy + d2, cz - h2)))
    v3 = bm.verts.new(Vector((cx - w2, cy + d2, cz - h2)))
    v4 = bm.verts.new(Vector((cx - w2, cy - d2, cz + h2)))
    v5 = bm.verts.new(Vector((cx + w2, cy - d2, cz + h2)))
    v6 = bm.verts.new(Vector((cx + w2, cy + d2, cz + h2)))
    v7 = bm.verts.new(Vector((cx - w2, cy + d2, cz + h2)))

    faces = [
        bm.faces.new([v0, v3, v2, v1]), # -Z bottom
        bm.faces.new([v4, v5, v6, v7]), # +Z top
        bm.faces.new([v0, v1, v5, v4]), # -Y front
        bm.faces.new([v2, v3, v7, v6]), # +Y back
        bm.faces.new([v0, v4, v7, v3]), # -X left
        bm.faces.new([v1, v2, v6, v5]), # +X right
    ]
    for f in faces:
        f.material_index = mat_idx
    return faces

def add_tapered_box(bm, cx, cy, cz, w_bot, d_bot, w_top, d_top, h, mat_idx=0):
    wb2, db2, wt2, dt2, h2 = w_bot * 0.5, d_bot * 0.5, w_top * 0.5, d_top * 0.5, h * 0.5
    v0 = bm.verts.new(Vector((cx - wb2, cy - db2, cz - h2)))
    v1 = bm.verts.new(Vector((cx + wb2, cy - db2, cz - h2)))
    v2 = bm.verts.new(Vector((cx + wb2, cy + db2, cz - h2)))
    v3 = bm.verts.new(Vector((cx - wb2, cy + db2, cz - h2)))
    v4 = bm.verts.new(Vector((cx - wt2, cy - dt2, cz + h2)))
    v5 = bm.verts.new(Vector((cx + wt2, cy - dt2, cz + h2)))
    v6 = bm.verts.new(Vector((cx + wt2, cy + dt2, cz + h2)))
    v7 = bm.verts.new(Vector((cx - wt2, cy + dt2, cz + h2)))

    faces = [
        bm.faces.new([v0, v3, v2, v1]),
        bm.faces.new([v4, v5, v6, v7]),
        bm.faces.new([v0, v1, v5, v4]),
        bm.faces.new([v2, v3, v7, v6]),
        bm.faces.new([v0, v4, v7, v3]),
        bm.faces.new([v1, v2, v6, v5]),
    ]
    for f in faces:
        f.material_index = mat_idx
    return faces

def add_cylinder(bm, cx, cy, cz, r, h, segs=8, mat_idx=0):
    h2 = h * 0.5
    bot, top = [], []
    for i in range(segs):
        ang = (i / segs) * math.pi * 2
        x = cx + math.cos(ang) * r
        y = cy + math.sin(ang) * r
        bot.append(bm.verts.new(Vector((x, y, cz - h2))))
        top.append(bm.verts.new(Vector((x, y, cz + h2))))
    faces = []
    for i in range(segs):
        nxt = (i + 1) % segs
        faces.append(bm.faces.new([bot[i], bot[nxt], top[nxt], top[i]]))
    faces.append(bm.faces.new(top))
    faces.append(bm.faces.new(list(reversed(bot))))
    for f in faces:
        f.material_index = mat_idx
    return faces

def add_oriented_cylinder(bm, p1, p2, radius, segs=8, mat_idx=0):
    """Draws a cylinder connecting 3D point p1 to point p2."""
    v1 = Vector(p1)
    v2 = Vector(p2)
    diff = v2 - v1
    length = diff.length
    if length < 0.001:
        return []
    center = (v1 + v2) * 0.5
    z_axis = Vector((0, 0, 1))
    diff_norm = diff.normalized()
    rot = z_axis.rotation_difference(diff_norm)

    h2 = length * 0.5
    bot, top = [], []
    for i in range(segs):
        ang = (i / segs) * math.pi * 2
        local_x = math.cos(ang) * radius
        local_y = math.sin(ang) * radius
        
        pt_b = rot @ Vector((local_x, local_y, -h2)) + center
        pt_t = rot @ Vector((local_x, local_y, h2)) + center
        bot.append(bm.verts.new(pt_b))
        top.append(bm.verts.new(pt_t))
    faces = []
    for i in range(segs):
        nxt = (i + 1) % segs
        faces.append(bm.faces.new([bot[i], bot[nxt], top[nxt], top[i]]))
    faces.append(bm.faces.new(top))
    faces.append(bm.faces.new(list(reversed(bot))))
    for f in faces:
        f.material_index = mat_idx
    return faces

def add_cone(bm, cx, cy, cz, r_bot, r_top, h, segs=8, mat_idx=0):
    h2 = h * 0.5
    bot, top = [], []
    for i in range(segs):
        ang = (i / segs) * math.pi * 2
        bot.append(bm.verts.new(Vector((cx + math.cos(ang) * r_bot, cy + math.sin(ang) * r_bot, cz - h2))))
        if r_top > 0.001:
            top.append(bm.verts.new(Vector((cx + math.cos(ang) * r_top, cy + math.sin(ang) * r_top, cz + h2))))
    faces = []
    if r_top > 0.001:
        for i in range(segs):
            nxt = (i + 1) % segs
            faces.append(bm.faces.new([bot[i], bot[nxt], top[nxt], top[i]]))
        faces.append(bm.faces.new(top))
    else:
        apex = bm.verts.new(Vector((cx, cy, cz + h2)))
        for i in range(segs):
            nxt = (i + 1) % segs
            faces.append(bm.faces.new([bot[i], bot[nxt], apex]))
    faces.append(bm.faces.new(list(reversed(bot))))
    for f in faces:
        f.material_index = mat_idx
    return faces

# -------------------------------------------------------------
# Base Character Generator Macro
# -------------------------------------------------------------

# -------------------------------------------------------------
# Kit pipeline (v2): shared body, rigid animatable parts, variants, colour slots
# -------------------------------------------------------------
# A kit GLB holds one mesh object per (part, variant). The renderer
# (src/engine/citizen-crowd.ts) instances every object, swings each part about its
# pivot, picks one option per variant group and one colour per slot for each citizen.
#   part     body | head | arm_L | arm_R | leg_L | leg_R   (extras "part")
#   variant  "" = always drawn, else "group:option"          (extras "variant")
#   Slot_*   materials are white; the renderer tints them from the kit's palettes.
# Blender frame: Z up, the character faces -Y, so its right hand is at -X.

import json

BASE_PIVOTS = {            # Blender (y, z) of each part's swing axis (parallel to X)
    "body": (0.0, 0.90),
    "head": (0.0, 1.47),
    "arm_L": (0.0, 1.39),
    "arm_R": (0.0, 1.39),
    "leg_L": (0.0, 0.90),
    "leg_R": (0.0, 0.90),
}

HEAD_C = (0.0, 0.005, 1.61)
HEAD_R = (0.094, 0.108, 0.13)

# Palettes are sRGB hex. Tiers: p plebeian, a artisan, b burgher, r patrician.
SKIN = [["#e8c4a6", 3, "pabr"], ["#dcb08e", 3, "pabr"], ["#c99878", 2, "pabr"], ["#b98466", 1, "pab"]]
HAIR = [["#2c1e14", 3, "pabr"], ["#4a3220", 3, "pabr"], ["#6b4a2e", 2, "pabr"],
        ["#9a7448", 1, "pabr"], ["#7a3e22", 1, "pabr"], ["#1a1512", 1, "pabr"]]
HAIR_OLD = [["#8f8a84", 2, "pabr"], ["#bdb8b0", 2, "pabr"], ["#5e5852", 1, "pabr"]]
UNDYED = [["#8a7f6a", 3, "pa"], ["#6f6552", 3, "pa"], ["#9b927e", 2, "pab"], ["#5a5446", 2, "pa"]]
DYED = [["#5f6b3a", 2, "ab"], ["#4b5a6e", 2, "abr"], ["#7a3a2c", 2, "abr"],
        ["#8a6a2e", 2, "ab"], ["#3e4f3a", 1, "abr"], ["#2f3f63", 1, "br"], ["#8c2f2a", 1, "br"]]
LINEN = [["#e6dfcf", 3, "pabr"], ["#d6ccb4", 3, "pabr"], ["#c7bba0", 2, "pa"]]
KERCHIEF = LINEN[1:] + [["#b9a27a", 2, "pa"], ["#a86656", 1, "ab"], ["#7e8ea3", 1, "abr"],
                        ["#b8963f", 1, "ab"]]   # unbleached, madder, woad, weld
HOSE = [["#4f4a3e", 3, "pa"], ["#5d4a36", 2, "pab"], ["#3b3f45", 2, "abr"], ["#6e2f28", 1, "br"]]
LEATHER = [["#3a2a1c", 3, "pabr"], ["#4d3622", 2, "pabr"], ["#2b211a", 2, "pabr"]]
OILED = [["#24201c", 3, "pabr"], ["#2f2a24", 2, "pabr"], ["#3a2c22", 2, "pabr"]]
KIRTLE = [["#6d6450", 3, "pa"], ["#5f6b3a", 2, "pab"], ["#7a3a2c", 2, "abr"],
          ["#4b5a6e", 2, "abr"], ["#8a6a2e", 1, "ab"], ["#2f3f63", 1, "br"]]


def srgb_hex(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


class Kit:
    def __init__(self, name):
        self.name = name
        self.parts = {}                 # (part, variant) -> bmesh
        self.mat_list = []              # bpy materials, index = material_index
        self.mat_idx = {}
        self.groups = {}                # group -> {option: [weight_male, weight_female]}
        self.slots = {}                 # slot -> palette list
        self.anim = {"work": "idle"}
        self.slot("skin", SKIN)
        self.slot("hair", HAIR)
        self.slot("hair_old", HAIR_OLD)

    def bm(self, part, variant=""):
        key = (part, variant)
        if key not in self.parts:
            self.parts[key] = bmesh.new()
        return self.parts[key]

    def mat(self, key, color=None, roughness=0.8, metallic=0.0):
        """'slot:tunic' -> white Slot_tunic material; 'iron_steel' -> FIXED_MATS material;
        key + color (sRGB tuple or "#hex") -> this kit's own material Kit_<kit>_<key>."""
        if key not in self.mat_idx:
            if key.startswith("slot:"):
                m = create_mat("Slot_" + key[5:], (1.0, 1.0, 1.0), roughness=0.85)
            elif color is not None:
                rgb = srgb_hex(color) if isinstance(color, str) else color
                m = create_mat(f"Kit_{self.name}_{key}", rgb, roughness=roughness, metallic=metallic)
            else:
                m = FIXED_MATS[key]
            self.mat_idx[key] = len(self.mat_list)
            self.mat_list.append(m)
        return self.mat_idx[key]

    def slot(self, name, palette):
        self.slots[name] = palette

    def option(self, group, opt, w_male, w_female):
        self.groups.setdefault(group, {})[opt] = [w_male, w_female]


FIXED_MATS = {}

def get_fixed_mats():
    FIXED_MATS.update({
        "eye": create_mat("CharEye", (0.16, 0.12, 0.10), roughness=0.4),
        "lip": create_mat("CharLip", (0.55, 0.32, 0.28), roughness=0.7),
        # Low metallic: the scene has no environment map, so metal renders near black.
        # Own name: create_mat reuses by name and the legacy builders define CharIronSteel.
        "iron_steel": create_mat("CharSteelBright", (0.62, 0.63, 0.65), roughness=0.4, metallic=0.3),
        "iron_dark": create_mat("CharIronDarkKit", (0.2, 0.2, 0.22), roughness=0.45, metallic=0.3),
        "wood_ash": create_mat("CharWoodAsh", (0.48, 0.36, 0.24), roughness=0.75),
        "wood_dark": create_mat("CharWoodDark", (0.28, 0.18, 0.10), roughness=0.75),
        "leather_tan": create_mat("CharLeatherTan", (0.38, 0.26, 0.16), roughness=0.7),
        "hot_iron": create_mat("CharHotIron", (0.95, 0.35, 0.05), roughness=0.2),
    })


# --- smooth primitives -------------------------------------------------------

def _frame(d):
    """Right-handed ring frame (side, front) perpendicular to unit direction d."""
    x = Vector((1, 0, 0))
    s = x - d * x.dot(d)
    if s.length < 1e-4:
        y = Vector((0, 1, 0))
        s = y - d * y.dot(d)
    s.normalize()
    return s, d.cross(s)


def add_tube(bm, pts, segs=8, mat_idx=0, cap0=True, cap1=True, smooth=True):
    """Lofted tube through pts = [((x,y,z), r_side, r_front), ...]; rings are
    perpendicular to the path, so it bends at elbows and knees."""
    P = [Vector(p[0]) for p in pts]
    rings = []
    for i, (_, rs, rf) in enumerate(pts):
        a = P[max(i - 1, 0)]
        b = P[min(i + 1, len(P) - 1)]
        d = (b - a).normalized()
        s, f = _frame(d)
        ring = []
        for j in range(segs):
            ang = j / segs * math.tau
            ring.append(bm.verts.new(P[i] + s * (math.cos(ang) * rs) + f * (math.sin(ang) * rf)))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(segs):
            k = (j + 1) % segs
            faces.append(bm.faces.new([r0[j], r0[k], r1[k], r1[j]]))
    caps = []
    if cap1:
        caps.append(bm.faces.new(rings[-1]))
    if cap0:
        caps.append(bm.faces.new(list(reversed(rings[0]))))
    for f in faces:
        f.material_index = mat_idx
        f.smooth = smooth
    for f in caps:
        f.material_index = mat_idx
    return faces + caps


def add_ellipsoid(bm, c, r, segs=10, rings=7, mat_idx=0, keep=None, taper=0.0, smooth=True):
    """Ellipsoid centred at c with radii r. keep(nx, ny, nz) filters faces by their
    unit-sphere centre (open shells for hair, hoods, beards). taper narrows X toward
    the bottom (jaw)."""
    cx, cy, cz = c
    rx, ry, rz = r

    def pos(lat, lon):
        nz = math.sin(lat)
        nx = math.cos(lat) * math.cos(lon)
        ny = math.cos(lat) * math.sin(lon)
        t = 1.0 - taper * max(0.0, -nz)
        return Vector((cx + nx * rx * t, cy + ny * ry, cz + nz * rz)), (nx, ny, nz)

    grid = []
    for i in range(1, rings):
        lat = -math.pi / 2 + math.pi * i / rings
        grid.append([bm.verts.new(pos(lat, j / segs * math.tau)[0]) for j in range(segs)])
    bot = bm.verts.new(Vector((cx, cy, cz - rz)))
    top = bm.verts.new(Vector((cx, cy, cz + rz)))

    def centre(i, j):  # unit coords at the centre of band i (0 = bottom fan), column j
        lat = -math.pi / 2 + math.pi * (i + 0.5) / rings
        return pos(lat, (j + 0.5) / segs * math.tau)[1]

    faces = []

    def emit(verts, i, j):
        if keep is None or keep(*centre(i, j)):
            faces.append(bm.faces.new(verts))

    for j in range(segs):
        k = (j + 1) % segs
        emit([bot, grid[0][k], grid[0][j]], 0, j)
        for i in range(len(grid) - 1):
            emit([grid[i][j], grid[i][k], grid[i + 1][k], grid[i + 1][j]], i + 1, j)
        emit([grid[-1][j], grid[-1][k], top], rings - 1, j)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    for f in faces:
        f.material_index = mat_idx
        f.smooth = smooth
    return faces


def add_panel(bm, z0, z1, w0, w1, y0, y1, t, mat_idx, x=0.0):
    """Flat slab (apron, tabard): bottom edge at z0 (width w0, depth y0), top at z1."""
    v = []
    for (z, w, y) in ((z0, w0, y0), (z1, w1, y1)):
        for dy in (0.0, t):
            for sx in (-1, 1):
                v.append(bm.verts.new(Vector((x + sx * w / 2, y + dy, z))))
    # v index: [z][dy][sx] -> 4*zi + 2*di + si
    def q(zi, di, si):
        return v[4 * zi + 2 * di + si]
    quads = [
        [q(0, 0, 0), q(0, 0, 1), q(1, 0, 1), q(1, 0, 0)],  # front (-y)
        [q(0, 1, 1), q(0, 1, 0), q(1, 1, 0), q(1, 1, 1)],  # back
        [q(0, 1, 0), q(0, 0, 0), q(1, 0, 0), q(1, 1, 0)],  # -x
        [q(0, 0, 1), q(0, 1, 1), q(1, 1, 1), q(1, 0, 1)],  # +x
        [q(1, 0, 0), q(1, 0, 1), q(1, 1, 1), q(1, 1, 0)],  # top
        [q(0, 1, 0), q(0, 1, 1), q(0, 0, 1), q(0, 0, 0)],  # bottom
    ]
    for f in quads:
        bm.faces.new(f).material_index = mat_idx


def head_surface_y(x, z, lift=0.0):
    """Front surface (-y) of the head ellipsoid at (x, z), pushed out by lift."""
    cx, cy, cz = HEAD_C
    rx, ry, rz = HEAD_R
    nz = (z - cz) / rz
    t = 1.0 - 0.16 * max(0.0, -nz)
    nx = (x - cx) / (rx * t)
    return cy - ry * math.sqrt(max(0.0, 1.0 - nx * nx - nz * nz)) - lift


# --- body ---------------------------------------------------------------------

def kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="shoes", sleeves=("full", "rolled"),
             sleeve_w=(1, 1), male_hem=0.62):
    """Shared adult body: torso (per sex), head with face, arms, legs."""
    sk = kit.mat("slot:skin")
    tun = kit.mat("slot:" + tunic_slot)
    hose = kit.mat("slot:" + hose_slot)
    belt = kit.mat("slot:belt")
    kit.slot("belt", LEATHER)
    kit.slot("shoes", LEATHER)
    kit.option("sex", "m", 1, 0)
    kit.option("sex", "f", 0, 1)

    # Torso, male: tunic to mid-thigh.
    bm = kit.bm("body", "sex:m")
    add_tube(bm, [((0, 0.0, male_hem), 0.215, 0.155), ((0, 0, 0.80), 0.185, 0.13),
                  ((0, 0, 0.98), 0.165, 0.115), ((0, 0, 1.18), 0.19, 0.13),
                  ((0, 0, 1.35), 0.205, 0.125), ((0, 0, 1.40), 0.2, 0.112),
                  ((0, 0, 1.44), 0.13, 0.078), ((0, 0, 1.475), 0.075, 0.065)], segs=10, mat_idx=tun)
    add_tube(bm, [((0, 0, 0.95), 0.172, 0.122), ((0, 0, 1.0), 0.172, 0.122)], segs=10, mat_idx=belt)
    # Torso, female: fitted bodice, kirtle to the ankle.
    bm = kit.bm("body", "sex:f")
    add_tube(bm, [((0, 0.0, 0.07), 0.25, 0.22), ((0, 0, 0.55), 0.205, 0.17),
                  ((0, 0, 0.98), 0.15, 0.105), ((0, -0.005, 1.16), 0.165, 0.125),
                  ((0, 0, 1.33), 0.18, 0.11), ((0, 0, 1.385), 0.185, 0.1),
                  ((0, 0, 1.43), 0.12, 0.075), ((0, 0, 1.465), 0.07, 0.06)], segs=10, mat_idx=tun)
    add_tube(bm, [((0, 0, 0.96), 0.155, 0.11), ((0, 0, 1.0), 0.155, 0.11)], segs=10, mat_idx=belt)

    # Neck + head + face (head part, pivot at the neck).
    bm = kit.bm("head")
    add_tube(bm, [((0, 0.005, 1.42), 0.055, 0.055), ((0, 0.005, 1.53), 0.05, 0.05)], segs=8, mat_idx=sk)
    add_ellipsoid(bm, HEAD_C, HEAD_R, segs=12, rings=8, mat_idx=sk, taper=0.16)
    eye, lip = kit.mat("eye"), kit.mat("lip")
    hair = kit.mat("slot:hair")
    for sx in (-1, 1):
        x = sx * 0.038
        add_box(bm, x, head_surface_y(x, 1.625, -0.006), 1.625, 0.026, 0.014, 0.017, mat_idx=eye)
        xb = sx * 0.042
        add_box(bm, xb, head_surface_y(xb, 1.652, -0.004), 1.652, 0.042, 0.016, 0.011, mat_idx=hair)
        # ears
        add_ellipsoid(bm, (sx * 0.092, 0.012, 1.612), (0.014, 0.022, 0.032), segs=6, rings=4, mat_idx=sk)
    ny = head_surface_y(0, 1.60)
    add_tube(bm, [((0, ny + 0.012, 1.635), 0.011, 0.008), ((0, ny - 0.018, 1.592), 0.02, 0.016),
                  ((0, ny - 0.006, 1.578), 0.016, 0.01)], segs=6, mat_idx=sk)          # nose
    add_box(bm, 0, head_surface_y(0, 1.552, -0.004), 1.552, 0.046, 0.014, 0.010, mat_idx=lip)

    # Arms: shoulder cap + upper sleeve + hand in the base; forearm per sleeve option.
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        bm = kit.bm(side)
        sh = (sx * 0.205, 0.0, 1.385)
        el = (sx * 0.232, 0.01, 1.11)
        wr = (sx * 0.238, -0.05, 0.86)
        # Flat cap rounding the sleeve top into the torso slope (taller ones read as epaulettes).
        add_ellipsoid(bm, (sx * 0.2, 0.0, 1.37), (0.064, 0.066, 0.034), segs=8, rings=5, mat_idx=tun)
        add_tube(bm, [(sh, 0.062, 0.064), (el, 0.052, 0.054)], segs=8, mat_idx=tun)
        add_ellipsoid(bm, (sx * 0.24, -0.065, 0.80), (0.03, 0.042, 0.058), segs=8, rings=5, mat_idx=sk)
        for opt in sleeves:
            vb = kit.bm(side, "sleeves:" + opt)
            if opt == "full":
                add_tube(vb, [(el, 0.052, 0.054), (wr, 0.044, 0.046)], segs=8, mat_idx=tun)
            else:  # rolled to the elbow: bare forearm + cuff
                add_tube(vb, [(el, 0.046, 0.048), (wr, 0.036, 0.038)], segs=8, mat_idx=sk)
                add_tube(vb, [((sx * 0.232, 0.01, 1.14), 0.06, 0.062), ((sx * 0.233, 0.0, 1.08), 0.06, 0.062)],
                         segs=8, mat_idx=tun)
    for opt, w in zip(sleeves, sleeve_w):
        kit.option("sleeves", opt, w, w)

    # Legs: hose + shoes (or boots, drawn by the caller).
    for side, sx in (("leg_R", -1), ("leg_L", 1)):
        bm = kit.bm(side)
        x = sx * 0.095
        add_tube(bm, [((x, 0, 0.93), 0.08, 0.08), ((x, -0.01, 0.48), 0.056, 0.058),
                      ((x, 0.0, 0.10), 0.044, 0.046)], segs=8, mat_idx=hose)
        if shoe == "shoes":
            add_tube(bm, [((x, 0.055, 0.06), 0.048, 0.06), ((x, -0.06, 0.055), 0.054, 0.055),
                          ((x, -0.165, 0.035), 0.04, 0.032)], segs=8, mat_idx=kit.mat("slot:shoes"))
        elif shoe == "boots":
            b = kit.mat("slot:boots")
            add_tube(bm, [((x, 0.0, 0.03), 0.06, 0.062), ((x, 0.0, 0.36), 0.064, 0.066),
                          ((x, 0.0, 0.42), 0.072, 0.074)], segs=8, mat_idx=b)
            add_tube(bm, [((x, 0.06, 0.06), 0.052, 0.062), ((x, -0.06, 0.055), 0.056, 0.056),
                          ((x, -0.17, 0.035), 0.042, 0.034)], segs=8, mat_idx=b)


def kit_heads(kit, options):
    """Hair, beards and head coverings. options: {"hat:<opt>": (w_m, w_f), "beard:<opt>": ...}."""
    hair = kit.mat("slot:hair")
    cx, cy, cz = HEAD_C
    rx, ry, rz = HEAD_R
    for key, (wm, wf) in options.items():
        group, opt = key.split(":")
        kit.option(group, opt, wm, wf)
        bm = kit.bm("head", key)
        if key == "hair:short":
            add_ellipsoid(bm, (cx, cy + 0.006, cz + 0.008), (rx * 1.07, ry * 1.06, rz * 1.04), segs=12, rings=8,
                          mat_idx=hair, keep=lambda x, y, z: z > 0.32 or (y > -0.25 and z > -0.35) or (y > 0.2 and z > -0.6))
        elif key == "hair:long":
            add_ellipsoid(bm, (cx, cy + 0.006, cz + 0.008), (rx * 1.08, ry * 1.07, rz * 1.04), segs=12, rings=8,
                          mat_idx=hair, keep=lambda x, y, z: z > 0.32 or (y > -0.3 and z > -0.8))
            add_tube(bm, [((0, 0.06, 1.56), 0.085, 0.045), ((0, 0.07, 1.45), 0.08, 0.04)], segs=8, mat_idx=hair)
        elif key == "hair:bald":
            add_ellipsoid(bm, (cx, cy + 0.006, cz + 0.004), (rx * 1.06, ry * 1.05, rz * 1.03), segs=12, rings=8,
                          mat_idx=hair, keep=lambda x, y, z: z < 0.2 and z > -0.3 and y > -0.1)
        elif key == "beard:short":
            add_ellipsoid(bm, HEAD_C, (rx * 1.04, ry * 1.05, rz * 1.02), segs=12, rings=8, mat_idx=hair, taper=0.16,
                          keep=lambda x, y, z: z < -0.3 and y < 0.35)
        elif key == "beard:full":
            add_ellipsoid(bm, HEAD_C, (rx * 1.06, ry * 1.08, rz * 1.03), segs=12, rings=8, mat_idx=hair, taper=0.16,
                          keep=lambda x, y, z: z < -0.2 and y < 0.4)
            add_tube(bm, [((0, -0.07, 1.52), 0.06, 0.04), ((0, -0.085, 1.44), 0.035, 0.025)],
                     segs=8, mat_idx=hair)
        elif key == "beard:moustache":
            y = head_surface_y(0, 1.568, 0.002)
            add_tube(bm, [((-0.045, y + 0.012, 1.556), 0.008, 0.008), ((0, y, 1.570), 0.014, 0.01),
                          ((0.045, y + 0.012, 1.556), 0.008, 0.008)], segs=6, mat_idx=hair)
        elif key == "hat:coif":   # linen coif tied under the chin
            m = kit.mat("slot:linen")
            add_ellipsoid(bm, (cx, cy + 0.01, cz + 0.012), (rx * 1.14, ry * 1.12, rz * 1.08), segs=12, rings=8,
                          mat_idx=m, keep=lambda x, y, z: z > -0.62 and not (y < -0.5 and z < 0.45))
            for sx in (-1, 1):   # thin ties: thick ones read as a white beard
                add_tube(bm, [((sx * 0.085, -0.03, 1.53), 0.005, 0.005), ((sx * 0.04, -0.07, 1.47), 0.005, 0.005),
                              ((0, -0.08, 1.46), 0.005, 0.005)], segs=4, mat_idx=m)
            add_fringe(bm, hair)
        elif key == "hat:kerchief":  # women: kerchief knotted at the nape
            m = kit.mat("slot:kerchief")
            add_ellipsoid(bm, (cx, cy + 0.012, cz + 0.012), (rx * 1.14, ry * 1.13, rz * 1.08), segs=12, rings=8,
                          mat_idx=m, keep=lambda x, y, z: (z > 0.15 and y > -0.75) or (y > 0.1 and z > -0.5))
            add_tube(bm, [((0, 0.11, 1.58), 0.03, 0.03), ((0, 0.135, 1.52), 0.04, 0.02)], segs=6, mat_idx=m)
            add_fringe(bm, hair)
        elif key == "hat:cap":    # felt skullcap
            m = kit.mat("slot:cap")
            add_ellipsoid(bm, (cx, cy + 0.004, cz + 0.03), (rx * 1.12, ry * 1.1, rz * 1.0), segs=12, rings=8,
                          mat_idx=m, keep=lambda x, y, z: z > 0.25)
            add_tube(bm, [((0, cy + 0.004, cz + 0.045), rx * 1.13, ry * 1.11), ((0, cy + 0.004, cz + 0.075), rx * 1.13, ry * 1.11)],
                     segs=12, mat_idx=m, cap0=False, cap1=False)
        elif key == "hat:hood":   # wool hood with shoulder cape
            m = kit.mat("slot:hood")
            add_ellipsoid(bm, (cx, cy + 0.015, cz + 0.015), (rx * 1.26, ry * 1.22, rz * 1.15), segs=12, rings=8,
                          mat_idx=m, keep=lambda x, y, z: not (y < -0.42 and -0.75 < z < 0.5))
            add_tube(bm, [((0, 0.01, 1.30), 0.27, 0.2), ((0, 0.01, 1.42), 0.17, 0.14), ((0, 0.015, 1.50), 0.1, 0.1)],
                     segs=10, mat_idx=m, cap1=False)
        elif key == "hat:veil":      # women: wimple round the face + veil to the shoulders
            m = kit.mat("slot:linen")
            add_ellipsoid(bm, (cx, cy + 0.012, cz + 0.012), (rx * 1.16, ry * 1.14, rz * 1.1), segs=12, rings=8,
                          mat_idx=m, keep=lambda x, y, z: not (y < -0.45 and -0.62 < z < 0.5))
            add_tube(bm, [((0, 0.03, 1.33), 0.2, 0.17), ((0, 0.03, 1.50), 0.12, 0.13), ((0, 0.02, 1.58), 0.11, 0.12)],
                     segs=10, mat_idx=m, cap1=False)
        elif key in ("hat:bare", "beard:none"):
            pass
        else:
            raise ValueError(f"{kit.name}: unknown head option {key}")
    kit.slot("linen", LINEN)
    kit.slot("kerchief", KERCHIEF)


def add_fringe(bm, hair):
    """Strip of hair across the forehead under a head cloth, so white linen does not read as white hair."""
    pts = []
    for x in (-0.07, -0.035, 0.0, 0.035, 0.07):
        z = 1.672 - 0.9 * x * x
        pts.append(((x, head_surface_y(x, z, 0.004), z), 0.012, 0.009))
    add_tube(bm, pts, segs=6, mat_idx=hair)


def kit_bib_apron(kit, variant, slot, bottom=0.30, top=1.30, waist_only=False):
    """Front apron hung from a neck strap; bottom tilts forward so walking legs clear it."""
    m = kit.mat("slot:" + slot)
    for sex, (wb, wt, yb, yt) in {"m": (0.40, 0.30, -0.215, -0.135), "f": (0.42, 0.28, -0.205, -0.125)}.items():
        bm = kit.bm("body", f"{variant}+sex:{sex}")
        add_panel(bm, bottom, 0.99, wb, wt, yb, yt, 0.018, m)
        if not waist_only:
            yb2 = yt - 0.003
            add_panel(bm, 0.99, top, 0.24, 0.22, yb2, yb2 - 0.004, 0.016, m)
            for sx in (-1, 1):   # neck strap over the shoulders, crossing to the back of the belt
                add_tube(bm, [((sx * 0.1, yb2, top - 0.01), 0.012, 0.006), ((sx * 0.095, -0.06, 1.45), 0.012, 0.006),
                              ((sx * 0.1, 0.11, 1.38), 0.012, 0.006), ((-sx * 0.09, 0.13, 1.0), 0.012, 0.006)],
                             segs=4, mat_idx=m)


KIT_DIR = "characters"   # one file per kit: characters/char_<trade>.py defining build(kit)


def load_kit_builders():
    """Each kit file runs with this module's globals (Kit, kit_body, kit_heads, primitives, palettes)."""
    out = []
    for fn in sorted(os.listdir(KIT_DIR)):
        if fn.startswith("char_") and fn.endswith(".py"):
            path = os.path.join(KIT_DIR, fn)
            ns = dict(globals())
            with open(path, encoding="utf-8") as f:
                exec(compile(f.read(), path, "exec"), ns)
            out.append((fn[:-3], ns["build"]))
    return out


def gltf_yz(y, z):
    """Blender (y, z) -> glTF (y_up, z_front) for a pivot on the X axis."""
    return [round(z, 4), round(-y, 4)]


def export_kit(kit):
    clear_scene()
    objs = []
    tris = {}
    for (part, variant), bm in kit.parts.items():
        if not bm.faces:          # options like hat:bare draw nothing
            bm.free()
            continue
        bm.normal_update()
        name = f"{part}__{variant.replace(':', '_').replace('+', '_') or 'base'}"
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for m in kit.mat_list:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(name, mesh)
        obj["part"] = part
        obj["variant"] = variant
        bpy.context.collection.objects.link(obj)
        objs.append(obj)
        tris[name] = sum(len(p.vertices) - 2 for p in mesh.polygons)
    bpy.context.scene["kit"] = json.dumps({
        "pivots": {p: gltf_yz(*yz) for p, yz in BASE_PIVOTS.items()},
        "groups": kit.groups,
        "slots": kit.slots,
        "anim": kit.anim,
    })
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{kit.name}.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_extras=True)
    base = sum(t for n, t in tris.items() if n.endswith("__base"))
    print(f"Exported kit: {path} ({os.path.getsize(path):,} bytes | {len(objs)} meshes | "
          f"{base} base tris, {sum(tris.values())} incl. all variants)")


# -------------------------------------------------------------
# Compilation & Export Pipeline
# -------------------------------------------------------------

def main():
    print("=== Lublin Anno Domini 1392: Procedural 3D Character Pipeline ===")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    wanted = {a.removesuffix(".glb") for a in argv}
    get_fixed_mats()
    kit_builders = load_kit_builders()
    for name, builder in kit_builders:
        if wanted and name not in wanted:
            continue
        kit = Kit(name)
        builder(kit)
        export_kit(kit)

    print(f"\nDone: character models written to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
