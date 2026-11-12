#!/usr/bin/env python3
"""
Headless Blender Asset Pipeline: Lublin Anno Domini 1392
Procedurally generates high-fidelity low-poly 3D models matching historical medieval architecture:
- 1. Old Town Hall (Ratusz) with clock belfry, blind arcades, copper spires, external stairs
- 2. Szmatruz (Cloth & Bread Hall) with brick pillars and market stalls
- 3. Market Stalls with striped scalloped canopies (red/white, blue/white, yellow/white)
- 4. Market Carts with spoked wheels, loaded with goods
- 5. Municipal Stone Well with timber roof and windlass
- 6. House Type 1: Authentic Timber Log House with saddle notches and cabbage garden patch
- 7. House Type 2: Authentic Half-Timber Jettied House with carved corbels and shop shutters
- 8. House Type 3: Patrician Stepped Brick Kamienica with 5-tier pinnacle crow-gable
- 9. Defensive Curtain Wall and Curtain Defense Tower
- 10. Medieval Oak Tree
- 11. Timber Outbuilding / Backyard Shed
- 12. Gothic Collegiate Parish Church (Fara)
- 13. Romanesque Round Keep (Donżon Zamkowy)
- 14. Kraków Gate & Barbican Drawbridge (Brama Krakowska)
- 15. Grodzka Gate & Czechówka Crossing (Brama Grodzka)
- 16. Castle Archery & Training Yard
- 17. Riverside Watermill with rotating paddle waterwheel and flour dock
- 18. Hilltop Post Windmill (Wiatrak Koźlak) with 4-blade canvas sails and tail-pole
- 19. Stepped Limestone Quarry with timber A-frame jib crane and ashlar blocks
- 20. Logging Camp & Pit Sawmill with two-man pit-saw trestle and log ricks
- 21. Riverside Harbor Wharves with clinker-built cog ship and treadwheel crane
- 22. Blacksmith's Workshop with open forge canopy, glowing coals, anvil, and water quench trough
- 23. Baker's House with domed outdoor brick bread oven, chimney, and gilded pretzel sign
- 24. Brewer's Malthouse with ventilation louvers, cask yard, and outdoor drinking tables
- 25. Tanner's Riverside Workshop with tanning vats, stretched hide racks, and fleshing beam
- 26. Potter's Shed & Kiln Yard with domed pottery kiln, kick-wheel, and terracotta amphora shelves
- 27. Weaver's Half-Timber Workshop with St. Andrew's braces, dye vats, and drying cloth rails
- 28. Dominican Monastery & Cloister Garden with arcaded quad and raised herb beds

All models exported as optimized GLTF/GLB models to public/models/
"""

import os
import sys
import math

import bpy
import bmesh
from mathutils import Vector, Matrix, Color

OUTPUT_DIR = "public/models"

def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)

def create_mat(name, color, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            rgba = (*color[:3], 1.0) if len(color) == 3 else color
            bsdf.inputs["Base Color"].default_value = rgba
            bsdf.inputs["Roughness"].default_value = roughness
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = metallic
    return mat

def get_materials():
    return {
        "brick_gothic": create_mat("BrickGothic", (0.58, 0.18, 0.12)),
        "brick_dark": create_mat("BrickDark", (0.42, 0.14, 0.09)),
        "plaster_white": create_mat("PlasterWhite", (0.86, 0.83, 0.76)),
        "plaster_cream": create_mat("PlasterCream", (0.78, 0.72, 0.60)),
        "stone_limestone": create_mat("Limestone", (0.72, 0.68, 0.58)),
        "timber_dark": create_mat("TimberDark", (0.24, 0.16, 0.10)),
        "timber_plank": create_mat("TimberPlank", (0.48, 0.35, 0.22)),
        "timber_weathered": create_mat("TimberWeathered", (0.36, 0.32, 0.28)),
        "roof_tile_red": create_mat("RoofTileRed", (0.68, 0.24, 0.14)),
        "roof_shingle": create_mat("RoofShingle", (0.32, 0.28, 0.24)),
        "roof_thatch": create_mat("RoofThatch", (0.58, 0.48, 0.28)),
        "copper_patina": create_mat("CopperPatina", (0.20, 0.46, 0.40), roughness=0.5),
        "iron_wrought": create_mat("IronWrought", (0.12, 0.12, 0.14), roughness=0.4, metallic=0.7),
        "awning_red_white": create_mat("AwningRedWhite", (0.85, 0.20, 0.18)),
        "awning_blue_white": create_mat("AwningBlueWhite", (0.18, 0.42, 0.82)),
        "awning_yellow_white": create_mat("AwningYellowWhite", (0.88, 0.72, 0.16)),
        "goods_cheese_bread": create_mat("GoodsFood", (0.86, 0.68, 0.26)),
        "goods_fabrics": create_mat("GoodsFabric", (0.45, 0.25, 0.55)),
        "foliage_green": create_mat("FoliageGreen", (0.22, 0.45, 0.18), roughness=0.9),
        "fire_orange": create_mat("FireOrange", (0.95, 0.40, 0.05), roughness=0.2),
        "pottery_terracotta": create_mat("PotteryTerracotta", (0.75, 0.38, 0.22)),
        "tannin_water": create_mat("TanninWater", (0.22, 0.16, 0.12), roughness=0.1),
        "cloth_indigo": create_mat("ClothIndigo", (0.18, 0.28, 0.58)),
        "cloth_red": create_mat("ClothRed", (0.72, 0.18, 0.20)),
        "cloth_madder": create_mat("ClothMadder", (0.75, 0.18, 0.22)),
        "flour_sack_cloth": create_mat("FlourSack", (0.78, 0.74, 0.64)),
        "hide_leather": create_mat("HideLeather", (0.62, 0.44, 0.28)),
        "iron_steel": create_mat("IronSteel", (0.55, 0.57, 0.60), roughness=0.3, metallic=0.8),
        "gold_sign": create_mat("GoldSign", (0.95, 0.75, 0.14), roughness=0.25, metallic=0.5),
        "water_clean": create_mat("WaterClean", (0.22, 0.38, 0.42), roughness=0.1),
        "dye_indigo": create_mat("DyeIndigo", (0.16, 0.26, 0.58), roughness=0.1),
        "dye_madder": create_mat("DyeMadder", (0.72, 0.16, 0.20), roughness=0.1),
        "cloth_violet": create_mat("ClothViolet", (0.45, 0.20, 0.50), roughness=0.85),
        "cloth_gold": create_mat("ClothGold", (0.85, 0.68, 0.18), roughness=0.85),
        "hide_raw": create_mat("HideRaw", (0.78, 0.68, 0.52), roughness=0.8),
        "coal_black": create_mat("CoalBlack", (0.12, 0.12, 0.12), roughness=0.7),
        "clay_mound": create_mat("ClayMound", (0.58, 0.48, 0.38), roughness=0.9),
        "brick_oven": create_mat("BrickOven", (0.62, 0.24, 0.14), roughness=0.85),
        "gold_pretzel": create_mat("GoldPretzel", (0.96, 0.76, 0.12), roughness=0.25, metallic=0.55),
        "bread_golden": create_mat("BreadGolden", (0.76, 0.50, 0.20), roughness=0.6),
        "birch_bark": create_mat("BirchBark", (0.84, 0.82, 0.78), roughness=0.8),
        "wood_end_grain": create_mat("WoodEndGrain", (0.75, 0.65, 0.46), roughness=0.7),
        "soot_black": create_mat("SootBlack", (0.08, 0.08, 0.08), roughness=0.95),
        # Linear colour: (0.10, 0.14, 0.18) displayed as a light blue-grey (~89,105,118 sRGB).
        "glass_dark": create_mat("GlassDark", (0.022, 0.026, 0.032), roughness=0.35),
        # Texture-family splits (Phase 3): same colours as the flat originals so models
        # look unchanged until the runtime binds textures by material name.
        "timber_log": create_mat("TimberLog", (0.24, 0.16, 0.10)),
        "timber_log_weathered": create_mat("TimberLogWeathered", (0.36, 0.32, 0.28)),
        "stone_fieldstone": create_mat("StoneFieldstone", (0.72, 0.68, 0.58)),
    }


# Per-model material substitutions, applied at export. They split shared flat-colour
# materials into the texture families of docs/material_board:
#   Limestone  -> StoneFieldstone  on vernacular plinths/foundations (rubble masonry);
#                 castle, gates, towers, church, town hall and quarry keep ashlar.
#   TimberDark -> TimberLog        where the slot is the horizontal log body.
FIELDSTONE = {"Limestone": "StoneFieldstone"}
MODEL_MATERIAL_OVERRIDES = {
    "house_timber_log": {"Limestone": "StoneFieldstone", "TimberDark": "TimberLog"},
    "house_tanner": {"TimberWeathered": "TimberLogWeathered", **FIELDSTONE},
    "house_half_timber": FIELDSTONE,
    "shed_timber": FIELDSTONE,
    "town_well": FIELDSTONE,
    "house_baker": FIELDSTONE,
    "house_brewer": FIELDSTONE,
    "blacksmith_workshop": FIELDSTONE,
    "house_potter": FIELDSTONE,
    "house_weaver": FIELDSTONE,
    "watermill": FIELDSTONE,
    "windmill": FIELDSTONE,
    "market_cart": FIELDSTONE,
}

# Materials whose texture grain must follow the part's length (beams, braces, posts)
# rather than the world-up wall projection.
UV_ALONG_LENGTH = {"TimberDark"}

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
        bm.faces.new([v0, v3, v2, v1]), # bottom (-Z)
        bm.faces.new([v4, v5, v6, v7]), # top (+Z)
        bm.faces.new([v0, v1, v5, v4]), # front (-Y)
        bm.faces.new([v2, v3, v7, v6]), # back (+Y)
        bm.faces.new([v0, v4, v7, v3]), # left (-X)
        bm.faces.new([v1, v2, v6, v5]), # right (+X)
    ]
    for f in faces:
        f.material_index = mat_idx
    return faces

def add_sloped_roof(bm, cx, cy, z_base, w, d, h, overhang=0.3, mat_idx=0):
    w2 = w * 0.5 + overhang
    d2 = d * 0.5 + overhang
    v0 = bm.verts.new(Vector((cx - w2, cy - d2, z_base)))
    v1 = bm.verts.new(Vector((cx + w2, cy - d2, z_base)))
    v2 = bm.verts.new(Vector((cx + w2, cy + d2, z_base)))
    v3 = bm.verts.new(Vector((cx - w2, cy + d2, z_base)))
    r0 = bm.verts.new(Vector((cx, cy - d2, z_base + h)))
    r1 = bm.verts.new(Vector((cx, cy + d2, z_base + h)))

    f_left = bm.faces.new([v0, r0, r1, v3])
    f_right = bm.faces.new([v1, v2, r1, r0])
    f_front = bm.faces.new([v0, v1, r0])
    f_back = bm.faces.new([v2, v3, r1])

    for f in [f_left, f_right, f_front, f_back]:
        f.material_index = mat_idx

def add_timber_beam(bm, p1, p2, width=0.18, depth=0.18, mat_idx=0):
    d_vec = p2 - p1
    length = d_vec.length
    if length < 1e-5: return []
    d_dir = d_vec / length
    ref = Vector((0, 0, 1)) if abs(d_dir.z) < 0.9 else Vector((0, 1, 0))
    u_dir = d_dir.cross(ref).normalized()
    v_dir = d_dir.cross(u_dir).normalized()

    w2, dp2 = width * 0.5, depth * 0.5
    offs = [-u_dir * w2 - v_dir * dp2, u_dir * w2 - v_dir * dp2, u_dir * w2 + v_dir * dp2, -u_dir * w2 + v_dir * dp2]
    b0 = [bm.verts.new(p1 + off) for off in offs]
    b1 = [bm.verts.new(p2 + off) for off in offs]

    faces = [
        bm.faces.new([b0[3], b0[2], b0[1], b0[0]]),
        bm.faces.new([b1[0], b1[1], b1[2], b1[3]]),
        bm.faces.new([b0[0], b1[0], b1[3], b0[3]]),
        bm.faces.new([b0[1], b1[1], b1[0], b0[0]]),
        bm.faces.new([b0[2], b1[2], b1[1], b0[1]]),
        bm.faces.new([b0[3], b1[3], b1[2], b0[2]]),
    ]
    for f in faces: f.material_index = mat_idx
    return faces

def add_cylinder(bm, cx, cy, cz, radius, height, segs=12, mat_idx=0):
    h2 = height * 0.5
    bot, top = [], []
    for i in range(segs):
        ang = (i / segs) * math.pi * 2.0
        x = cx + math.cos(ang) * radius
        y = cy + math.sin(ang) * radius
        bot.append(bm.verts.new(Vector((x, y, cz - h2))))
        top.append(bm.verts.new(Vector((x, y, cz + h2))))
    for i in range(segs):
        nxt = (i + 1) % segs
        f = bm.faces.new([bot[i], bot[nxt], top[nxt], top[i]])
        f.material_index = mat_idx
    bm.faces.new(top).material_index = mat_idx
    bm.faces.new(list(reversed(bot))).material_index = mat_idx

def add_pantile_roof(bm, cx, cy, z_base, w, d, h, overhang=0.45, courses=8, mat_tile=0, mat_trim=1, mat_plaster=0):
    w2 = w * 0.5 + overhang
    d2 = d * 0.5 + overhang
    r_z = z_base + h
    trim_thick = 0.14

    for y_end in [-d2, d2 - trim_thick]:
        add_timber_beam(bm, Vector((cx - w2, cy + y_end, z_base)), Vector((cx, cy + y_end, r_z)), width=0.16, depth=trim_thick, mat_idx=mat_trim)
        add_timber_beam(bm, Vector((cx + w2, cy + y_end, z_base)), Vector((cx, cy + y_end, r_z)), width=0.16, depth=trim_thick, mat_idx=mat_trim)

    # Front Gable
    v_f_lb = bm.verts.new(Vector((cx - w2, cy - d2 + trim_thick, z_base)))
    v_f_rb = bm.verts.new(Vector((cx + w2, cy - d2 + trim_thick, z_base)))
    v_f_top = bm.verts.new(Vector((cx, cy - d2 + trim_thick, r_z)))
    f_front = bm.faces.new([v_f_lb, v_f_rb, v_f_top])
    f_front.material_index = mat_plaster

    y_g = cy - d2 + trim_thick * 0.5
    add_timber_beam(bm, Vector((cx, y_g, z_base)), Vector((cx, y_g, r_z)), width=0.18, depth=0.18, mat_idx=mat_trim)
    add_timber_beam(bm, Vector((cx - w2 * 0.65, y_g, z_base)), Vector((cx, y_g, z_base + h * 0.65)), width=0.15, depth=0.15, mat_idx=mat_trim)
    add_timber_beam(bm, Vector((cx + w2 * 0.65, y_g, z_base)), Vector((cx, y_g, z_base + h * 0.65)), width=0.15, depth=0.15, mat_idx=mat_trim)

    # Back Gable
    v_b_lb = bm.verts.new(Vector((cx - w2, cy + d2 - trim_thick, z_base)))
    v_b_rb = bm.verts.new(Vector((cx + w2, cy + d2 - trim_thick, z_base)))
    v_b_top = bm.verts.new(Vector((cx, cy + d2 - trim_thick, r_z)))
    f_back = bm.faces.new([v_b_rb, v_b_lb, v_b_top])
    f_back.material_index = mat_trim

    y_min, y_max = cy - d2 + trim_thick, cy + d2 - trim_thick
    for c in range(courses):
        t0, t1 = c / courses, (c + 1) / courses
        xl0, zl0 = cx - w2 * (1.0 - t0), z_base + h * t0
        xl1, zl1 = cx - w2 * (1.0 - t1), z_base + h * t1
        v0 = bm.verts.new(Vector((xl0, y_min, zl0 + 0.025)))
        v1 = bm.verts.new(Vector((xl0, y_max, zl0 + 0.025)))
        v2 = bm.verts.new(Vector((xl1, y_max, zl1)))
        v3 = bm.verts.new(Vector((xl1, y_min, zl1)))
        # Winding: reversed so the normal points up/out. [v0, v1, v2, v3] faced down and
        # inward, so every model using this helper rendered its roof dark or, with
        # single-sided materials, not at all (the "cream plaster block" bug).
        bm.faces.new([v3, v2, v1, v0]).material_index = mat_tile

        xr0, zr0 = cx + w2 * (1.0 - t0), z_base + h * t0
        xr1, zr1 = cx + w2 * (1.0 - t1), z_base + h * t1
        vr0 = bm.verts.new(Vector((xr0, y_max, zr0 + 0.025)))
        vr1 = bm.verts.new(Vector((xr0, y_min, zr0 + 0.025)))
        vr2 = bm.verts.new(Vector((xr1, y_min, zr1)))
        vr3 = bm.verts.new(Vector((xr1, y_max, zr1)))
        bm.faces.new([vr3, vr2, vr1, vr0]).material_index = mat_tile

    add_box(bm, cx, cy, r_z + 0.08, 0.32, d2 * 2.0, 0.16, mat_idx=mat_tile)

def _ht_end_extent(kind, timber, proud):
    """How far (m) a wall's plates run past its plaster end, for one end joint kind.

    Each framed wall's timbers occupy the band [proud - t/2, proud + t/2] in front of its
    plaster. At an outside corner the neighbour's band crosses this wall's line at
    s in [-(proud + t/2), -(proud - t/2)], so:
      "flush": plates stop at the plaster end (legacy; a free-standing wall end)
      "post":  this wall owns the corner: plates run through to the neighbour's outer face
      "butt":  the neighbour owns the corner: plates stop against its post/plates
    """
    if kind == "post":
        return proud + timber * 0.5
    if kind == "butt":
        return proud - timber * 0.5
    return 0.0


def add_half_timber_wall(bm, a, b, z0, z1, outward, mat_timber, mat_glass=None,
                         bay=1.5, timber=0.18, proud=0.05, rails=(1.0, 2.5), windows=True,
                         ends=("flush", "flush")):
    """Timber frame (szachulec) over a plaster wall running from a to b, between z0 and z1.

    a, b: (x, y) corners on the plaster face; outward: unit vector out of the wall.
    Square timbers sit `proud` m in front of the plaster, so the infill reads as recessed
    and catches shadow along every member (KEY_FINDINGS section 13).
    Layout: sill and head plates, posts every ~`bay` m, long corner braces in the two
    end bays, and in the inner bays two rails (window sill / lintel) with a St. Andrew's
    cross below and a glazed window between them in alternate bays.

    ends: joint at (a, b), each "flush" (default, free wall end), "post" or "butt".
    Where two framed walls meet at an outside corner, exactly one of them must use "post"
    there and the other "butt". The owner then draws one square corner post on the outer
    corner (centred `proud` beyond the plaster line on both walls) and runs its plates
    through, so the two frames close into one solid corner instead of leaving a
    proud x proud notch between two separate end posts. Walls listed head-to-tail around
    a footprint simply use ends=("post", "butt").
    """
    a = Vector((a[0], a[1], 0.0))
    b = Vector((b[0], b[1], 0.0))
    length = (b - a).length
    t = (b - a) / length
    out = Vector(outward).normalized()
    off = out * proud
    n = max(3, round(length / bay))
    step = length / n
    h = timber * 0.5
    z_sill, z_lintel = z0 + rails[0], z0 + rails[1]
    end_a, end_b = ends

    def P(s, z):
        return a + t * s + off + Vector((0.0, 0.0, z))

    def beam(p, q, size=timber):
        add_timber_beam(bm, p, q, width=size, depth=size, mat_idx=mat_timber)

    s_lo = -_ht_end_extent(end_a, timber, proud)
    s_hi = length + _ht_end_extent(end_b, timber, proud)
    beam(P(s_lo, z0 + h), P(s_hi, z0 + h))                   # sill plate
    beam(P(s_lo, z1 - h), P(s_hi, z1 - h))                   # head plate
    for i in range(n + 1):                                    # posts
        s = min(max(i * step, h), length - h)
        end = end_a if i == 0 else end_b if i == n else None
        if end == "butt":
            continue                                          # the neighbour's corner post
        if end == "post":
            s = -proud if i == 0 else length + proud          # one post on the outer corner
        beam(P(s, z0 + timber), P(s, z1 - timber))

    for i in range(n):
        s0, s1 = i * step + h, (i + 1) * step - h
        if i == 0 and end_a != "flush":
            s0 = h - proud                                    # inner face of the corner post
        if i == n - 1 and end_b != "flush":
            s1 = length - (h - proud)
        if i == 0:                                            # corner brace, foot at the corner
            beam(P(s0, z0 + timber), P(s1, z1 - timber), timber * 0.85)
            continue
        if i == n - 1:
            beam(P(s1, z0 + timber), P(s0, z1 - timber), timber * 0.85)
            continue
        beam(P(s0, z_sill), P(s1, z_sill), timber * 0.9)      # window-sill rail
        beam(P(s0, z_lintel), P(s1, z_lintel), timber * 0.9)  # lintel rail
        beam(P(s0, z0 + timber), P(s1, z_sill - h), timber * 0.75)   # St. Andrew's cross
        beam(P(s1, z0 + timber), P(s0, z_sill - h), timber * 0.75)
        if windows and mat_glass is not None and i % 2 == 1:
            c = a + t * ((s0 + s1) * 0.5) + out * 0.02
            ww, wh = step - timber * 2.2, (z_lintel - z_sill) - timber * 1.6
            along_x = abs(t.x) > 0.5
            zc = (z_sill + z_lintel) * 0.5
            add_box(bm, c.x, c.y, zc, ww if along_x else 0.04, 0.04 if along_x else ww, wh, mat_idx=mat_glass)
            # leaded-window mullion cross, just proud of the glass
            m = c + out * 0.03 + Vector((0, 0, zc))      # c lies on z = 0; lift to window centre
            add_timber_beam(bm, m + Vector((0, 0, -wh * 0.5)), m + Vector((0, 0, wh * 0.5)),
                            width=0.06, depth=0.06, mat_idx=mat_timber)
            add_timber_beam(bm, m - t * (ww * 0.5) + Vector((0, 0, wh * 0.08)), m + t * (ww * 0.5) + Vector((0, 0, wh * 0.08)),
                            width=0.06, depth=0.06, mat_idx=mat_timber)


def add_gable_roof(bm, cx, cy, z_base, w, d, h, overhang, mat_roof, mat_plaster, mat_timber,
                   mat_glass=None, timber=0.18, proud=0.05, frame=True, loft_windows=2,
                   bargeboards=True, eave_lip=0.0, frame_wrap=False):
    """Saddle roof (ridge along Y) with proper gable walls instead of tiled gable ends.

    Slopes follow add_sloped_roof (eaves at z_base, extended by `overhang`). The gables sit
    on the wall planes y = cy +/- d/2 as pentagons in `mat_plaster` (plaster, boards or
    brick) that close up under the eaves.
      frame:        timber frame on the gable (sill, king post, collar, struts); the king
                    post and collar run up to the underside of the roof
      loft_windows: 0, 1 (centred) or 2 small gable windows (needs mat_glass)
      bargeboards:  timber verge boards along the gable edges
      eave_lip:     thickness (m) of a roof-material fascia under each eave, so thatch
                    reads as a thick bundle instead of a paper-thin sheet
      frame_wrap:   the walls below are framed with add_half_timber_wall corner posts
                    (same timber/proud): run the gable sill out over those posts so the
                    corner column is capped instead of stepping in at the wall line
    """
    w2, d2 = w * 0.5 + overhang, d * 0.5 + overhang
    ridge = z_base + h
    v0 = bm.verts.new(Vector((cx - w2, cy - d2, z_base)))
    v1 = bm.verts.new(Vector((cx + w2, cy - d2, z_base)))
    v2 = bm.verts.new(Vector((cx + w2, cy + d2, z_base)))
    v3 = bm.verts.new(Vector((cx - w2, cy + d2, z_base)))
    r0 = bm.verts.new(Vector((cx, cy - d2, ridge)))
    r1 = bm.verts.new(Vector((cx, cy + d2, ridge)))
    bm.faces.new([v0, r0, r1, v3]).material_index = mat_roof
    bm.faces.new([v1, v2, r1, r0]).material_index = mat_roof
    add_box(bm, cx, cy, ridge + 0.05, 0.30, d2 * 2.0, 0.12, mat_idx=mat_roof)   # ridge cap
    if eave_lip > 0:
        for sx in (-1.0, 1.0):
            add_box(bm, cx + sx * (w2 - 0.2), cy, z_base - eave_lip * 0.5 + 0.02, 0.4, d2 * 2.0, eave_lip, mat_idx=mat_roof)

    hw = w * 0.5
    z_edge = z_base + h * (overhang / w2)        # roof height straight above the wall line
    for sgn in (-1.0, 1.0):
        y = cy + sgn * d * 0.5
        pts = [(cx - hw, z_base), (cx + hw, z_base), (cx + hw, z_edge), (cx, ridge), (cx - hw, z_edge)]
        if sgn > 0:
            pts.reverse()                        # keep the face normal pointing out of the gable
        verts = [bm.verts.new(Vector((px, y, pz))) for px, pz in pts]
        bm.faces.new(verts).material_index = mat_plaster

        if bargeboards:                                          # verge boards
            ye = cy + sgn * (d2 - 0.08)
            add_timber_beam(bm, Vector((cx - w2, ye, z_base)), Vector((cx, ye, ridge)), width=0.16, depth=0.18, mat_idx=mat_timber)
            add_timber_beam(bm, Vector((cx + w2, ye, z_base)), Vector((cx, ye, ridge)), width=0.16, depth=0.18, mat_idx=mat_timber)

        yb = y + sgn * proud
        zc = z_base + h * 0.42                                   # collar height
        if frame:                                                # gable frame, proud of the infill
            ht = timber * 0.5
            # Collar and king post end where their upper corners touch the roof plane
            # (roof line at height z is x = w2 * (1 - (z - z_base) / h)), so no plaster
            # sliver shows between the frame and the verge.
            xc = w2 * (1.0 - (zc + ht - z_base) / h)
            z_king = ridge - h * ht / w2
            xs = hw + (proud + ht if frame_wrap else 0.0)        # sill over the corner posts
            add_timber_beam(bm, Vector((cx - xs, yb, z_base + ht)), Vector((cx + xs, yb, z_base + ht)),
                            width=timber, depth=timber, mat_idx=mat_timber)
            add_timber_beam(bm, Vector((cx, yb, z_base + timber)), Vector((cx, yb, z_king)),
                            width=timber, depth=timber, mat_idx=mat_timber)
            add_timber_beam(bm, Vector((cx - xc, yb, zc)), Vector((cx + xc, yb, zc)),
                            width=timber, depth=timber, mat_idx=mat_timber)
            for sx in (-1.0, 1.0):
                add_timber_beam(bm, Vector((cx + sx * hw * 0.8, yb, z_base + timber)), Vector((cx + sx * 0.35, yb, zc - 0.1)),
                                width=timber * 0.8, depth=timber * 0.8, mat_idx=mat_timber)
        if mat_glass is not None and loft_windows:               # small loft windows
            xs = (0.0,) if loft_windows == 1 else (-1.0, 1.0)
            for wx in xs:
                add_box(bm, cx + wx, y + sgn * 0.02, zc + (ridge - zc) * 0.3, 0.55, 0.04, 0.7, mat_idx=mat_glass)


def add_wall_window(bm, c, along, out, w, h, mat_glass, mat_frame, frame=0.12, pointed=False,
                    shutters_mat=None):
    """Framed window on an axis-aligned wall.

    c: Vector at the window centre on the wall face; along: wall direction; out: outward normal.
    Dark glass sits just proud of the wall, framed by jambs, a deeper sill and a head.
    pointed=True gives a Gothic lancet head (two raking members over a glass triangle).
    shutters_mat: if set, two open board shutters hinge out beside the window.
    """
    along = Vector(along).normalized()
    out = Vector(out).normalized()
    up = Vector((0.0, 0.0, 1.0))
    g = c + out * 0.02
    ax = abs(along.x) > 0.5
    add_box(bm, g.x, g.y, g.z, w if ax else 0.04, 0.04 if ax else w, h, mat_idx=mat_glass)
    f = c + out * (frame * 0.5)
    hw, hh = w * 0.5 + frame * 0.5, h * 0.5 + frame * 0.5

    def beam(p, q, size=frame):
        add_timber_beam(bm, p, q, width=size, depth=size, mat_idx=mat_frame)

    beam(f - along * hw - up * hh, f - along * hw + up * hh)                    # jambs
    beam(f + along * hw - up * hh, f + along * hw + up * hh)
    beam(f - along * (hw + 0.08) - up * hh + out * 0.03,
         f + along * (hw + 0.08) - up * hh + out * 0.03, frame * 1.3)          # sill
    if pointed:
        apex = f + up * (hh + w * 0.55)
        beam(f - along * hw + up * hh, apex)
        beam(f + along * hw + up * hh, apex)
        tri = [g - along * (w * 0.5) + up * (h * 0.5), g + along * (w * 0.5) + up * (h * 0.5),
               g + up * (h * 0.5 + w * 0.5)]
        if (tri[1] - tri[0]).cross(tri[2] - tri[1]).dot(out) < 0:
            tri.reverse()                                                        # face outward
        bm.faces.new([bm.verts.new(p) for p in tri]).material_index = mat_glass
    else:
        beam(f - along * hw + up * hh, f + along * hw + up * hh)               # head
    if shutters_mat is not None:
        for s in (-1.0, 1.0):
            p = c + along * s * (hw + w * 0.25 + 0.04) + out * 0.04
            add_box(bm, p.x, p.y, p.z, (w * 0.5) if ax else 0.05, 0.05 if ax else (w * 0.5), h, mat_idx=shutters_mat)


def add_log_corner_crossings(bm, cx, cy, w, d, z0, z1, course=0.25, stub=0.38, mat_idx=0):
    """Saddle-notched corners (wiencie): log ends cross past each corner, alternating
    direction every course as the wall logs interlock."""
    n = int(round((z1 - z0) / course))
    for k in range(n):
        z = z0 + (k + 0.5) * course
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                x, y = cx + sx * w * 0.5, cy + sy * d * 0.5
                if k % 2 == 0:   # log of the X-running wall pokes out in X
                    p, q = Vector((x - sx * 0.15, y, z)), Vector((x + sx * stub, y, z))
                else:            # log of the Y-running wall pokes out in Y
                    p, q = Vector((x, y - sy * 0.15, z)), Vector((x, y + sy * stub, z))
                add_timber_beam(bm, p, q, width=course * 0.95, depth=course * 0.92, mat_idx=mat_idx)


def add_crow_step_gable(bm, cx, y, sgn, z_base, w, steps, step_h, mat_brick, mat_plaster,
                        thick=0.5, niches=True):
    """Brick Gothic crow-stepped gable (szczyt schodkowy) standing proud of the roof.

    sgn: -1 for a gable facing -Y, +1 for +Y. Each step narrows by w / (steps + 1) and is
    capped with plaster coping; plaster pinnacles (sterczyny) stand on every step end, and
    white lancet blind niches (blendy) decorate the face.
    """
    yc = y + sgn * thick * 0.5
    shrink = w / (steps + 1)
    for s in range(steps):
        sw = w - s * shrink
        sz = z_base + s * step_h
        add_box(bm, cx, yc, sz + step_h * 0.5, sw, thick, step_h, mat_idx=mat_brick)
        for sx in (-1.0, 1.0):
            ex = cx + sx * (sw * 0.5 - 0.22)
            add_box(bm, ex, yc, sz + step_h + 0.04, 0.5, thick + 0.08, 0.08, mat_idx=mat_plaster)   # coping
            add_box(bm, ex, yc, sz + step_h + 0.5, 0.32, 0.32, 0.9, mat_idx=mat_plaster)           # pinnacle
    add_box(bm, cx, yc, z_base + steps * step_h + 0.04, w - (steps - 1) * shrink, thick + 0.08, 0.08, mat_idx=mat_plaster)
    if niches:
        yf = y + sgn * (thick + 0.02)
        nw = 0.55
        for i in range(-(steps - 1), steps, 2):
            nx = cx + i * shrink * 0.5
            # tallest step whose half-width still clears this niche
            top_s = max(s for s in range(steps) if (w - s * shrink) * 0.5 - 0.35 > abs(nx - cx) + nw * 0.5)
            z_top = z_base + (top_s + 1) * step_h - 0.45
            z_bot = z_base + 0.4
            if z_top - z_bot < 0.8:
                continue
            add_box(bm, nx, yf, (z_bot + z_top) * 0.5, nw, 0.04, z_top - z_bot, mat_idx=mat_plaster)
            tri = [Vector((nx - nw * 0.5, yf, z_top)), Vector((nx + nw * 0.5, yf, z_top)), Vector((nx, yf, z_top + nw * 0.55))]
            if sgn > 0:
                tri.reverse()
            bm.faces.new([bm.verts.new(p) for p in tri]).material_index = mat_plaster


def add_ashlar_chimney(bm, cx, cy, z_base, w, d, h, mat_stone=0, mat_soot=1):
    h_base, h_taper, h_shaft, h_cap = h * 0.45, h * 0.10, h * 0.40, h * 0.05
    add_box(bm, cx, cy, z_base + h_base * 0.5, w, d, h_base, mat_idx=mat_stone)
    z_taper = z_base + h_base
    w_top, d_top = w * 0.78, d * 0.78
    add_box(bm, cx, cy, z_taper + h_taper * 0.5, (w + w_top) * 0.5, (d + d_top) * 0.5, h_taper, mat_idx=mat_stone)
    z_shaft = z_taper + h_taper
    add_box(bm, cx, cy, z_shaft + h_shaft * 0.5, w_top, d_top, h_shaft, mat_idx=mat_stone)
    z_cap = z_shaft + h_shaft
    add_box(bm, cx, cy, z_cap + h_cap * 0.5, w_top + 0.22, d_top + 0.22, h_cap, mat_idx=mat_stone)
    add_box(bm, cx, cy, z_cap + h_cap + 0.01, w_top * 0.6, d_top * 0.6, 0.02, mat_idx=mat_soot)

def add_barrel(bm, cx, cy, cz, radius=0.45, height=1.1, segs=10, mat_wood=0, mat_iron=1):
    add_cylinder(bm, cx, cy, cz, radius, height, segs=segs, mat_idx=mat_wood)
    # Iron binding hoops
    add_cylinder(bm, cx, cy, cz - height * 0.3, radius * 1.02, 0.06, segs=segs, mat_idx=mat_iron)
    add_cylinder(bm, cx, cy, cz + height * 0.3, radius * 1.02, 0.06, segs=segs, mat_idx=mat_iron)

def add_barrel_pyramid(bm, cx, cy, cz, rot_y=False, mat_wood=0, mat_iron=1):
    """Pyramid of 6 beer casks."""
    r = 0.44
    h = 1.05
    # Bottom row of 3
    for i in [-1, 0, 1]:
        by = cy + i * (h * 1.05) if not rot_y else cy
        bx = cx if not rot_y else cx + i * (h * 1.05)
        add_barrel(bm, bx, by, cz + r, radius=r, height=h, mat_wood=mat_wood, mat_iron=mat_iron)
    # Middle row of 2
    for i in [-0.5, 0.5]:
        by = cy + i * (h * 1.05) if not rot_y else cy
        bx = cx if not rot_y else cx + i * (h * 1.05)
        add_barrel(bm, bx, by, cz + r * 2.6, radius=r, height=h, mat_wood=mat_wood, mat_iron=mat_iron)
    # Top barrel
    add_barrel(bm, cx, cy, cz + r * 4.2, radius=r, height=h, mat_wood=mat_wood, mat_iron=mat_iron)

def add_water_trough(bm, cx, cy, cz, w, d, h, mat_wood=0, mat_water=1):
    thick = 0.10
    add_box(bm, cx, cy, cz + thick * 0.5, w, d, thick, mat_idx=mat_wood) # bottom
    add_box(bm, cx, cy - d * 0.5 + thick * 0.5, cz + h * 0.5, w, thick, h, mat_idx=mat_wood) # front
    add_box(bm, cx, cy + d * 0.5 - thick * 0.5, cz + h * 0.5, w, thick, h, mat_idx=mat_wood) # back
    add_box(bm, cx - w * 0.5 + thick * 0.5, cy, cz + h * 0.5, thick, d, h, mat_idx=mat_wood) # left
    add_box(bm, cx + w * 0.5 - thick * 0.5, cy, cz + h * 0.5, thick, d, h, mat_idx=mat_wood) # right
    # Water surface
    add_box(bm, cx, cy, cz + h * 0.82, w - thick * 2, d - thick * 2, 0.05, mat_idx=mat_water)

def add_tavern_table_and_benches(bm, cx, cy, cz, mat_wood=0):
    # Table top
    add_box(bm, cx, cy, cz + 0.75, 1.2, 2.6, 0.08, mat_idx=mat_wood)
    # Table trestle legs
    add_timber_beam(bm, Vector((cx - 0.4, cy - 0.9, cz)), Vector((cx, cy - 0.9, cz + 0.7)), width=0.12, depth=0.12, mat_idx=mat_wood)
    add_timber_beam(bm, Vector((cx + 0.4, cy - 0.9, cz)), Vector((cx, cy - 0.9, cz + 0.7)), width=0.12, depth=0.12, mat_idx=mat_wood)
    add_timber_beam(bm, Vector((cx - 0.4, cy + 0.9, cz)), Vector((cx, cy + 0.9, cz + 0.7)), width=0.12, depth=0.12, mat_idx=mat_wood)
    add_timber_beam(bm, Vector((cx + 0.4, cy + 0.9, cz)), Vector((cx, cy + 0.9, cz + 0.7)), width=0.12, depth=0.12, mat_idx=mat_wood)
    # Two benches
    for bx in [-0.85, 0.85]:
        add_box(bm, cx + bx, cy, cz + 0.45, 0.35, 2.6, 0.06, mat_idx=mat_wood)
        add_box(bm, cx + bx, cy - 0.9, cz + 0.22, 0.25, 0.10, 0.44, mat_idx=mat_wood)
        add_box(bm, cx + bx, cy + 0.9, cz + 0.22, 0.25, 0.10, 0.44, mat_idx=mat_wood)

def add_beehive_dome(bm, cx, cy, z_base, radius, height, segs_u=14, segs_v=6, mat_idx=0):
    rings = []
    for v in range(segs_v):
        phi = (v / segs_v) * (math.pi * 0.5)
        r = radius * math.cos(phi)
        z = z_base + height * math.sin(phi)
        ring_verts = []
        for u in range(segs_u):
            theta = (u / segs_u) * (math.pi * 2.0)
            x = cx + r * math.cos(theta)
            y = cy + r * math.sin(theta)
            ring_verts.append(bm.verts.new(Vector((x, y, z))))
        rings.append(ring_verts)
    top_vert = bm.verts.new(Vector((cx, cy, z_base + height)))
    for v in range(segs_v - 1):
        r1, r2 = rings[v], rings[v + 1]
        for u in range(segs_u):
            nxt = (u + 1) % segs_u
            f = bm.faces.new([r1[u], r1[nxt], r2[nxt], r2[u]])
            f.material_index = mat_idx
    for u in range(segs_u):
        nxt = (u + 1) % segs_u
        f = bm.faces.new([rings[-1][u], rings[-1][nxt], top_vert])
        f.material_index = mat_idx

def add_curved_pretzel(bm, cx, cy, cz, size=0.7, mat_gold=0):
    segs = 16
    r_x = size * 0.55
    r_z = size * 0.42
    thick = 0.075
    points = []
    for i in range(segs):
        ang = (i / segs) * math.pi * 2.0
        x = cx + r_x * math.sin(ang)
        z = cz + r_z * (math.cos(ang) - 0.25 * (math.sin(ang)**2))
        points.append(Vector((x, cy, z)))
    for i in range(segs):
        p1 = points[i]
        p2 = points[(i + 1) % segs]
        add_timber_beam(bm, p1, p2, width=thick, depth=thick, mat_idx=mat_gold)
    p_center = Vector((cx, cy, cz - r_z * 0.2))
    p_left_lobe = Vector((cx - r_x * 0.42, cy, cz + r_z * 0.15))
    p_right_lobe = Vector((cx + r_x * 0.42, cy, cz + r_z * 0.15))
    add_timber_beam(bm, p_center, p_left_lobe, width=thick * 0.85, depth=thick * 0.85, mat_idx=mat_gold)
    add_timber_beam(bm, p_center, p_right_lobe, width=thick * 0.85, depth=thick * 0.85, mat_idx=mat_gold)

def add_flour_chute(bm, cx, cy, z_top, length=1.8, width=0.55, depth=0.18, angle_deg=35, mat_wood=0):
    rad = math.radians(angle_deg)
    dx = length * math.cos(rad)
    dz = -length * math.sin(rad)
    p_start = Vector((cx, cy, z_top))
    p_end = Vector((cx + dx, cy, z_top + dz))
    add_timber_beam(bm, p_start, p_end, width=width, depth=0.06, mat_idx=mat_wood)
    add_timber_beam(bm, p_start + Vector((0, -width*0.5, depth*0.5)), p_end + Vector((0, -width*0.5, depth*0.5)), width=0.04, depth=depth, mat_idx=mat_wood)
    add_timber_beam(bm, p_start + Vector((0, width*0.5, depth*0.5)), p_end + Vector((0, width*0.5, depth*0.5)), width=0.04, depth=depth, mat_idx=mat_wood)
    add_timber_beam(bm, Vector((cx, cy, z_top - 0.9)), p_end - Vector((dx * 0.3, 0, dz * 0.3)), width=0.10, depth=0.10, mat_idx=mat_wood)

def add_prop_firewood_pile(bm, cx, cy, cz, w=1.8, d=1.1, h=1.4, mat_bark=0, mat_end=1):
    rows, cols = 4, 5
    log_len, r_log = d, 0.11
    dx, dz = w / cols, h / rows
    for r in range(rows):
        n_logs = cols if r % 2 == 0 else cols - 1
        x_start = cx - (w * 0.5) + (dx * 0.5) + (dx * 0.25 if r % 2 == 1 else 0)
        z = cz + (r + 0.5) * dz
        for c in range(n_logs):
            x = x_start + c * dx
            p1 = Vector((x, cy - log_len * 0.5, z))
            p2 = Vector((x, cy + log_len * 0.5, z))
            add_timber_beam(bm, p1, p2, width=r_log*1.9, depth=r_log*1.9, mat_idx=mat_bark)
            add_box(bm, x, cy - log_len * 0.5 - 0.01, z, r_log * 1.6, 0.02, r_log * 1.6, mat_idx=mat_end)
            add_box(bm, x, cy + log_len * 0.5 + 0.01, z, r_log * 1.6, 0.02, r_log * 1.6, mat_idx=mat_end)

def add_prop_flour_sacks(bm, positions, mat_sack=0):
    for pos in positions:
        x, y, z, rot = pos
        add_box(bm, x, y, z + 0.35, 0.65, 0.52, 0.68, mat_idx=mat_sack)
        add_box(bm, x, y, z + 0.72, 0.24, 0.22, 0.12, mat_idx=mat_sack)
        add_box(bm, x, y, z + 0.81, 0.32, 0.28, 0.08, mat_idx=mat_sack)


def apply_material_overrides(obj, name):
    for old, new in MODEL_MATERIAL_OVERRIDES.get(name, {}).items():
        new_mat = bpy.data.materials.get(new)
        for i, m in enumerate(obj.data.materials):
            if m is not None and m.name == old:
                obj.data.materials[i] = new_mat


def add_world_uvs(obj):
    """UVs in metres (1 UV unit = 1 m); the runtime sets texture.repeat = 1 / tile_m.

    Per face, by its normal n:
      - near-horizontal faces (ground, tops, decks): planar X/Y.
      - everything else: u along the face's horizontal tangent t = Z x n,
        v along b = n x t, which is world-up on walls and up-slope on roofs.
        So brick courses and log rows stay horizontal and roof textures put the
        ridge at the top of the image, consistent across all buildings.
      - UV_ALONG_LENGTH materials: u along the face's longest edge, so wood grain
        follows diagonal braces and posts.
    Blender's glTF exporter writes v' = 1 - v; with three.js textures at flipY = false
    that keeps +v = image up.
    """
    mesh = obj.data
    uv = mesh.uv_layers.new(name="UVMap").data
    up = Vector((0.0, 0.0, 1.0))
    mat_names = [m.name if m else "" for m in mesh.materials]
    verts = mesh.vertices
    for poly in mesh.polygons:
        n = poly.normal
        mname = mat_names[poly.material_index] if poly.material_index < len(mat_names) else ""
        if mname in UV_ALONG_LENGTH:
            vids = list(poly.vertices)
            best, t = -1.0, None
            for i in range(len(vids)):
                e = verts[vids[(i + 1) % len(vids)]].co - verts[vids[i]].co
                e = e - n * e.dot(n)                      # keep it in the face plane
                if e.length > best:
                    best, t = e.length, e
            t = t.normalized() if best > 1e-6 else Vector((1.0, 0.0, 0.0))
            b = n.cross(t).normalized()
        elif abs(n.z) > 0.95:
            t, b = Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0 if n.z > 0 else -1.0, 0.0))
        else:
            t = up.cross(n)
            t = t.normalized() if t.length > 1e-6 else Vector((1.0, 0.0, 0.0))
            b = n.cross(t).normalized()
        for li in poly.loop_indices:
            co = verts[mesh.loops[li].vertex_index].co
            uv[li].uv = (co.dot(t), co.dot(b))


def export_object(obj, name):
    apply_material_overrides(obj, name)
    add_world_uvs(obj)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"{name}.glb")
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True
    )
    print(f"Exported: {filepath} ({os.path.getsize(filepath):,} bytes)")

# =============================================================
# Landmark helpers (_lm_*): oriented closed solids, Brick Gothic details, roofs, spires.
# Used by the town hall, Szmatruz, church, monastery, donjon and the two gates.
# _lm_extrude fixes its own winding, so callers may pass any in-plane axes and every
# face (walls, roofs, spires) comes out wound outward.
# =============================================================
_LM_Z = Vector((0.0, 0.0, 1.0))


def _lm_extrude(bm, pts, origin, u, v, n, depth, mat):
    """Convex polygon pts [(a, b)] in the plane origin + u*a + v*b, extruded by n*depth (> 0)."""
    o, u, v, n = Vector(origin), Vector(u), Vector(v), Vector(n).normalized()
    P = [o + u * a + v * b for a, b in pts]
    nrm = Vector((0.0, 0.0, 0.0))
    for i in range(len(P)):
        nrm += P[i].cross(P[(i + 1) % len(P)])
    if nrm.dot(n) < 0:
        P.reverse()                                   # ccw around +n
    vp = [bm.verts.new(p) for p in P]
    vq = [bm.verts.new(p + n * depth) for p in P]
    faces = [bm.faces.new(list(reversed(vp))), bm.faces.new(vq)]
    k = len(P)
    for i in range(k):
        j = (i + 1) % k
        faces.append(bm.faces.new([vp[i], vp[j], vq[j], vq[i]]))
    for f in faces:
        f.material_index = mat
    return faces


def _lm_hexa(bm, pts, mat):
    """Hexahedron from 8 corners in add_box order (bottom -x-y, +x-y, +x+y, -x+y; then top)."""
    v = [bm.verts.new(Vector(p)) for p in pts]
    for a, b, c, d in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (0, 4, 7, 3), (1, 2, 6, 5)):
        bm.faces.new([v[a], v[b], v[c], v[d]]).material_index = mat


def _lm_obox(bm, c, along, out, w, d, h, mat):
    """Box centred on c, w along `along`, d along `out`, h vertical (any horizontal orientation)."""
    along, out = Vector(along).normalized(), Vector(out).normalized()
    _lm_extrude(bm, [(-w * 0.5, -h * 0.5), (w * 0.5, -h * 0.5), (w * 0.5, h * 0.5), (-w * 0.5, h * 0.5)],
                Vector(c) - out * (d * 0.5), along, _LM_Z, out, d, mat)


def _lm_ngon_prism(bm, cx, cy, z0, z1, r, sides, mat, r_top=None, rot=None, caps=True):
    """Vertical n-gon prism / frustum (r = circumradius). Default rot puts a flat facing +X."""
    rot = math.pi / sides if rot is None else rot
    r_top = r if r_top is None else r_top
    bot, top = [], []
    for i in range(sides):
        a = rot + 2.0 * math.pi * i / sides
        bot.append(bm.verts.new(Vector((cx + r * math.cos(a), cy + r * math.sin(a), z0))))
        top.append(bm.verts.new(Vector((cx + r_top * math.cos(a), cy + r_top * math.sin(a), z1))))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new([bot[i], bot[j], top[j], top[i]]).material_index = mat
    if caps:
        bm.faces.new(top).material_index = mat
        bm.faces.new(list(reversed(bot))).material_index = mat


def _lm_spire(bm, cx, cy, z0, r, h, sides, mat, rot=None, base_cap=True):
    """n-sided spire / helm / cone from a ring of circumradius r at z0 to an apex h above."""
    rot = math.pi / sides if rot is None else rot
    ring = [bm.verts.new(Vector((cx + r * math.cos(rot + 2.0 * math.pi * i / sides),
                                 cy + r * math.sin(rot + 2.0 * math.pi * i / sides), z0))) for i in range(sides)]
    apex = bm.verts.new(Vector((cx, cy, z0 + h)))
    for i in range(sides):
        bm.faces.new([ring[i], ring[(i + 1) % sides], apex]).material_index = mat
    if base_cap:
        bm.faces.new(list(reversed(ring))).material_index = mat


def _lm_finial(bm, x, y, z, mat_rod, mat_orb, h=1.6, cross=False):
    """Iron spike with a gilded orb (and optional cross) on a spire apex at z."""
    add_timber_beam(bm, Vector((x, y, z - 0.3)), Vector((x, y, z + h)), width=0.09, depth=0.09, mat_idx=mat_rod)
    zo = z + h * 0.35
    _lm_ngon_prism(bm, x, y, zo, zo + 0.12, 0.13, 8, mat_orb, r_top=0.22)
    _lm_ngon_prism(bm, x, y, zo + 0.12, zo + 0.26, 0.22, 8, mat_orb, r_top=0.13)
    if cross:
        add_timber_beam(bm, Vector((x - 0.35, y, z + h - 0.35)), Vector((x + 0.35, y, z + h - 0.35)),
                        width=0.08, depth=0.08, mat_idx=mat_rod)


def _lm_lancet(bm, c, along, out, w, h, mat_glass, mat_frame, frame=0.15, rise=0.6,
               mullion=False, sill=True, proud=0.03):
    """Pointed (lancet) opening on any vertical wall. c = bottom-centre on the wall face.

    Glass (or a plank door leaf) fills a pentagon w wide, h to the springing, w*rise to the
    apex; the frame (jambs, two raking head members, optional sill) stands proud of the wall.
    mat_glass=None draws only the frame (e.g. a gate portal); mat_frame=None only the glass.
    """
    c, along, out = Vector(c), Vector(along).normalized(), Vector(out).normalized()
    top = h + w * rise
    if mat_glass is not None:
        _lm_extrude(bm, [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, h), (0.0, top), (-w * 0.5, h)],
                    c - out * 0.02, along, _LM_Z, out, 0.02 + proud, mat_glass)
    if mat_frame is None:
        return
    f = c + out * (frame * 0.5)
    hw = w * 0.5 + frame * 0.5

    def beam(p, q, s=frame):
        add_timber_beam(bm, p, q, width=s, depth=s, mat_idx=mat_frame)

    beam(f - along * hw, f - along * hw + _LM_Z * h)
    beam(f + along * hw, f + along * hw + _LM_Z * h)
    apex = f + _LM_Z * (top + frame * 0.6)
    beam(f - along * hw + _LM_Z * h, apex)
    beam(f + along * hw + _LM_Z * h, apex)
    if sill:
        beam(f - along * (hw + 0.1) + out * 0.03, f + along * (hw + 0.1) + out * 0.03, frame * 1.3)
    if mullion and mat_glass is not None:
        beam(f + out * 0.01, f + out * 0.01 + _LM_Z * (h + w * rise * 0.45), frame * 0.55)


def _lm_blind(bm, c, along, out, w, h, mat, proud=0.05, rise=0.6):
    """Blind lancet niche panel (blenda) standing `proud` off the wall; c = bottom-centre."""
    c, along, out = Vector(c), Vector(along).normalized(), Vector(out).normalized()
    _lm_extrude(bm, [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, h), (0.0, h + w * rise), (-w * 0.5, h)],
                c - out * 0.02, along, _LM_Z, out, proud + 0.02, mat)


def _lm_disc(bm, c, along, out, r, mat, proud=0.06, segs=12):
    """Round disc (clock dial) centred on c, standing `proud` off the wall."""
    c, along, out = Vector(c), Vector(along).normalized(), Vector(out).normalized()
    pts = [(r * math.cos(2.0 * math.pi * i / segs), r * math.sin(2.0 * math.pi * i / segs)) for i in range(segs)]
    _lm_extrude(bm, pts, c - out * 0.02, along, _LM_Z, out, proud + 0.02, mat)


def _lm_buttress(bm, p, out, along, width, tiers, mat, z0=0.0, back=0.05):
    """Stepped Gothic buttress at wall point p, projecting along `out`.

    tiers: [(height, depth), ...] bottom-up with decreasing depth; every offset and the top
    get a 45-degree weathering slope. back: how far the body reaches into the wall (use
    ~0.6 on convex corners so no sliver gap shows). Returns the top z.
    """
    p = Vector((p[0], p[1], 0.0))
    out, along = Vector(out).normalized(), Vector(along).normalized()
    o = p - along * (width * 0.5)
    z = z0
    for k, (hgt, dep) in enumerate(tiers):
        nxt = tiers[k + 1][1] if k + 1 < len(tiers) else 0.0
        zt = z + hgt
        dz = dep - nxt
        if nxt > 0:
            pts = [(-back, z), (dep, z), (dep, zt), (nxt, zt + dz), (-back, zt + dz)]
        else:
            pts = [(-back, z), (dep, z), (dep, zt), (-back, zt + dz)]
        _lm_extrude(bm, pts, o, out, _LM_Z, along, width, mat)
        z = zt + dz
    return z


def _lm_arcade(bm, o, along, out, piers, pier_w, thick, z_spring, z_top, mat, mat_cap=None,
               rise=0.6, end_piers=True):
    """Open arcade of pointed arches in a wall face. o: point on the face at along-coordinate 0
    and the base height; piers: pier-centre coordinates along `along`; the wall is `thick` deep
    behind the face (away from `out`). Spandrels extruded through the depth give the arches
    real soffits. end_piers=False omits the first/last pier (supplied by another wall)."""
    o, along = Vector(o), Vector(along).normalized()
    n = -Vector(out).normalized()
    hw = pier_w * 0.5
    for i, p in enumerate(piers):
        if not end_piers and i in (0, len(piers) - 1):
            continue
        _lm_extrude(bm, [(p - hw, 0.0), (p + hw, 0.0), (p + hw, z_top), (p - hw, z_top)], o, along, _LM_Z, n, thick, mat)
        if mat_cap is not None:
            _lm_obox(bm, o + along * p + n * (thick * 0.5) + _LM_Z * z_spring, along, n,
                     pier_w + 0.16, thick + 0.16, 0.22, mat_cap)
    for p, q in zip(piers, piers[1:]):
        a, b = p + hw, q - hw
        m = (a + b) * 0.5
        za = min(z_spring + (b - a) * rise, z_top - 0.1)
        _lm_extrude(bm, [(a, z_spring), (m, za), (m, z_top), (a, z_top)], o, along, _LM_Z, n, thick, mat)
        _lm_extrude(bm, [(m, za), (b, z_spring), (b, z_top), (m, z_top)], o, along, _LM_Z, n, thick, mat)


def _lm_saddle_roof(bm, cx, cy, z0, length, span, h, axis, mat, overhang=0.4, end_overhang=0.0, ridge_cap=True):
    """Two roof slopes, ridge along 'x' or 'y', meeting the wall tops at z0 (the eaves drop
    below z0 by the overhang at the same pitch, so there is no gap). Gable ends are left
    open for crow-stepped or plain gables built separately."""
    L2, S2 = length * 0.5 + end_overhang, span * 0.5 + overhang
    ez, rz = z0 - h * overhang / (span * 0.5), z0 + h
    swap = axis == 'y'

    def P(u, v, z):
        return Vector((cx + v, cy + u, z)) if swap else Vector((cx + u, cy + v, z))

    e = [bm.verts.new(P(-L2, -S2, ez)), bm.verts.new(P(L2, -S2, ez)),
         bm.verts.new(P(L2, S2, ez)), bm.verts.new(P(-L2, S2, ez))]
    r0, r1 = bm.verts.new(P(-L2, 0.0, rz)), bm.verts.new(P(L2, 0.0, rz))
    for quad in ([e[0], e[1], r1, r0], [e[2], e[3], r0, r1]):
        bm.faces.new(list(reversed(quad)) if swap else quad).material_index = mat
    if ridge_cap:
        if swap:
            add_box(bm, cx, cy, rz + 0.05, 0.3, 2.0 * L2, 0.14, mat_idx=mat)
        else:
            add_box(bm, cx, cy, rz + 0.05, 2.0 * L2, 0.3, 0.14, mat_idx=mat)


def _lm_hip_roof(bm, cx, cy, z0, w, d, h, mat, overhang=0.3):
    """Hipped roof over a w x d plan (pyramid when square), eaves at z0, ridge along the long side."""
    w2, d2 = w * 0.5 + overhang, d * 0.5 + overhang
    swap = d > w
    a, b = (d2, w2) if swap else (w2, d2)
    rl = max(a - b, 0.0)

    def P(u, v, z):
        return Vector((cx + v, cy + u, z)) if swap else Vector((cx + u, cy + v, z))

    c = [bm.verts.new(P(-a, -b, z0)), bm.verts.new(P(a, -b, z0)), bm.verts.new(P(a, b, z0)), bm.verts.new(P(-a, b, z0))]
    r0 = bm.verts.new(P(-rl, 0.0, z0 + h))
    r1 = bm.verts.new(P(rl, 0.0, z0 + h)) if rl > 1e-3 else r0
    faces = [[c[3], c[0], r0], [c[1], c[2], r1]]
    if r1 is r0:
        faces += [[c[0], c[1], r0], [c[2], c[3], r0]]
    else:
        faces += [[c[0], c[1], r1, r0], [c[2], c[3], r0, r1]]
    for f in faces:
        bm.faces.new(list(reversed(f)) if swap else f).material_index = mat
    return P(-rl, 0.0, z0 + h), P(rl, 0.0, z0 + h)


def _lm_parapet_rect(bm, cx, cy, z, w, d, h, thick, mat, merlon_h=0.0, merlon_w=0.6, pitch=1.2):
    """Rectangular parapet ring (outer size w x d) from z to z+h, optionally crenellated."""
    add_box(bm, cx, cy - d * 0.5 + thick * 0.5, z + h * 0.5, w, thick, h, mat_idx=mat)
    add_box(bm, cx, cy + d * 0.5 - thick * 0.5, z + h * 0.5, w, thick, h, mat_idx=mat)
    add_box(bm, cx - w * 0.5 + thick * 0.5, cy, z + h * 0.5, thick, d - 2.0 * thick, h, mat_idx=mat)
    add_box(bm, cx + w * 0.5 - thick * 0.5, cy, z + h * 0.5, thick, d - 2.0 * thick, h, mat_idx=mat)
    if merlon_h <= 0:
        return
    zc = z + h + merlon_h * 0.5
    n = max(1, int(round((w - merlon_w) / pitch)))
    for i in range(n + 1):
        x = cx - w * 0.5 + merlon_w * 0.5 + i * (w - merlon_w) / n
        for sy in (-1.0, 1.0):
            add_box(bm, x, cy + sy * (d * 0.5 - thick * 0.5), zc, merlon_w, thick, merlon_h, mat_idx=mat)
    m = max(1, int(round((d - merlon_w) / pitch)))
    for j in range(1, m):                                # corners come from the X sides
        y = cy - d * 0.5 + merlon_w * 0.5 + j * (d - merlon_w) / m
        for sx in (-1.0, 1.0):
            add_box(bm, cx + sx * (w * 0.5 - thick * 0.5), y, zc, thick, merlon_w, merlon_h, mat_idx=mat)


def _lm_crow_gable(bm, c, along, out, z_base, w, steps, step_h, mat_brick, mat_plaster, thick=0.5, niches=True):
    """Crow-stepped gable (szczyt schodkowy) facing any horizontal direction.

    c: (x, y) of the gable's inner face centre; the gable occupies c .. c + out*thick, so put
    c `thick` inside the wall line to keep the front flush with the wall below. Plaster
    coping and pinnacles (sterczyny) on every step, a taller central pinnacle, and lancet
    blind niches. Unlike add_crow_step_gable, the top step gets no end copings that would
    duplicate the full-width coping (coplanar overlap).
    """
    c = Vector((c[0], c[1], 0.0))
    along, out = Vector(along).normalized(), Vector(out).normalized()
    shrink = w / (steps + 1)

    def slab(u, uw, z0, z1, d0, d1, mat):
        _lm_extrude(bm, [(u - uw * 0.5, z0), (u + uw * 0.5, z0), (u + uw * 0.5, z1), (u - uw * 0.5, z1)],
                    c + out * d0, along, _LM_Z, out, d1 - d0, mat)

    for s in range(steps):
        sw, sz = w - s * shrink, z_base + s * step_h
        zt = sz + step_h
        slab(0.0, sw, sz, zt, 0.0, thick, mat_brick)
        if s < steps - 1:
            for sx in (-1.0, 1.0):
                ex = sx * (sw * 0.5 - 0.22)
                slab(ex, 0.5, zt, zt + 0.08, -0.04, thick + 0.04, mat_plaster)
                slab(ex, 0.32, zt + 0.08, zt + 0.98, thick * 0.5 - 0.16, thick * 0.5 + 0.16, mat_plaster)
    top_w, zt = w - (steps - 1) * shrink, z_base + steps * step_h
    slab(0.0, top_w, zt, zt + 0.08, -0.04, thick + 0.04, mat_plaster)
    for ex, ph in ((-(top_w * 0.5 - 0.22), 0.9), (top_w * 0.5 - 0.22, 0.9), (0.0, 1.4)):
        slab(ex, 0.32, zt + 0.08, zt + 0.08 + ph, thick * 0.5 - 0.16, thick * 0.5 + 0.16, mat_plaster)
    if not niches:
        return
    nw = 0.55
    for i in range(-(steps - 1), steps, 2):
        nx = i * shrink * 0.5
        ok = [s for s in range(steps) if (w - s * shrink) * 0.5 - 0.35 > abs(nx) + nw * 0.5]
        if not ok:
            continue
        z_top = z_base + (max(ok) + 1) * step_h - 0.45 - nw * 0.6
        z_bot = z_base + 0.4
        if z_top - z_bot < 0.8:
            continue
        _lm_blind(bm, c + out * thick + along * nx + _LM_Z * z_bot, along, out, nw, z_top - z_bot, mat_plaster, proud=0.04)


def _lm_gable_wall(bm, c, along, out, z0, span, h, thick, mat):
    """Plain triangular gable wall; c = base centre on the outer face, built inward."""
    _lm_extrude(bm, [(-span * 0.5, z0), (span * 0.5, z0), (0.0, z0 + h)], Vector((c[0], c[1], 0.0)),
                Vector(along), _LM_Z, -Vector(out), thick, mat)


def _lm_gate_passage(bm, L, W, pw, z_spring, z_top, mat_wall, mat_plinth, mat_frame, plinth_h=1.2,
                     batter=0.4, frame=0.45):
    """Gate-tower base L (along X, the road) x W (along Y, the curtain-wall line), centred on
    the origin, with a pointed-vaulted carriage passage pw wide running through along X.
    Battered limestone plinth on the two side blocks; limestone portal frames at both ends."""
    hl, hw, hp = L * 0.5, W * 0.5, pw * 0.5
    X, Y = Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0))
    for s in (-1.0, 1.0):
        ylo_b, yhi_b = sorted((s * hp, s * (hw + batter)))
        ylo_t, yhi_t = sorted((s * hp, s * hw))
        _lm_hexa(bm, [(-hl - batter, ylo_b, 0.0), (hl + batter, ylo_b, 0.0), (hl + batter, yhi_b, 0.0), (-hl - batter, yhi_b, 0.0),
                      (-hl, ylo_t, plinth_h), (hl, ylo_t, plinth_h), (hl, yhi_t, plinth_h), (-hl, yhi_t, plinth_h)], mat_plinth)
        add_box(bm, 0.0, s * (hp + hw) * 0.5, (plinth_h + z_top) * 0.5, L, hw - hp, z_top - plinth_h, mat_idx=mat_wall)
    za = z_spring + pw * 0.6
    for poly in ([(-hp, z_spring), (0.0, za), (0.0, z_top), (-hp, z_top)],
                 [(0.0, za), (hp, z_spring), (hp, z_top), (0.0, z_top)]):
        _lm_extrude(bm, poly, Vector((-hl, 0.0, 0.0)), Y, _LM_Z, X, L, mat_wall)
    for s in (-1.0, 1.0):
        _lm_lancet(bm, Vector((s * hl, 0.0, 0.0)), Y, Vector((s, 0.0, 0.0)), pw, z_spring, None, mat_frame,
                   frame=frame, sill=False)


def _lm_finish(bm, mat_list, glb_name, obj_name):
    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_" + obj_name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(obj_name, mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, glb_name)

# -------------------------------------------------------------
# 1. Old Town Hall (Ratusz Miejski)
# -------------------------------------------------------------
def build_town_hall(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["plaster_white"], mats["roof_tile_red"],
        mats["copper_patina"], mats["stone_limestone"], mats["timber_dark"],
        mats["glass_dark"], mats["timber_plank"], mats["iron_wrought"], mats["gold_sign"]
    ]

    BR, PL, RT, CU, LS, TD, GL, TP, IR, GD = range(10)
    X, Y, Z = Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), _LM_Z
    W, D, H, Z1, LOG = 18.0, 12.0, 10.0, 4.2, 2.2     # plan, eaves, first floor, loggia depth
    x2, y2 = W * 0.5, D * 0.5
    yb = -y2 + LOG                                      # loggia back wall

    # Ground storey behind the open loggia (on a limestone plinth); upper storey over the full plan
    add_box(bm, 0, (yb + y2) * 0.5, 0.25, W + 0.3, (y2 - yb) + 0.3, 0.5, mat_idx=LS)
    add_box(bm, 0, (yb + y2) * 0.5, Z1 * 0.5, W, y2 - yb, Z1, mat_idx=BR)
    add_box(bm, 0, 0, (Z1 + H) * 0.5, W, D, H - Z1, mat_idx=BR)

    # Market-front loggia (podcienia): six pointed arches on brick piers with limestone imposts
    piers = [-x2 + 0.45 + k * (W - 0.9) / 6 for k in range(7)]
    bays = [(a + b) * 0.5 for a, b in zip(piers, piers[1:])]
    _lm_arcade(bm, (0, -y2, 0), X, -Y, piers, 0.9, 0.8, 2.5, Z1, BR, mat_cap=LS)
    for sx in (-1.0, 1.0):                              # loggia end walls
        yc = (-y2 + 0.8 + yb) * 0.5
        add_box(bm, sx * (x2 - 0.45), yc, Z1 * 0.5, 0.9, yb - (-y2 + 0.8), Z1, mat_idx=BR)
        _lm_blind(bm, Vector((sx * x2, yc, 1.0)), Y, sx * X, 0.5, 1.6, PL)
    for i, bx in enumerate(bays):                       # doors and windows inside the loggia
        if i in (1, 4):
            _lm_lancet(bm, Vector((bx, yb, 0.0)), X, -Y, 1.4, 2.3, TP, LS, frame=0.2, sill=False)
        else:
            _lm_lancet(bm, Vector((bx, yb, 1.0)), X, -Y, 0.9, 1.4, GL, LS, frame=0.14)

    # Limestone string course and eaves cornice
    add_box(bm, 0, 0, Z1, W + 0.24, D + 0.24, 0.22, mat_idx=LS)
    add_box(bm, 0, 0, H - 0.3, W + 0.3, D + 0.3, 0.3, mat_idx=LS)

    # Upper floor: mullioned lancets on the bay axes, white blind niches (blendy) over the piers
    for sy in (-1.0, 1.0):
        for bx in bays:
            _lm_lancet(bm, Vector((bx, sy * y2, 5.3)), X, sy * Y, 1.1, 2.3, GL, LS, frame=0.15, mullion=True)
        for px in piers[1:-1]:
            _lm_blind(bm, Vector((px, sy * y2, 4.8)), X, sy * Y, 0.45, 3.6, PL)
    for sx in (-1.0, 1.0):
        for wy in ((-3.2, -0.2) if sx > 0 else (-3.0, 0.0, 3.0)):
            _lm_lancet(bm, Vector((sx * x2, wy, 5.3)), Y, sx * X, 1.1, 2.3, GL, LS, frame=0.15, mullion=True)
    for wy in (-1.0, 2.6):
        _lm_lancet(bm, Vector((-x2, wy, 1.0)), Y, -X, 0.9, 1.4, GL, LS, frame=0.14)

    # Steep tiled roof (ridge along X) between two crow-stepped gables with pinnacles
    _lm_saddle_roof(bm, 0, 0, H, W - 1.0, D, 6.5, 'x', RT, overhang=0.5)
    for sx in (-1.0, 1.0):
        _lm_crow_gable(bm, (sx * (x2 - 0.5), 0.0), Y, sx * X, H, D, 5, 1.4, BR, PL, thick=0.5)

    # Clock tower rising through the ridge
    TW = 5.2
    t2 = TW * 0.5
    add_box(bm, 0, 0, (H + 21.5) * 0.5, TW, TW, 21.5 - H, mat_idx=BR)
    add_box(bm, 0, 0, 17.0, TW + 0.2, TW + 0.2, 0.25, mat_idx=LS)
    for out, along in ((-Y, X), (Y, X), (X, Y), (-X, Y)):
        cc = out * t2 + Z * 19.2
        _lm_disc(bm, cc, along, out, 1.42, LS, proud=0.04, segs=16)          # stone ring
        _lm_disc(bm, cc, along, out, 1.25, PL, proud=0.08, segs=16)          # dial
        _lm_disc(bm, cc + out * 0.06, along, out, 0.16, GD, proud=0.06, segs=8)
        hub = cc + out * 0.13
        add_timber_beam(bm, hub, hub + Z * 0.95, width=0.08, depth=0.08, mat_idx=IR)
        add_timber_beam(bm, hub, hub + along * 0.6 - Z * 0.3, width=0.08, depth=0.08, mat_idx=IR)
        for k in range(4):                                                   # quarter-hour marks
            a = k * math.pi * 0.5
            p = cc + out * 0.1 + along * (1.05 * math.cos(a)) + Z * (1.05 * math.sin(a))
            _lm_obox(bm, p, along, out, 0.14, 0.04, 0.14, GD)
    for wx in (-1.1, 1.1):
        for sy in (-1.0, 1.0):
            _lm_blind(bm, Y * (sy * t2) + X * wx + Z * 14.4, X, sy * Y, 0.6, 1.6, PL)

    # Corbel table, crenellated gallery, octagonal belfry and copper spire
    add_box(bm, 0, 0, 21.75, TW + 0.8, TW + 0.8, 0.5, mat_idx=LS)
    _lm_parapet_rect(bm, 0, 0, 22.0, TW + 0.8, TW + 0.8, 0.8, 0.35, BR, merlon_h=0.7, merlon_w=0.55, pitch=1.2)
    r8 = 2.1 / math.cos(math.pi / 8)
    _lm_ngon_prism(bm, 0, 0, 22.0, 26.4, r8, 8, BR)
    for k in range(8):
        a = k * math.pi / 4
        out, along = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
        if k % 2 == 0:
            _lm_lancet(bm, out * 2.1 + Z * 23.6, along, out, 0.7, 1.7, GL, LS, frame=0.12)
        else:
            _lm_blind(bm, out * 2.1 + Z * 23.8, along, out, 0.45, 1.3, PL)
    _lm_ngon_prism(bm, 0, 0, 26.4, 26.7, r8 + 0.25, 8, LS)
    _lm_spire(bm, 0, 0, 26.7, r8 + 0.3, 9.5, 8, CU, base_cap=False)
    _lm_finial(bm, 0, 0, 36.2, IR, GD, h=1.6)

    # Four corbelled corner turrets (bartizans) with copper needle spires
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            tx, ty = sx * x2, sy * y2
            _lm_ngon_prism(bm, tx, ty, 7.0, 8.4, 0.3, 8, BR, r_top=1.05)
            _lm_ngon_prism(bm, tx, ty, 8.4, 13.0, 1.05, 8, BR)
            _lm_ngon_prism(bm, tx, ty, 13.0, 13.25, 1.18, 8, LS)
            dg = Vector((sx, sy, 0)).normalized()
            _lm_lancet(bm, Vector((tx, ty, 10.2)) + dg * (1.05 * math.cos(math.pi / 8)),
                       Vector((-dg.y, dg.x, 0)), dg, 0.3, 0.9, GL, None)
            _lm_spire(bm, tx, ty, 13.25, 1.2, 4.6, 8, CU, base_cap=False)
            _lm_finial(bm, tx, ty, 17.85, IR, GD, h=1.0)

    # External limestone stair along the +X gable up to the first-floor council door
    steps, run = 9, 0.8
    rise = Z1 / steps
    sx0, sx1, y_land, y_end = x2, x2 + 1.9, 2.0, 5.2
    y0 = y_land - steps * run
    for k in range(steps):
        add_box(bm, (sx0 + sx1) * 0.5, y0 + (k + 0.5) * run, (k + 1) * rise * 0.5,
                sx1 - sx0, run, (k + 1) * rise, mat_idx=LS)
    add_box(bm, (sx0 + sx1) * 0.5, (y_land + y_end) * 0.5, Z1 * 0.5, sx1 - sx0, y_end - y_land, Z1, mat_idx=LS)
    _lm_extrude(bm, [(y0, 0.0), (y_end, 0.0), (y_end, Z1 + 0.9), (y_land, Z1 + 0.9), (y0, 0.9)],
                Vector((sx1, 0, 0)), Y, Z, X, 0.25, LS)                      # raking balustrade
    add_box(bm, (sx0 + sx1 + 0.25) * 0.5, y_end + 0.125, (Z1 + 0.9) * 0.5, sx1 - sx0 + 0.25, 0.25, Z1 + 0.9, mat_idx=LS)
    _lm_lancet(bm, Vector((x2, 3.6, Z1)), Y, X, 1.2, 2.0, TP, LS, frame=0.2, sill=False)

    _lm_finish(bm, mat_list, "town_hall", "TownHall")

# -------------------------------------------------------------
# 2. Szmatruz (Cloth & Bread Hall)
# -------------------------------------------------------------
def build_szmatruz(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["stone_limestone"], mats["roof_tile_red"],
        mats["timber_dark"], mats["awning_red_white"], mats["awning_blue_white"],
        mats["plaster_white"], mats["glass_dark"], mats["goods_fabrics"],
        mats["goods_cheese_bread"]
    ]
    BR, LS, RT, TD, AR, AB, PL, GL, GF, GB = range(10)
    X, Y, Z = Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), _LM_Z
    HX, HY = 10.45, 4.45                       # outer faces of the 22 piers (x -10..10, y +-4)
    ZS, ZA, ZE = 3.3, 5.0, 7.0                 # arch springing, arcade top, attic eaves

    # Open pointed arcades on all four sides (22 piers on the long sides) with limestone imposts
    xs = [float(x) for x in range(-10, 11, 2)]
    for s in (-1.0, 1.0):
        _lm_arcade(bm, (0, s * HY, 0), X, s * Y, xs, 0.9, 0.9, ZS, ZA, BR, mat_cap=LS)
        _lm_arcade(bm, (s * HX, 0, 0), Y, s * X, [-4.0, -2.0, 0.0, 2.0, 4.0], 0.9, 0.9, ZS, ZA, BR,
                   mat_cap=LS, end_piers=False)
        for x in xs:
            add_box(bm, x, s * (HY - 0.45), 0.2, 1.1, 1.1, 0.4, mat_idx=LS)          # pier bases
        for y in (-2.0, 0.0, 2.0):
            add_box(bm, s * (HX - 0.45), y, 0.2, 1.1, 1.1, 0.4, mat_idx=LS)

    # Attic storey (cloth store) with string course, cornice, vents and blind niches
    add_box(bm, 0, 0, (ZA + ZE) * 0.5, 2 * HX, 2 * HY, ZE - ZA, mat_idx=BR)
    add_box(bm, 0, 0, ZA, 2 * HX + 0.2, 2 * HY + 0.2, 0.2, mat_idx=LS)
    add_box(bm, 0, 0, ZE - 0.3, 2 * HX + 0.25, 2 * HY + 0.25, 0.3, mat_idx=LS)
    for s in (-1.0, 1.0):
        for i, bx in enumerate(range(-9, 10, 2)):
            if i % 2 == 0:
                _lm_lancet(bm, Vector((bx, s * HY, 5.35)), X, s * Y, 0.5, 0.7, GL, LS, frame=0.1)
            else:
                _lm_blind(bm, Vector((bx, s * HY, 5.3)), X, s * Y, 0.45, 0.8, PL)
        for y in (-2.0, 2.0):
            _lm_blind(bm, Vector((s * HX, y, 5.3)), Y, s * X, 0.45, 0.8, PL)

    # Tiled saddle roof between crow-stepped gables
    _lm_saddle_roof(bm, 0, 0, ZE, 2 * HX - 1.0, 2 * HY, 5.0, 'x', RT, overhang=0.45)
    for s in (-1.0, 1.0):
        _lm_crow_gable(bm, (s * (HX - 0.5), 0.0), Y, s * X, ZE, 2 * HY, 4, 1.45, BR, PL, thick=0.5)

    # Trestle counters along the covered aisle: broadcloth bolts and loaves under small canopies
    for i, bx in enumerate((-7.0, -3.0, 3.0, 7.0)):
        for s in (-1.0, 1.0):
            cy = s * 2.5
            add_box(bm, bx, cy, 0.45, 1.6, 0.9, 0.9, mat_idx=TD)
            goods = GF if (i + (s > 0)) % 2 == 0 else GB
            for gx in (-0.5, 0.0, 0.5):
                add_box(bm, bx + gx, cy, 1.02, 0.4, 0.6, 0.24, mat_idx=goods)
            for px in (-0.75, 0.75):
                add_timber_beam(bm, Vector((bx + px, s * 1.95, 0.0)), Vector((bx + px, s * 1.95, 2.4)),
                                width=0.08, depth=0.08, mat_idx=TD)
            add_box(bm, bx, s * 2.4, 2.44, 1.9, 1.2, 0.08, mat_idx=AR if i % 2 == 0 else AB)

    _lm_finish(bm, mat_list, "szmatruz", "Szmatruz")

# -------------------------------------------------------------
# 3. Market Stall with Scalloped Striped Canopy
# -------------------------------------------------------------
def build_market_stall(mats, awning_mat_name, name_suffix):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_plank"], mats[awning_mat_name],
        mats["goods_cheese_bread"], mats["goods_fabrics"], mats["plaster_white"]
    ]

    w, d = 3.2, 2.2
    w2, d2 = w * 0.5, d * 0.5
    for cx in [-w2 + 0.1, w2 - 0.1]:
        for cy in [-d2 + 0.1, d2 - 0.1]:
            add_box(bm, cx, cy, 1.4, 0.12, 0.12, 2.8, mat_idx=0)

    add_box(bm, 0, 0, 0.85, w - 0.2, d - 0.2, 0.8, mat_idx=1)
    add_box(bm, 0, -d2 + 0.05, 0.9, w, 0.1, 0.15, mat_idx=0)

    add_box(bm, -0.8, 0.2, 1.35, 0.7, 0.7, 0.3, mat_idx=3)
    add_box(bm, -0.8, -0.4, 1.35, 0.6, 0.5, 0.25, mat_idx=3)
    add_box(bm, 0.6, 0.0, 1.4, 1.0, 0.6, 0.4, mat_idx=4)

    v0 = bm.verts.new(Vector((-w2 - 0.2, -d2 - 0.2, 2.5)))
    v1 = bm.verts.new(Vector((w2 + 0.2, -d2 - 0.2, 2.5)))
    v2 = bm.verts.new(Vector((w2 + 0.2, d2 + 0.2, 2.5)))
    v3 = bm.verts.new(Vector((-w2 - 0.2, d2 + 0.2, 2.5)))
    r0 = bm.verts.new(Vector((0, -d2 - 0.2, 3.2)))
    r1 = bm.verts.new(Vector((0, d2 + 0.2, 3.2)))

    f0 = bm.faces.new([v0, r0, r1, v3])
    f1 = bm.faces.new([v1, v2, r1, r0])
    f2 = bm.faces.new([v0, v1, r0])
    f3 = bm.faces.new([v2, v3, r1])
    for f in [f0, f1, f2, f3]: f.material_index = 2

    for side, ypos in [(1, -d2 - 0.2), (-1, d2 + 0.2)]:
        add_box(bm, 0, ypos, 2.35, w + 0.4, 0.05, 0.35, mat_idx=2)

    bm.normal_update()
    mesh = bpy.data.meshes.new(f"Mesh_MarketStall_{name_suffix}")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new(f"MarketStall_{name_suffix}", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, f"market_stall_{name_suffix}")

# -------------------------------------------------------------
# 4. Market Cart with Spoked Wheels
# -------------------------------------------------------------
def build_market_cart(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_plank"], mats["timber_dark"], mats["iron_wrought"],
        mats["goods_cheese_bread"], mats["stone_limestone"]
    ]

    add_box(bm, 0, 0, 0.85, 1.2, 2.4, 0.1, mat_idx=0)
    add_box(bm, -0.55, 0, 1.15, 0.08, 2.4, 0.5, mat_idx=0)
    add_box(bm, 0.55, 0, 1.15, 0.08, 2.4, 0.5, mat_idx=0)
    add_box(bm, 0, 1.15, 1.15, 1.2, 0.08, 0.5, mat_idx=0)

    add_box(bm, -0.3, -1.8, 0.55, 0.08, 1.6, 0.08, mat_idx=1)
    add_box(bm, 0.3, -1.8, 0.55, 0.08, 1.6, 0.08, mat_idx=1)
    add_box(bm, 0, 0, 0.6, 1.6, 0.1, 0.1, mat_idx=2)

    for wx in [-0.75, 0.75]:
        segs = 8
        for i in range(segs):
            a1 = (i / segs) * math.pi * 2
            a2 = ((i + 1) / segs) * math.pi * 2
            y1, z1 = math.cos(a1) * 0.6, 0.6 + math.sin(a1) * 0.6
            y2, z2 = math.cos(a2) * 0.6, 0.6 + math.sin(a2) * 0.6
            my, mz = (y1 + y2) * 0.5, (z1 + z2) * 0.5
            len_seg = math.hypot(y2 - y1, z2 - z1)
            add_box(bm, wx, my, mz, 0.08, len_seg, 0.08, mat_idx=1)
        add_box(bm, wx, 0, 0.6, 0.18, 0.2, 0.2, mat_idx=2)
        add_box(bm, wx, 0, 0.6, 0.06, 1.1, 0.06, mat_idx=1)
        add_box(bm, wx, 0, 0.6, 0.06, 0.06, 1.1, mat_idx=1)

    add_box(bm, 0, 0.4, 1.15, 0.8, 0.8, 0.7, mat_idx=1)
    add_box(bm, 0, -0.4, 1.05, 0.7, 0.9, 0.5, mat_idx=3)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_MarketCart")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("MarketCart", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "market_cart")

# -------------------------------------------------------------
# 5. Municipal Stone Well (Studnia Miejska)
# -------------------------------------------------------------
def build_town_well(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"], mats["timber_dark"], mats["roof_shingle"],
        mats["iron_wrought"], mats["plaster_cream"]
    ]

    segs = 8
    radius = 1.1
    for i in range(segs):
        a1 = (i / segs) * math.pi * 2
        a2 = ((i + 1) / segs) * math.pi * 2
        x1, y1 = math.cos(a1) * radius, math.sin(a1) * radius
        x2, y2 = math.cos(a2) * radius, math.sin(a2) * radius
        mx, my = (x1 + x2) * 0.5, (y1 + y2) * 0.5
        seg_len = math.hypot(x2 - x1, y2 - y1)
        add_box(bm, mx, my, 0.5, 0.35, seg_len, 1.0, mat_idx=0)

    add_box(bm, -0.9, 0, 1.8, 0.16, 0.16, 2.6, mat_idx=1)
    add_box(bm, 0.9, 0, 1.8, 0.16, 0.16, 2.6, mat_idx=1)
    add_box(bm, 0, 0, 2.8, 1.9, 0.16, 0.16, mat_idx=1)
    add_box(bm, 0, 0, 2.4, 0.9, 0.2, 0.2, mat_idx=3)

    add_sloped_roof(bm, 0, 0, 2.9, 2.2, 1.8, 1.1, overhang=0.2, mat_idx=2)
    add_box(bm, 0.5, 0.5, 1.25, 0.4, 0.4, 0.45, mat_idx=1)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_TownWell")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("TownWell", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "town_well")

# -------------------------------------------------------------
# 6. Improved House Type 1: Timber Log Cottage (Dom zrębowy)
# -------------------------------------------------------------
def build_house_timber_log(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_plank"], mats["roof_thatch"],
        mats["stone_limestone"], mats["brick_gothic"], mats["foliage_green"],
        mats["glass_dark"]
    ]

    # Fieldstone plinth (Limestone -> StoneFieldstone at export)
    add_box(bm, 0, 0, 0.4, 8.4, 11.4, 0.8, mat_idx=3)

    # Interlocking log body (TimberDark -> TimberLog at export) with saddle-notched
    # corners: log ends cross past every corner, alternating each 25 cm course.
    W, D, z0, z1 = 8.0, 11.0, 0.8, 5.6
    add_box(bm, 0, 0, (z0 + z1) * 0.5, W, D, z1 - z0, mat_idx=0)
    add_log_corner_crossings(bm, 0, 0, W, D, z0, z1, course=0.25, mat_idx=0)

    # Plank door and small framed windows with open board shutters
    add_box(bm, 0, -D * 0.5 - 0.05, 0.8 + 1.05, 1.1, 0.12, 2.1, mat_idx=1)
    front, flank = Vector((0, -1, 0)), Vector((1, 0, 0))
    for wx in (-2.4, 2.4):
        add_wall_window(bm, Vector((wx, -D * 0.5, 2.5)), (1, 0, 0), front, 0.8, 0.8,
                        mat_glass=6, mat_frame=1, frame=0.12, shutters_mat=1)
    for wy in (-2.8, 2.2):                                      # camera-facing +X flank
        add_wall_window(bm, Vector((W * 0.5, wy, 2.5)), (0, 1, 0), flank, 0.8, 0.8,
                        mat_glass=6, mat_frame=1, frame=0.12, shutters_mat=1)
    add_wall_window(bm, Vector((-W * 0.5, 0.0, 2.5)), (0, 1, 0), (-1, 0, 0), 0.8, 0.8, mat_glass=6, mat_frame=1)
    add_wall_window(bm, Vector((0.0, D * 0.5, 2.5)), (1, 0, 0), (0, 1, 0), 0.8, 0.8, mat_glass=6, mat_frame=1)

    # Thick thatched roof: board gables (vertical planks), deep thatch eaves, verge boards,
    # one loft window, and ridge cross-timbers (kozly)
    add_gable_roof(bm, 0, 0, z1, W, D, 5.2, overhang=0.6, mat_roof=2, mat_plaster=1, mat_timber=1,
                   mat_glass=6, frame=False, loft_windows=1, eave_lip=0.3)
    for ypos in [-5.0, -2.5, 0.0, 2.5, 5.0]:
        add_box(bm, 0, ypos, 10.9, 0.8, 0.15, 0.5, mat_idx=0)

    # Chimney
    add_box(bm, 2.0, 2.0, 8.5, 1.1, 1.1, 4.5, mat_idx=4)

    # Yard doodads: split-rail fence, vegetable patch, firewood cord
    add_box(bm, 5.2, 0, 0.2, 2.0, 6.0, 0.2, mat_idx=5) # cabbage bed
    add_box(bm, -4.8, 0, 0.6, 0.8, 3.0, 1.0, mat_idx=0) # firewood stack

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HouseLog")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseLog", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_timber_log")

# -------------------------------------------------------------
# 7. Improved House Type 2: Half-Timber Jettied House (Kamienica szachulcowa)
# -------------------------------------------------------------
def build_house_half_timber(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_white"], mats["timber_dark"], mats["roof_tile_red"],
        mats["stone_limestone"], mats["brick_gothic"], mats["timber_plank"],
        mats["glass_dark"]
    ]

    # Ground floor: stone/brick plinth
    add_box(bm, 0, 0, 2.2, 8.0, 12.0, 4.4, mat_idx=3)
    # Shop opening with fold-down wooden counter shutters
    add_box(bm, -1.8, -6.05, 1.8, 1.4, 0.15, 2.6, mat_idx=1)
    add_box(bm, 1.8, -6.05, 2.0, 2.2, 0.15, 1.6, mat_idx=5) # shutter
    add_box(bm, 1.8, -6.3, 1.3, 2.4, 0.5, 0.1, mat_idx=5) # display shelf

    # Overhanging 2nd floor jetty: lime-plaster infill (recessed) in a timber frame on all
    # four sides. Previously four solid TimberDark slabs hid the plaster entirely, so the
    # storey read as a dark band instead of white panels between dark beams.
    W, D, z0, z1 = 8.8, 12.6, 4.3, 8.1
    add_box(bm, 0, 0, (z0 + z1) * 0.5, W, D, z1 - z0, mat_idx=0)
    x2, y2 = W * 0.5, D * 0.5
    for a, b, out in [((-x2, -y2), (x2, -y2), (0, -1, 0)),   # street facade (-Y)
                      ((x2, -y2), (x2, y2), (1, 0, 0)),      # camera-facing flank (+X)
                      ((x2, y2), (-x2, y2), (0, 1, 0)),
                      ((-x2, y2), (-x2, -y2), (-1, 0, 0))]:
        # Walls run head-to-tail, so each owns the corner at its start (one solid corner
        # post, plates through) and butts against its neighbour's at its end.
        add_half_timber_wall(bm, a, b, z0, z1, Vector(out), mat_timber=1, mat_glass=6,
                             ends=("post", "butt"))

    # Carved wooden corbels under jetty
    for cx in [-4.0, -2.0, 0.0, 2.0, 4.0]:
        add_box(bm, cx, -6.2, 4.3, 0.35, 0.5, 0.7, mat_idx=1)

    # Clay tiled medieval gable roof (framed plaster gables) with attic dormer
    add_gable_roof(bm, 0, 0, z1, W, D, 5.5, overhang=0.4, mat_roof=2, mat_plaster=0, mat_timber=1, mat_glass=6,
                   frame_wrap=True)
    add_box(bm, 2.2, -2.0, 11.2, 1.6, 2.2, 1.8, mat_idx=0)
    add_sloped_roof(bm, 2.2, -2.0, 12.1, 1.6, 2.2, 1.0, overhang=0.2, mat_idx=2)

    # Backyard rain barrel and firewood cord
    add_cylinder(bm, 4.8, -4.5, 0.6, radius=0.45, height=1.2, segs=8, mat_idx=1)
    add_box(bm, -4.8, 0, 0.8, 0.8, 3.5, 1.4, mat_idx=1)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HouseHalfTimber")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseHalfTimber", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_half_timber")

# -------------------------------------------------------------
# 8. Improved House Type 3: Patrician Stepped Brick Kamienica
# -------------------------------------------------------------
def build_house_patrician_brick(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["plaster_white"], mats["roof_tile_red"],
        mats["stone_limestone"], mats["iron_wrought"], mats["glass_dark"],
        mats["timber_plank"]
    ]

    # Ground + 1st floors in Polish Gothic Brick: 9m wide x 14m deep x 8m high
    W, D, H = 9.0, 14.0, 8.0
    x2, y2 = W * 0.5, D * 0.5
    add_box(bm, 0, 0, H * 0.5, W, D, H, mat_idx=0)

    # Limestone plinth, string course between storeys, and eaves cornice
    add_box(bm, 0, 0, 0.35, W + 0.24, D + 0.24, 0.7, mat_idx=3)
    add_box(bm, 0, 0, 4.1, W + 0.16, D + 0.16, 0.2, mat_idx=3)
    add_box(bm, 0, 0, H - 0.12, W + 0.2, D + 0.2, 0.24, mat_idx=3)

    # Corner buttresses on the street facade, with sloped-look limestone caps
    for sx in (-1.0, 1.0):
        add_box(bm, sx * (x2 - 0.35), -y2 - 0.25, 3.6, 0.7, 0.5, 7.2, mat_idx=0)
        add_box(bm, sx * (x2 - 0.35), -y2 - 0.25, 7.3, 0.8, 0.6, 0.2, mat_idx=3)

    # Pointed Gothic portal: limestone surround, plank door; cellar street trapdoor
    portal = Vector((0.0, -y2, 0.7 + 1.35))
    # (the window helper's "glass" panel is the plank door leaf here: mat_glass=6)
    add_wall_window(bm, portal, (1, 0, 0), (0, -1, 0), 1.5, 2.7, mat_glass=6, mat_frame=3,
                    frame=0.28, pointed=True)
    add_box(bm, 2.8, -7.6, 0.2, 1.6, 1.2, 0.3, mat_idx=4) # cellar iron hatch

    # Lancet windows with limestone surrounds: street facade, +X flank (camera side), -X, back
    def lancet(c, along, out, w=1.0, h=1.8):
        add_wall_window(bm, c, along, out, w, h, mat_glass=5, mat_frame=3, frame=0.14, pointed=True)

    for wx in (-2.6, 2.6):
        lancet(Vector((wx, -y2, 2.2)), (1, 0, 0), (0, -1, 0), h=1.4)          # ground floor
    for wx in (-2.6, 0.0, 2.6):
        lancet(Vector((wx, -y2, 5.6)), (1, 0, 0), (0, -1, 0))                 # upper floor
    for sx, out in ((1.0, (1, 0, 0)), (-1.0, (-1, 0, 0))):
        for wy in (-4.5, -1.5, 1.5, 4.5):
            lancet(Vector((sx * x2, wy, 2.2)), (0, 1, 0), out, h=1.4)
            lancet(Vector((sx * x2, wy, 5.6)), (0, 1, 0), out)
    for wx in (-2.6, 0.0, 2.6):
        lancet(Vector((wx, y2, 5.6)), (1, 0, 0), (0, 1, 0))

    # High pitched clay tile roof; gable ends are brick (hidden behind the crow steps)
    add_gable_roof(bm, 0, 0, H, W, D, 6.0, overhang=0.2, mat_roof=2, mat_plaster=0, mat_timber=0,
                   frame=False, loft_windows=0, bargeboards=False)

    # Crow-stepped gables (szczyt schodkowy) with pinnacles and white lancet blind niches,
    # on the street front and, plainer, on the back
    add_crow_step_gable(bm, 0, -y2, -1.0, H, W, steps=5, step_h=1.3, mat_brick=0, mat_plaster=1)
    add_crow_step_gable(bm, 0, y2, 1.0, H, W, steps=5, step_h=1.3, mat_brick=0, mat_plaster=1, niches=False)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HousePatrician")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HousePatrician", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_patrician_brick")

# -------------------------------------------------------------
# 9. Curtain Wall & Defense Tower
# -------------------------------------------------------------
def build_curtain_wall(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["stone_limestone"], mats["timber_dark"],
        mats["roof_tile_red"]
    ]

    add_box(bm, 0, 0, 1.0, 16.0, 2.6, 2.0, mat_idx=1)
    add_box(bm, 0, 0, 5.0, 16.0, 2.4, 6.0, mat_idx=0)

    for x in range(-7, 8, 2):
        add_box(bm, x, 1.1, 8.8, 1.2, 0.4, 1.6, mat_idx=0)

    add_box(bm, 0, -1.0, 7.6, 16.0, 1.4, 0.2, mat_idx=2)
    add_box(bm, 0, -1.6, 8.3, 16.0, 0.1, 1.2, mat_idx=2)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_CurtainWall")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("CurtainWall", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "curtain_wall")

def build_defense_tower(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["stone_limestone"], mats["roof_tile_red"],
        mats["timber_dark"]
    ]

    add_box(bm, 0, 0, 1.0, 7.4, 7.4, 2.0, mat_idx=1)
    add_box(bm, 0, 0, 8.0, 7.0, 7.0, 12.0, mat_idx=0)

    add_box(bm, 0, 0, 14.6, 8.2, 8.2, 1.4, mat_idx=1)
    for cx in [-3.5, 0, 3.5]:
        for cy in [-3.5, 3.5]:
            add_box(bm, cx, cy, 16.0, 1.4, 0.5, 1.4, mat_idx=0)

    add_box(bm, 0, 0, 18.0, 7.6, 7.6, 3.0, mat_idx=2)
    add_box(bm, 0, 0, 20.2, 4.0, 4.0, 2.0, mat_idx=2)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_DefenseTower")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("DefenseTower", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "curtain_tower")

# -------------------------------------------------------------
# 10. Medieval Oak Tree & Timber Shed
# -------------------------------------------------------------
def build_tree_oak(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [mats["timber_dark"], mats["foliage_green"]]

    add_box(bm, 0, 0, 2.0, 0.7, 0.7, 4.0, mat_idx=0)
    add_box(bm, 0.4, 0.3, 4.2, 0.5, 0.5, 2.0, mat_idx=0)
    add_box(bm, -0.3, -0.2, 4.5, 0.5, 0.5, 2.2, mat_idx=0)

    add_box(bm, 0, 0, 6.8, 4.2, 4.2, 3.2, mat_idx=1)
    add_box(bm, 0.8, 0.6, 6.0, 3.2, 3.2, 2.8, mat_idx=1)
    add_box(bm, -0.7, -0.5, 6.2, 3.0, 3.0, 2.6, mat_idx=1)
    add_box(bm, 0, 0, 8.6, 2.6, 2.6, 2.2, mat_idx=1)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_TreeOak")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("TreeOak", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "tree_oak")

def build_shed_timber(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_plank"], mats["roof_shingle"],
        mats["stone_limestone"]
    ]

    add_box(bm, 0, 0, 0.2, 5.2, 6.2, 0.4, mat_idx=3)
    add_box(bm, 0, 0, 1.8, 4.8, 5.8, 2.8, mat_idx=1)
    for cx in [-2.45, 2.45]:
        for cy in [-2.95, 2.95]:
            add_box(bm, cx, cy, 1.8, 0.35, 0.35, 2.8, mat_idx=0)
    add_box(bm, 0, -2.95, 1.2, 1.2, 0.1, 2.0, mat_idx=0)
    add_box(bm, 2.7, 0, 0.8, 0.6, 3.2, 1.2, mat_idx=0)

    add_sloped_roof(bm, 0, 0, 3.2, 4.8, 5.8, 2.4, overhang=0.35, mat_idx=2)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_ShedTimber")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("ShedTimber", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "shed_timber")

# -------------------------------------------------------------
# 11. Collegiate Parish Church & Castle Donjon
# -------------------------------------------------------------
def build_church_gothic(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["plaster_white"], mats["roof_tile_red"],
        mats["stone_limestone"], mats["copper_patina"], mats["glass_dark"],
        mats["timber_plank"], mats["iron_wrought"], mats["gold_sign"]
    ]
    BR, PL, RT, LS, CU, GL, TP, IR, GD = range(9)
    X, Y, Z = Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), _LM_Z

    # Plan (footprint as before: x +-8, y -21.5 .. ~15): west tower, nave, narrower chancel
    # ending in a three-sided apse. The church is placed rotated, so -Y (tower) and -X face the camera.
    NX, YW, YE, NH, NR = 8.0, -13.5, 7.0, 13.0, 12.0          # nave half-width, west/east ends, eaves, roof
    CXH, YC, CH, CR = 5.5, 12.0, 12.0, 9.5                     # chancel half-width, apse chord, eaves, roof
    APSE = [(5.5, 12.0), (3.0, 14.6), (-3.0, 14.6), (-5.5, 12.0)]
    APSE_P = [(5.65, 12.0), (3.08, 14.75), (-3.08, 14.75), (-5.65, 12.0)]
    TC, T2, TH = Vector((0.0, -17.5, 0.0)), 4.0, 27.0

    # Limestone plinths (different heights so no top faces are coplanar)
    add_box(bm, 0, (YW + YE) * 0.5, 0.4, 2 * NX + 0.3, YE - YW + 0.3, 0.8, mat_idx=LS)
    add_box(bm, 0, (YE + YC) * 0.5, 0.35, 2 * CXH + 0.3, YC - YE, 0.7, mat_idx=LS)
    _lm_extrude(bm, APSE_P, Vector((0, 0, 0)), X, Y, Z, 0.7, LS)

    # Walls and eaves cornices
    add_box(bm, 0, (YW + YE) * 0.5, NH * 0.5, 2 * NX, YE - YW, NH, mat_idx=BR)
    add_box(bm, 0, (YE + YC) * 0.5, CH * 0.5, 2 * CXH, YC - YE, CH, mat_idx=BR)
    _lm_extrude(bm, APSE, Vector((0, 0, 0)), X, Y, Z, CH, BR)
    add_box(bm, 0, (YW + YE) * 0.5, NH - 0.25, 2 * NX + 0.3, YE - YW + 0.3, 0.3, mat_idx=LS)
    add_box(bm, 0, (YE + YC) * 0.5, CH - 0.25, 2 * CXH + 0.3, YC - YE, 0.3, mat_idx=LS)
    _lm_extrude(bm, APSE_P, Vector((0, 0, CH - 0.4)), X, Y, Z, 0.3, LS)

    # Nave: stepped buttresses with weathering slopes, tall mullioned lancets between them
    bays_y = [-13.0, -9.4, -5.3, -1.2, 2.9, 6.5]
    for sx in (-1.0, 1.0):
        for by in bays_y:
            _lm_buttress(bm, (sx * NX, by), sx * X, Y, 1.0, [(5.5, 1.8), (3.5, 1.2), (1.8, 0.6)], BR)
        for i, (a, b) in enumerate(zip(bays_y, bays_y[1:])):
            wy = (a + b) * 0.5
            if sx < 0 and i == 2:              # porch bay: a short clerestory light only
                _lm_lancet(bm, Vector((sx * NX, wy, 8.0)), Y, sx * X, 1.4, 2.2, GL, LS, frame=0.18)
                continue
            _lm_lancet(bm, Vector((sx * NX, wy, 3.6)), Y, sx * X, 1.7, 5.8, GL, LS, frame=0.2, mullion=True)

    # South porch with a pointed portal (on the camera-facing -X flank)
    px0, px1, py = -NX - 2.2, -NX, -3.25
    add_box(bm, (px0 + px1) * 0.5, py, 2.6, px1 - px0, 3.0, 5.2, mat_idx=BR)
    _lm_saddle_roof(bm, (px0 + px1) * 0.5, py, 5.2, px1 - px0, 3.0, 2.0, 'x', RT, overhang=0.25)
    _lm_gable_wall(bm, (px0, py), Y, -X, 5.2, 3.0, 2.0, 0.3, BR)
    _lm_blind(bm, Vector((px0, py, 5.45)), Y, -X, 0.4, 0.6, PL)
    _lm_lancet(bm, Vector((px0, py, 0.0)), Y, -X, 1.5, 2.6, TP, LS, frame=0.3, sill=False)

    # Steep nave roof between two crow-stepped gables with blind niches
    _lm_saddle_roof(bm, 0, (YW + YE) * 0.5, NH, (YE - YW) - 1.0, 2 * NX, NR, 'y', RT, overhang=0.5)
    _lm_crow_gable(bm, (0.0, YW + 0.5), X, -Y, NH, 2 * NX, 6, 2.2, BR, PL, thick=0.5)
    _lm_crow_gable(bm, (0.0, YE - 0.5), X, Y, NH, 2 * NX, 6, 2.2, BR, PL, thick=0.5)

    # Ridge turret (sygnaturka) for the sanctus bell
    rz = NH + NR
    _lm_ngon_prism(bm, 0, 3.5, rz - 1.5, rz + 1.6, 0.7, 8, CU)
    for k in range(0, 8, 2):
        a = k * math.pi / 4
        out = Vector((math.cos(a), math.sin(a), 0))
        _lm_lancet(bm, Vector((0, 3.5, rz + 0.3)) + out * (0.7 * math.cos(math.pi / 8)),
                   Vector((-out.y, out.x, 0)), out, 0.3, 0.7, GL, None)
    _lm_spire(bm, 0, 3.5, rz + 1.6, 0.85, 3.8, 8, CU, base_cap=False)
    _lm_finial(bm, 0, 3.5, rz + 5.4, IR, GD, h=1.0, cross=True)

    # Chancel and apse: lancets, diagonal buttresses at the apse corners, half-hipped roof
    for sx in (-1.0, 1.0):
        _lm_lancet(bm, Vector((sx * CXH, 9.5, 3.2)), Y, sx * X, 1.4, 5.6, GL, LS, frame=0.18, mullion=True)
    normals = [X]
    for i in range(3):
        a, b = Vector((*APSE[i], 0.0)), Vector((*APSE[i + 1], 0.0))
        along = (b - a).normalized()
        out = Vector((along.y, -along.x, 0.0))
        normals.append(out)
        _lm_lancet(bm, (a + b) * 0.5 + Z * 3.2, along, out, 1.3, 5.6, GL, LS, frame=0.18, mullion=True)
    normals.append(-X)
    for i, p in enumerate(APSE):
        n = (normals[i] + normals[i + 1]).normalized()
        _lm_buttress(bm, p, n, Vector((-n.y, n.x, 0.0)), 0.9, [(5.0, 1.4), (3.2, 0.9), (2.0, 0.5)], BR, back=0.6)
    _lm_saddle_roof(bm, 0, (YE + YC) * 0.5, CH, YC - YE, 2 * CXH, CR, 'y', RT, overhang=0.4)
    ez = CH - CR * 0.4 / CXH
    ev = [bm.verts.new(Vector(p)) for p in ((CXH + 0.4, YC, ez), (3.25, 15.0, ez), (-3.25, 15.0, ez), (-CXH - 0.4, YC, ez))]
    apex = bm.verts.new(Vector((0.0, YC, CH + CR)))
    for i in range(3):
        bm.faces.new([ev[i], ev[i + 1], apex]).material_index = RT

    # West tower: clasping buttresses, string courses, portal, blind niches, belfry openings
    tx, ty = TC.x, TC.y
    add_box(bm, tx, ty, 0.5, 2 * T2 + 0.4, 2 * T2 + 0.4, 1.0, mat_idx=LS)
    add_box(bm, tx, ty, TH * 0.5, 2 * T2, 2 * T2, TH, mat_idx=BR)
    for zb in (9.0, 18.0):
        add_box(bm, tx, ty, zb, 2 * T2 + 0.3, 2 * T2 + 0.3, 0.3, mat_idx=LS)
    tiers = [(9.0, 1.6), (8.0, 1.1), (6.5, 0.6)]
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            _lm_buttress(bm, (tx + sx * T2, ty + sy * (T2 - 0.5)), sx * X, Y, 1.0, tiers, BR)
            if sy < 0:
                _lm_buttress(bm, (tx + sx * (T2 - 0.5), ty + sy * T2), sy * Y, X, 1.0, tiers, BR)
    fy = ty - T2
    _lm_blind(bm, Vector((tx, fy, 0.0)), X, -Y, 3.3, 3.2, LS, proud=0.3)                  # portal orders
    _lm_lancet(bm, Vector((tx, fy - 0.3, 0.0)), X, -Y, 2.0, 2.7, TP, LS, frame=0.25, sill=False)
    _lm_lancet(bm, Vector((tx, fy, 5.6)), X, -Y, 1.5, 2.2, GL, LS, frame=0.18, mullion=True)
    for out, along in ((-Y, X), (X, Y), (-X, Y)):
        base = TC + out * T2
        for o in (-1.3, 1.3):
            _lm_blind(bm, base + along * o + Z * 9.6, along, out, 0.9, 6.3, PL)
        for o in (-1.2, 1.2):
            _lm_lancet(bm, base + along * o + Z * 19.0, along, out, 1.0, 4.6, GL, LS, frame=0.16)

    # Tower top: cornice, parapet with corner pinnacles, octagonal belfry, copper needle spire
    add_box(bm, tx, ty, TH + 0.3, 2 * T2 + 1.0, 2 * T2 + 1.0, 0.6, mat_idx=LS)
    _lm_parapet_rect(bm, tx, ty, TH + 0.6, 2 * T2 + 1.0, 2 * T2 + 1.0, 0.9, 0.35, BR)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            px_, py_ = tx + sx * (T2 + 0.1), ty + sy * (T2 + 0.1)
            _lm_ngon_prism(bm, px_, py_, TH + 0.6, TH + 3.0, 0.6, 8, BR)
            _lm_spire(bm, px_, py_, TH + 3.0, 0.7, 3.4, 8, CU, base_cap=False)
    r8 = 3.0 / math.cos(math.pi / 8)
    _lm_ngon_prism(bm, tx, ty, TH + 0.6, TH + 6.6, r8, 8, BR)
    for k in range(8):
        a = k * math.pi / 4
        out, along = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
        _lm_lancet(bm, TC + out * 3.0 + Z * (TH + 2.0), along, out, 0.8, 2.6, GL, LS, frame=0.14)
    _lm_ngon_prism(bm, tx, ty, TH + 6.6, TH + 6.9, r8 + 0.2, 8, LS)
    _lm_spire(bm, tx, ty, TH + 6.9, r8 + 0.25, 15.0, 8, CU, base_cap=False)
    _lm_finial(bm, tx, ty, TH + 21.9, IR, GD, h=2.0, cross=True)

    _lm_finish(bm, mat_list, "church_gothic", "ChurchGothic")

def build_castle_donjon(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"], mats["brick_gothic"], mats["roof_tile_red"],
        mats["timber_dark"], mats["glass_dark"], mats["timber_plank"],
        mats["iron_wrought"], mats["fire_orange"], mats["gold_sign"],
        mats["cloth_red"], mats["roof_shingle"]
    ]
    LS, BR, RT, TD, GL, TP, IR, FO, GD, CR, SH = range(11)
    X, Y, Z = Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), _LM_Z
    S, R = 16, 7.0
    FL = R * math.cos(math.pi / S)                      # distance to a wall flat

    def radial(a_deg):
        a = math.radians(a_deg)
        return Vector((math.cos(a), math.sin(a), 0.0)), Vector((-math.sin(a), math.cos(a), 0.0))

    # Round limestone keep: battered base, shaft, string courses, arrow slits
    _lm_ngon_prism(bm, 0, 0, 0.0, 3.0, 7.9, S, LS, r_top=R)
    _lm_ngon_prism(bm, 0, 0, 3.0, 21.6, R, S, LS)
    for zb in (9.9, 15.8):
        _lm_ngon_prism(bm, 0, 0, zb, zb + 0.3, R + 0.15, S, LS)
    for a_deg, z in ((0, 6.0), (90, 6.0), (180, 6.0), (45, 12.4), (135, 12.4), (225, 12.4),
                     (315, 12.4), (270, 12.4), (0, 17.6), (90, 17.6), (180, 17.6), (270, 17.6)):
        out, along = radial(a_deg)
        _lm_lancet(bm, out * FL + Z * z, along, out, 0.28, 1.3, GL, None)

    # Raised entrance with a timber platform and draw-stair (camera side, -Y)
    out, along = -Y, X
    _lm_lancet(bm, out * FL + Z * 7.2, along, out, 1.3, 1.7, TP, LS, frame=0.25, rise=0.5, sill=False)
    add_box(bm, 0, -7.9, 7.05, 3.4, 2.6, 0.3, mat_idx=TP)                        # deck y -9.2..-6.6
    for px in (-1.5, 1.5):
        add_timber_beam(bm, Vector((px, -9.0, 0.0)), Vector((px, -9.0, 6.9)), width=0.22, depth=0.22, mat_idx=TD)
        add_timber_beam(bm, Vector((px, -9.0, 5.0)), Vector((px, -7.1, 6.9)), width=0.16, depth=0.16, mat_idx=TD)
    for p, q in (((-1.6, -9.1), (1.6, -9.1)), ((-1.6, -9.1), (-1.6, -6.9))):
        add_timber_beam(bm, Vector((p[0], p[1], 8.1)), Vector((q[0], q[1], 8.1)), width=0.1, depth=0.1, mat_idx=TD)
    for p in ((-1.6, -9.1), (0.0, -9.1), (1.6, -9.1), (-1.6, -7.0)):
        add_timber_beam(bm, Vector((p[0], p[1], 7.2)), Vector((p[0], p[1], 8.15)), width=0.1, depth=0.1, mat_idx=TD)
    n_st, run, sx0 = 11, 0.55, 1.7
    rise = 7.2 / (n_st + 1)
    for yy in (-8.35, -9.25):                                                    # stringers
        add_timber_beam(bm, Vector((sx0, yy, 7.05)), Vector((sx0 + (n_st + 1) * run, yy, 0.05)), width=0.14, depth=0.2, mat_idx=TD)
    for k in range(n_st):
        add_box(bm, sx0 + (k + 0.5) * run, -8.8, 7.2 - (k + 1) * rise + 0.04, 0.5, 1.0, 0.08, mat_idx=TP)
    add_timber_beam(bm, Vector((5.0, -8.8, 0.0)), Vector((5.0, -8.8, 3.6)), width=0.18, depth=0.18, mat_idx=TD)
    for yy, wx in ((-8.35, 1.0), (-9.25, 1.4)):                                  # lifting chains
        add_timber_beam(bm, Vector((sx0 + 0.3, yy, 6.7)), Vector((wx, -math.sqrt(R * R - wx * wx) + 0.05, 9.6)),
                        width=0.06, depth=0.06, mat_idx=IR)

    # Machicolation corbels, brick fighting gallery with merlons, conical tile roof
    for k in range(S):
        out, along = radial(k * 360.0 / S)
        _lm_obox(bm, out * (FL + 0.3) + Z * 21.3, along, out, 0.45, 0.7, 0.6, LS)
    RB = 7.65
    FB = RB * math.cos(math.pi / S)
    _lm_ngon_prism(bm, 0, 0, 21.6, 24.4, RB, S, BR)
    flat = 2.0 * RB * math.sin(math.pi / S)
    for k in range(S):
        out, along = radial(k * 360.0 / S)
        if k % 2 == 0:
            _lm_obox(bm, out * (FB - 0.35) + Z * 25.05, along, out, flat * 0.85, 0.7, 1.3, BR)
        else:
            _lm_lancet(bm, out * FB + Z * 22.4, along, out, 0.25, 0.9, GL, None)
    _lm_spire(bm, 0, 0, 24.4, 7.1, 10.2, S, RT, base_cap=False)
    _lm_finial(bm, 0, 0, 34.6, IR, GD, h=2.0)
    add_box(bm, 0.55, 0, 36.25, 1.0, 0.04, 0.5, mat_idx=CR)                         # pennant

    # Bailey guardhouse and brazier fire basket by the stair foot
    hx, hy = -5.0, -10.8
    add_box(bm, hx, hy, 1.2, 3.2, 2.4, 2.4, mat_idx=TP)
    _lm_saddle_roof(bm, hx, hy, 2.4, 3.2, 2.4, 1.4, 'x', SH, overhang=0.3, end_overhang=0.25)
    for sx in (-1.0, 1.0):
        _lm_gable_wall(bm, (hx + sx * 1.6, hy), Y, sx * X, 2.4, 2.4, 1.4, 0.2, TP)
    add_box(bm, hx, hy - 1.23, 0.95, 0.9, 0.06, 1.9, mat_idx=TD)
    add_timber_beam(bm, Vector((9.0, -10.2, 0.0)), Vector((9.0, -10.2, 1.1)), width=0.1, depth=0.1, mat_idx=IR)
    _lm_ngon_prism(bm, 9.0, -10.2, 1.1, 1.55, 0.25, 8, IR, r_top=0.42)
    _lm_ngon_prism(bm, 9.0, -10.2, 1.55, 1.75, 0.34, 8, FO)

    _lm_finish(bm, mat_list, "castle_donjon", "CastleDonjon")

# =============================================================
# NEW DIFFERENTIATED ARTISAN GUILD WORKSHOPS
# =============================================================

# -------------------------------------------------------------
# Workshop helpers (_ws_*): used only by the six craft workshops below.
# Every face built here is wound by an explicit reference point (no guessing
# vertex order), so roofs, tubs and slats always face outward/up.
# -------------------------------------------------------------
def _ws_poly(bm, verts, mat, ref, outward=True):
    """Face from BMVerts whose normal points away from `ref` (towards it if outward=False)."""
    co = [v.co for v in verts]
    c = sum(co, Vector()) / len(co)
    n = Vector()
    for i in range(len(co)):                       # Newell normal: valid for any planar polygon
        p, q = co[i], co[(i + 1) % len(co)]
        n.x += (p.y - q.y) * (p.z + q.z)
        n.y += (p.z - q.z) * (p.x + q.x)
        n.z += (p.x - q.x) * (p.y + q.y)
    if (n.dot(c - Vector(ref)) < 0) == outward:
        verts = list(reversed(verts))
    f = bm.faces.new(verts)
    f.material_index = mat
    return f


def _ws_face(bm, pts, mat, ref, outward=True):
    return _ws_poly(bm, [bm.verts.new(Vector(p)) for p in pts], mat, ref, outward)


def _ws_prism(bm, top, thick, mat):
    """Convex slab (lean-to roof, board): `top` = upper face corners, extruded down by `thick`."""
    top = [Vector(p) for p in top]
    bot = [p - Vector((0.0, 0.0, thick)) for p in top]
    c = (sum(top, Vector()) + sum(bot, Vector())) / (2 * len(top))
    _ws_face(bm, top, mat, c)
    _ws_face(bm, bot, mat, c)
    for i in range(len(top)):
        j = (i + 1) % len(top)
        _ws_face(bm, [top[i], top[j], bot[j], bot[i]], mat, c)


def _ws_cyl(bm, p1, p2, r, segs=10, mat=0, caps=True):
    """Cylinder between two arbitrary points (logs, lying casks, wheels, bolts of cloth)."""
    p1, p2 = Vector(p1), Vector(p2)
    ax = (p2 - p1).normalized()
    ref = Vector((0.0, 0.0, 1.0)) if abs(ax.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = ax.cross(ref).normalized()
    v = ax.cross(u)
    ring = [u * math.cos(2 * math.pi * i / segs) + v * math.sin(2 * math.pi * i / segs) for i in range(segs)]
    a = [bm.verts.new(p1 + d * r) for d in ring]
    b = [bm.verts.new(p2 + d * r) for d in ring]
    mid = (p1 + p2) * 0.5
    for i in range(segs):
        j = (i + 1) % segs
        _ws_poly(bm, [a[i], a[j], b[j], b[i]], mat, mid)
    if caps:
        _ws_poly(bm, a, mat, mid)
        _ws_poly(bm, b, mat, mid)


def _ws_lathe(bm, cx, cy, z0, prof, segs=8, mat=0, cap_bottom=True, cap_top=True):
    """Solid of revolution about a vertical axis; prof = [(radius, z), ...] bottom to top.
    Keep consecutive profile points at different z (a flat ledge has no 'outward')."""
    rings = [[bm.verts.new(Vector((cx + r * math.cos(2 * math.pi * i / segs),
                                    cy + r * math.sin(2 * math.pi * i / segs), z0 + z)))
              for i in range(segs)] for r, z in prof]
    for k in range(len(rings) - 1):
        axis_pt = Vector((cx, cy, z0 + (prof[k][1] + prof[k + 1][1]) * 0.5))
        for i in range(segs):
            j = (i + 1) % segs
            _ws_poly(bm, [rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]], mat, axis_pt)
    if cap_bottom:
        _ws_poly(bm, rings[0], mat, Vector((cx, cy, z0 + prof[0][1] + 1.0)))
    if cap_top:
        _ws_poly(bm, rings[-1], mat, Vector((cx, cy, z0 + prof[-1][1] - 1.0)))


def _ws_tub(bm, cx, cy, z0, r, h, mat_wood, mat_fill, mat_hoop=None, segs=12, fill=0.8, wall=0.07):
    """Open-topped stave tub: outer and inner walls, rim, liquid surface at `fill` of the height
    and optional iron hoops. (Liquid placed inside a closed add_cylinder is invisible.)"""
    def ring(rad, z):
        return [bm.verts.new(Vector((cx + rad * math.cos(2 * math.pi * i / segs),
                                     cy + rad * math.sin(2 * math.pi * i / segs), z))) for i in range(segs)]
    zt, zf = z0 + h, z0 + h * fill
    ob, ot, it, ib = ring(r, z0), ring(r, zt), ring(r - wall, zt), ring(r - wall, zf)
    below, above = Vector((cx, cy, z0 - 1.0)), Vector((cx, cy, zt + 1.0))
    for i in range(segs):
        j = (i + 1) % segs
        _ws_poly(bm, [ob[i], ob[j], ot[j], ot[i]], mat_wood, Vector((cx, cy, (z0 + zt) * 0.5)))
        _ws_poly(bm, [ot[i], ot[j], it[j], it[i]], mat_wood, below)                 # rim, up
        _ws_poly(bm, [it[i], it[j], ib[j], ib[i]], mat_wood, Vector((cx, cy, (zt + zf) * 0.5)), outward=False)
    _ws_poly(bm, ib, mat_fill, below)                                               # liquid, up
    _ws_poly(bm, ob, mat_wood, above)                                               # base, down
    if mat_hoop is not None:
        for zh in (z0 + h * 0.2, z0 + h * 0.72):
            lo, hi = ring(r + 0.015, zh - 0.035), ring(r + 0.015, zh + 0.035)
            for i in range(segs):
                j = (i + 1) % segs
                _ws_poly(bm, [lo[i], lo[j], hi[j], hi[i]], mat_hoop, Vector((cx, cy, zh)))


def _ws_barrel(bm, cx, cy, z0, r=0.38, h=0.95, mat_wood=0, mat_hoop=1, segs=10):
    """Upright bellied cask with two iron hoops."""
    _ws_lathe(bm, cx, cy, z0, [(r * 0.84, 0.0), (r * 0.97, h * 0.22), (r, h * 0.5),
                               (r * 0.97, h * 0.78), (r * 0.84, h)], segs, mat_wood)
    for zf in (0.22, 0.78):
        rh = r * 0.97 + 0.015
        _ws_lathe(bm, cx, cy, z0, [(rh, h * zf - 0.035), (rh, h * zf + 0.035)], segs, mat_hoop,
                  cap_bottom=False, cap_top=False)


def _ws_cask(bm, p, axis, r=0.42, length=1.0, mat_wood=0, mat_hoop=1, segs=10):
    """Cask lying on its side along `axis`."""
    p = Vector(p)
    ax = Vector(axis).normalized()
    _ws_cyl(bm, p - ax * (length * 0.5), p + ax * (length * 0.5), r, segs, mat_wood)
    _ws_cyl(bm, p - ax * 0.2 * length, p + ax * 0.2 * length, r * 1.05, segs, mat_wood)   # belly
    for s in (-0.36, 0.36):
        c = p + ax * (s * length)
        _ws_cyl(bm, c - ax * 0.035, c + ax * 0.035, r * 1.04, segs, mat_hoop)


def _ws_pot(bm, cx, cy, z0, kind, mat, s=1.0, segs=8):
    """Terracotta ware for drying shelves: 'jug', 'amphora', 'bowl' or 'jar'."""
    prof = {
        "jug": [(0.09, 0.0), (0.15, 0.07), (0.17, 0.18), (0.12, 0.30), (0.06, 0.38), (0.08, 0.44)],
        "amphora": [(0.05, 0.0), (0.12, 0.08), (0.16, 0.22), (0.13, 0.36), (0.06, 0.44), (0.075, 0.50)],
        "bowl": [(0.07, 0.0), (0.15, 0.05), (0.20, 0.13)],
        "jar": [(0.16, 0.0), (0.24, 0.12), (0.27, 0.30), (0.22, 0.48), (0.14, 0.56), (0.16, 0.62)],
    }[kind]
    _ws_lathe(bm, cx, cy, z0, [(r * s, z * s) for r, z in prof], segs, mat)


def _ws_glaze(bm, c, along, out, w, h, mat_glass, mat_frame):
    """Leaded window in a timber-frame bay: dark glass just proud of the plaster + mullion cross."""
    along, out = Vector(along).normalized(), Vector(out).normalized()
    g = c + out * 0.02
    ax = abs(along.x) > 0.5
    add_box(bm, g.x, g.y, g.z, w if ax else 0.04, 0.04 if ax else w, h, mat_idx=mat_glass)
    m = c + out * 0.06
    up = Vector((0.0, 0.0, 1.0))
    add_timber_beam(bm, m - up * (h * 0.5), m + up * (h * 0.5), width=0.06, depth=0.06, mat_idx=mat_frame)
    add_timber_beam(bm, m - along * (w * 0.5) + up * (h * 0.08), m + along * (w * 0.5) + up * (h * 0.08),
                    width=0.06, depth=0.06, mat_idx=mat_frame)


def _ws_four_sides(hx, hy):
    """(a, b, outward) for the four walls of a centred hx x hy half-size footprint, listed
    head-to-tail (street -Y, camera flank +X, back +Y, -X) for ends=("post", "butt")."""
    return [((-hx, -hy), (hx, -hy), (0, -1, 0)), ((hx, -hy), (hx, hy), (1, 0, 0)),
            ((hx, hy), (-hx, hy), (0, 1, 0)), ((-hx, hy), (-hx, -hy), (-1, 0, 0))]


def _ws_three_sides(hx, hy):
    """The +X, back and -X walls (the street front is framed separately with openings)."""
    return _ws_four_sides(hx, hy)[1:]


# Corner joints for _ws_three_sides: the flank/back walls own the two back corners; the two
# street corners stay flush because _ws_framed_front draws its own end posts there.
_WS_THREE_SIDE_ENDS = (("flush", "post"), ("butt", "post"), ("butt", "flush"))


def _ws_wall_frame(a, b, outward, proud):
    a = Vector((a[0], a[1], 0.0))
    b = Vector((b[0], b[1], 0.0))
    length = (b - a).length
    t = (b - a) / length
    out = Vector(outward).normalized()
    return a, t, out, length, out * proud


def _ws_framed_front(bm, a, b, z0, z1, outward, mat_timber, openings, timber=0.18, proud=0.05, rail=None):
    """Street-front timber frame with door/shop openings (add_half_timber_wall would brace
    straight across a doorway). openings: [(s0, s1, z_bottom, z_top)] measured along a->b.
    Posts frame every opening, heads/sills close them, and each solid panel gets a long
    brace (alternating direction) plus an optional mid rail at z0 + rail."""
    a, t, out, length, off = _ws_wall_frame(a, b, outward, proud)
    h = timber * 0.5

    def P(s, z):
        return a + t * s + off + Vector((0.0, 0.0, z))

    def beam(p, q, size=timber):
        add_timber_beam(bm, p, q, width=size, depth=size, mat_idx=mat_timber)

    beam(P(0.0, z0 + h), P(length, z0 + h))
    beam(P(0.0, z1 - h), P(length, z1 - h))
    edges = [h, length - h]
    for s0, s1, zb, zt in openings:
        edges += [s0 - h, s1 + h]
        beam(P(s0 - timber, zt + h), P(s1 + timber, zt + h))
        if zb > z0 + 0.3:
            beam(P(s0 - timber, zb - h), P(s1 + timber, zb - h))
    edges.sort()
    for s in edges:
        beam(P(s, z0 + timber), P(s, z1 - timber))
    flip = False
    for sa, sb in zip(edges[:-1], edges[1:]):
        if sb - sa < 0.5 or any(sa >= o[0] - timber and sb <= o[1] + timber for o in openings):
            continue
        p0, p1 = sa + h, sb - h
        if rail:
            beam(P(p0, z0 + rail), P(p1, z0 + rail), timber * 0.9)
        if flip:
            beam(P(p1, z0 + timber), P(p0, z1 - timber), timber * 0.85)
        else:
            beam(P(p0, z0 + timber), P(p1, z1 - timber), timber * 0.85)
        flip = not flip


def _ws_andrew_wall(bm, a, b, z0, z1, outward, mat_timber, mat_glass=None, bay=1.4,
                    timber=0.18, proud=0.05, rail=0.9, window_every=2, ends=("flush", "flush")):
    """Dense St. Andrew's-cross framing (krzyze sw. Andrzeja) for the weaver: a low cross under
    the rail in every bay and a full-height cross above it, except glazed bays.
    ends: corner joints as in add_half_timber_wall ("post" owns the outer corner post)."""
    a, t, out, length, off = _ws_wall_frame(a, b, outward, proud)
    n = max(2, round(length / bay))
    step = length / n
    h = timber * 0.5
    zr = z0 + rail

    def P(s, z):
        return a + t * s + off + Vector((0.0, 0.0, z))

    def beam(p, q, size=timber):
        add_timber_beam(bm, p, q, width=size, depth=size, mat_idx=mat_timber)

    s_lo = -_ht_end_extent(ends[0], timber, proud)
    s_hi = length + _ht_end_extent(ends[1], timber, proud)
    beam(P(s_lo, z0 + h), P(s_hi, z0 + h))
    beam(P(s_lo, z1 - h), P(s_hi, z1 - h))
    for i in range(n + 1):
        s = min(max(i * step, h), length - h)
        end = ends[0] if i == 0 else ends[1] if i == n else None
        if end == "butt":
            continue
        if end == "post":
            s = -proud if i == 0 else length + proud
        beam(P(s, z0 + timber), P(s, z1 - timber))
    for i in range(n):
        s0, s1 = i * step + h, (i + 1) * step - h
        if i == 0 and ends[0] != "flush":
            s0 = h - proud
        if i == n - 1 and ends[1] != "flush":
            s1 = length - (h - proud)
        beam(P(s0, zr), P(s1, zr), timber * 0.9)
        beam(P(s0, z0 + timber), P(s1, zr - h), timber * 0.7)
        beam(P(s1, z0 + timber), P(s0, zr - h), timber * 0.7)
        if mat_glass is not None and 0 < i < n - 1 and i % window_every == 1:
            zb, zt = zr + h + 0.06, z1 - timber - 0.06
            c = a + t * ((s0 + s1) * 0.5) + Vector((0.0, 0.0, (zb + zt) * 0.5))
            _ws_glaze(bm, c, t, out, (s1 - s0) - 0.16, zt - zb, mat_glass, mat_timber)
        else:
            beam(P(s0, zr + h), P(s1, z1 - timber), timber * 0.75)
            beam(P(s1, zr + h), P(s0, z1 - timber), timber * 0.75)


def _ws_louvre(bm, c, along, out, w, h, mat_back, mat_slat, slats=6):
    """Malt-kiln ventilation louvre (zaluzja): dark opening behind downward-sloping board slats."""
    along, out = Vector(along).normalized(), Vector(out).normalized()
    up = Vector((0.0, 0.0, 1.0))
    g = c + out * 0.02
    ax = abs(along.x) > 0.5
    add_box(bm, g.x, g.y, g.z, w if ax else 0.04, 0.04 if ax else w, h, mat_idx=mat_back)
    step = h / slats
    for k in range(slats):
        zt = h * 0.5 - k * step
        p0 = c + out * 0.05 + up * zt
        p1 = c + out * 0.17 + up * (zt - step * 1.05)
        _ws_face(bm, [p0 - along * (w * 0.5), p0 + along * (w * 0.5),
                      p1 + along * (w * 0.5), p1 - along * (w * 0.5)], mat_slat, c - out)


def _ws_ridge_crosses(bm, cx, ys, z_ridge, slope, mat, reach=0.55, size=0.1):
    """Crossed ridge sticks (kozly) that hold thatch down; feet rest on the roof surface."""
    for y in ys:
        for sx in (-1.0, 1.0):
            add_timber_beam(bm, Vector((cx + sx * reach, y, z_ridge - reach * slope + 0.04)),
                            Vector((cx - sx * reach * 0.55, y, z_ridge + 0.4)), width=size, depth=size, mat_idx=mat)


def _ws_hide_rack(bm, x0, x1, y, h, hides, mat_frame, leg=0.6, pole_r=0.12):
    """A-frame hide/cloth rack along X with pelts hanging from the pole; hides = [mat, ...]."""
    for x in (x0, x1):
        for sy in (-1.0, 1.0):
            add_timber_beam(bm, Vector((x, y + sy * leg, 0.0)), Vector((x, y, h)), width=0.13, depth=0.13, mat_idx=mat_frame)
    add_timber_beam(bm, Vector((x0 - 0.15, y, h - 0.05)), Vector((x1 + 0.15, y, h - 0.05)), width=pole_r, depth=pole_r, mat_idx=mat_frame)
    n = len(hides)
    seg = (x1 - x0 - 0.3) / n
    for i, m in enumerate(hides):
        hx = x0 + 0.15 + seg * (i + 0.5)
        hl = 1.15 + 0.2 * ((i * 7) % 3) / 2.0              # uneven pelt lengths
        add_box(bm, hx, y + (0.03 if i % 2 else -0.03), h - 0.13 - hl * 0.5, seg * 0.82, 0.04, hl, mat_idx=m)


def _ws_finish(bm, mat_list, mesh_name, obj_name, glb_name):
    bm.normal_update()
    mesh = bpy.data.meshes.new(mesh_name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(obj_name, mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, glb_name)


# -------------------------------------------------------------
# 12. Baker's House & Masonry Bread Oven (Piekarnia)
# -------------------------------------------------------------
def build_baker_house(mats):
    """Half-timbered bakery (reference_photos/baker_house): framed ground-floor shop with bread
    counter and lift-up shutter, jettied framed upper storey, tiled gable roof, gilded pretzel
    on an iron bracket, and a brick beehive oven with stone flue under a tiled lean-to on +X."""
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_cream"],      # 0
        mats["timber_dark"],        # 1
        mats["roof_tile_red"],      # 2
        mats["brick_gothic"],       # 3
        mats["stone_limestone"],    # 4  (-> StoneFieldstone at export)
        mats["timber_plank"],       # 5
        mats["flour_sack_cloth"],   # 6
        mats["fire_orange"],        # 7
        mats["gold_pretzel"],       # 8
        mats["iron_wrought"],       # 9
        mats["birch_bark"],         # 10
        mats["wood_end_grain"],     # 11
        mats["soot_black"],         # 12
        mats["glass_dark"],         # 13
        mats["bread_golden"],       # 14
        mats["brick_oven"],         # 15
        mats["timber_weathered"]    # 16
    ]

    W, D = 7.6, 11.2
    w2, d2 = W * 0.5, D * 0.5
    z0, z1 = 0.6, 3.8                       # ground storey (shop + bakehouse)
    Wj, Dj = W + 0.5, D + 0.6               # jettied upper storey
    wj, dj = Wj * 0.5, Dj * 0.5
    zt = 7.2

    # Fieldstone plinth and plaster ground storey
    add_box(bm, 0, 0, z0 * 0.5, W + 0.12, D + 0.12, z0, mat_idx=4)
    add_box(bm, 0, 0, (z0 + z1) * 0.5, W, D, z1 - z0, mat_idx=0)

    # Street front (-Y): plank door (x -2.0) and shop window (x 1.4) in a framed facade
    _ws_framed_front(bm, (-w2, -d2), (w2, -d2), z0, z1, (0, -1, 0), 1,
                     [(1.25, 2.35, z0, z0 + 2.2), (4.1, 6.7, z0 + 0.95, z0 + 2.35)], rail=1.0)
    add_box(bm, -2.0, -d2 - 0.04, z0 + 1.1, 1.06, 0.06, 2.18, mat_idx=5)            # door leaf
    for zs in (z0 + 0.45, z0 + 1.75):                                                # strap hinges
        add_box(bm, -2.05, -d2 - 0.08, zs, 0.8, 0.02, 0.07, mat_idx=9)
    add_box(bm, -1.62, -d2 - 0.09, z0 + 1.05, 0.08, 0.03, 0.14, mat_idx=9)          # latch
    add_box(bm, 1.4, -d2 - 0.03, z0 + 1.65, 2.56, 0.04, 1.36, mat_idx=13)           # dark shop interior
    add_box(bm, 1.4, -d2 - 0.42, z0 + 0.85, 2.9, 0.8, 0.1, mat_idx=5)              # bread counter
    for bx in (0.1, 2.7):
        add_timber_beam(bm, Vector((bx, -d2 - 0.05, z0 + 0.2)), Vector((bx, -d2 - 0.72, z0 + 0.78)), width=0.1, depth=0.1, mat_idx=1)
    for i in range(6):                                                               # round loaves
        for j, ly in enumerate((-d2 - 0.62, -d2 - 0.3)):
            add_beehive_dome(bm, 0.3 + i * 0.44 + j * 0.2, ly, z0 + 0.9, 0.15, 0.11, segs_u=8, segs_v=3, mat_idx=14)
    _ws_prism(bm, [(-0.05, -d2 - 0.06, z0 + 2.5), (2.85, -d2 - 0.06, z0 + 2.5),
                   (2.85, -d2 - 0.85, z0 + 2.28), (-0.05, -d2 - 0.85, z0 + 2.28)], 0.06, 5)   # lifted shutter
    for bx in (0.0, 2.8):
        add_timber_beam(bm, Vector((bx, -d2 - 0.08, z1 - 0.3)), Vector((bx, -d2 - 0.82, z0 + 2.26)), width=0.04, depth=0.04, mat_idx=9)

    # Framed ground-storey flanks and back, leaded windows in alternate bays
    for (a, b, out), ends in zip(_ws_three_sides(w2, d2), _WS_THREE_SIDE_ENDS):
        add_half_timber_wall(bm, a, b, z0, z1, Vector(out), mat_timber=1, mat_glass=13, ends=ends)

    # Jetty: projecting joist ends and corner brackets under the overhang
    for i in range(11):
        add_box(bm, -3.5 + i * 0.7, -d2 - 0.18, z1 - 0.11, 0.16, 0.36, 0.2, mat_idx=1)
    for i in range(14):
        add_box(bm, w2 + 0.18, -5.2 + i * 0.8, z1 - 0.11, 0.36, 0.16, 0.2, mat_idx=1)
    for bx in (-w2 + 0.1, w2 - 0.1):
        add_timber_beam(bm, Vector((bx, -d2 - 0.05, z1 - 0.8)), Vector((bx, -dj + 0.02, z1 - 0.12)), width=0.16, depth=0.16, mat_idx=1)
    for by in (-d2 + 0.1, d2 - 0.1):
        add_timber_beam(bm, Vector((w2 + 0.05, by, z1 - 0.8)), Vector((wj - 0.02, by, z1 - 0.12)), width=0.16, depth=0.16, mat_idx=1)

    # Jettied upper storey: plaster panels in a full timber frame on all four sides
    add_box(bm, 0, 0, (z1 + zt) * 0.5, Wj, Dj, zt - z1, mat_idx=0)
    for a, b, out in _ws_four_sides(wj, dj):
        add_half_timber_wall(bm, a, b, z1, zt, Vector(out), mat_timber=1, mat_glass=13, ends=("post", "butt"))

    # Steep clay-tile roof with framed plaster gables and loft windows; brick kitchen chimney
    add_gable_roof(bm, 0, 0, zt, Wj, Dj, 4.9, overhang=0.4, mat_roof=2, mat_plaster=0, mat_timber=1, mat_glass=13,
                   frame_wrap=True)
    add_box(bm, 1.3, 3.2, 10.8, 0.7, 0.7, 2.4, mat_idx=3)
    add_box(bm, 1.3, 3.2, 12.05, 0.9, 0.9, 0.1, mat_idx=3)
    add_box(bm, 1.3, 3.2, 12.11, 0.5, 0.5, 0.02, mat_idx=12)

    # Gilded pretzel (precel) on a wrought-iron bracket at the front-left corner
    bx, by, bz = -wj - 0.05, -dj - 0.1, 5.9
    add_box(bm, bx + 0.02, by + 0.02, bz - 0.3, 0.1, 0.12, 0.8, mat_idx=9)
    add_timber_beam(bm, Vector((bx, by, bz)), Vector((bx - 1.25, by, bz)), width=0.06, depth=0.06, mat_idx=9)
    add_timber_beam(bm, Vector((bx, by, bz - 0.6)), Vector((bx - 0.95, by, bz)), width=0.05, depth=0.05, mat_idx=9)
    for hx in (bx - 0.55, bx - 1.15):
        add_timber_beam(bm, Vector((hx, by, bz)), Vector((hx, by, bz - 0.2)), width=0.03, depth=0.03, mat_idx=9)
    add_curved_pretzel(bm, bx - 0.85, by, bz - 0.55, size=0.85, mat_gold=8)

    # Beehive bread oven (brick dome on a brick plinth with a wood store), stone flue
    ox, oy = 5.6, -0.8
    add_box(bm, ox, oy, 0.6, 2.9, 3.6, 1.2, mat_idx=15)                              # plinth
    add_box(bm, ox, oy - 1.8 - 0.02, 0.5, 1.2, 0.06, 0.7, mat_idx=12)                # wood-store arch
    for i in range(3):
        for j in range(2):
            add_box(bm, ox - 0.35 + i * 0.35, oy - 1.88, 0.3 + j * 0.3, 0.26, 0.04, 0.26, mat_idx=11)
    add_box(bm, ox, oy, 1.25, 3.0, 3.7, 0.1, mat_idx=3)                              # coping
    add_beehive_dome(bm, ox, oy - 0.3, 1.3, 1.2, 1.35, segs_u=14, segs_v=6, mat_idx=15)
    add_box(bm, ox, oy - 1.45, 1.75, 0.9, 0.4, 0.9, mat_idx=3)                       # mouth arch
    add_box(bm, ox, oy - 1.45, 2.28, 1.05, 0.5, 0.16, mat_idx=3)
    add_box(bm, ox, oy - 1.68, 1.68, 0.55, 0.04, 0.5, mat_idx=7)                     # glowing mouth
    add_cylinder(bm, ox, oy - 0.3, 2.64, 0.16, 0.08, segs=8, mat_idx=12)             # smoke hole
    add_ashlar_chimney(bm, ox, oy + 1.35, 1.3, w=0.9, d=0.8, h=5.4, mat_stone=4, mat_soot=12)

    # (No lean-to over the oven: from the iso camera a roof hides the dome, the bakery's
    # signature; the reference shows it open-air.)

    # Bread peel leaning on the oven, firewood cords, flour sacks, rain barrel
    add_timber_beam(bm, Vector((4.3, -2.95, 0.02)), Vector((4.5, -2.62, 1.95)), width=0.06, depth=0.06, mat_idx=16)
    add_box(bm, 4.52, -2.6, 2.12, 0.32, 0.04, 0.36, mat_idx=16)
    add_prop_firewood_pile(bm, cx=6.3, cy=-3.75, cz=0, w=1.5, d=0.9, h=1.0, mat_bark=10, mat_end=11)
    add_prop_firewood_pile(bm, cx=5.4, cy=2.0, cz=0, w=2.2, d=1.0, h=1.3, mat_bark=10, mat_end=11)
    add_prop_flour_sacks(bm, [(4.45, -4.65, 0, 0), (4.5, -4.0, 0, 0), (5.15, -4.35, 0, 0),
                              (4.55, -4.33, 0.68, 0), (-4.25, -4.95, 0, 0), (-4.3, -4.3, 0, 0)], mat_sack=6)
    _ws_barrel(bm, -4.35, 2.0, 0.0, r=0.42, h=1.05, mat_wood=5, mat_hoop=9)

    _ws_finish(bm, mat_list, "Mesh_HouseBaker", "HouseBaker", "house_baker")


# -------------------------------------------------------------
# 13. Tanner's Riverside Workshop (Garbarnia)
# -------------------------------------------------------------
def build_tanner_workshop(mats):
    """Weathered log workshop (reference_photos/tanner_workshop) with saddle-notched corners,
    thick thatch with ridge sticks, a front-gable drying gallery hung with hides, a yard of six
    open stave vats (dark tan liquor, bark liquor, white lime), A-frame hide racks, a fleshing
    beam on its trestle and stacks of cured leather."""
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"],       # 0
        mats["timber_weathered"],  # 1  (-> TimberLogWeathered at export: log body)
        mats["roof_thatch"],       # 2
        mats["tannin_water"],      # 3
        mats["hide_leather"],      # 4
        mats["hide_raw"],          # 5
        mats["stone_limestone"],   # 6  (-> StoneFieldstone)
        mats["timber_plank"],      # 7
        mats["plaster_white"],     # 8  lime-pit liquor
        mats["iron_wrought"],      # 9
        mats["glass_dark"],        # 10
    ]

    W, D = 7.0, 11.0
    w2, d2 = W * 0.5, D * 0.5
    zp, ze = 0.5, 3.4

    # Fieldstone footing, weathered log body with crossed log ends at the corners
    add_box(bm, 0, 0, zp * 0.5, W + 0.3, D + 0.3, zp, mat_idx=6)
    add_box(bm, 0, 0, (zp + ze) * 0.5, W, D, ze - zp, mat_idx=1)
    add_log_corner_crossings(bm, 0, 0, W, D, zp, ze, course=0.25, stub=0.35, mat_idx=1)

    # Plank door with frame, small shuttered windows (street and camera flank)
    dx = -1.6
    add_box(bm, dx, -d2 - 0.04, zp + 1.05, 1.0, 0.06, 2.1, mat_idx=7)
    for sx in (-1.0, 1.0):
        add_timber_beam(bm, Vector((dx + sx * 0.6, -d2 - 0.07, zp)), Vector((dx + sx * 0.6, -d2 - 0.07, zp + 2.25)), width=0.14, depth=0.14, mat_idx=0)
    add_timber_beam(bm, Vector((dx - 0.75, -d2 - 0.07, zp + 2.25)), Vector((dx + 0.75, -d2 - 0.07, zp + 2.25)), width=0.16, depth=0.16, mat_idx=0)
    for zs in (zp + 0.4, zp + 1.7):
        add_box(bm, dx, -d2 - 0.08, zs, 0.75, 0.02, 0.07, mat_idx=9)
    add_wall_window(bm, Vector((1.6, -d2, 2.2)), (1, 0, 0), (0, -1, 0), 0.7, 0.6, mat_glass=10, mat_frame=7, frame=0.1, shutters_mat=7)
    for wy in (-2.6, 1.8):
        add_wall_window(bm, Vector((w2, wy, 2.2)), (0, 1, 0), (1, 0, 0), 0.7, 0.6, mat_glass=10, mat_frame=7, frame=0.1, shutters_mat=7)
    add_wall_window(bm, Vector((-w2, 0.0, 2.2)), (0, 1, 0), (-1, 0, 0), 0.7, 0.6, mat_glass=10, mat_frame=7, frame=0.1)

    # Thick thatch, board gables, ridge sticks (kozly)
    rh, ov = 4.1, 0.55
    add_gable_roof(bm, 0, 0, ze, W, D, rh, overhang=ov, mat_roof=2, mat_plaster=7, mat_timber=7,
                   frame=False, loft_windows=0, eave_lip=0.3)
    _ws_ridge_crosses(bm, 0, (-4.6, -2.3, 0.0, 2.3, 4.6), ze + rh, rh / (w2 + ov), 0)

    # Front-gable drying gallery (susharnia): loft opening, plank deck on brackets, railing, hides
    add_box(bm, 0, -d2 - 0.03, ze + 1.15, 1.6, 0.04, 1.3, mat_idx=10)
    add_box(bm, 0, -d2 - 0.55, ze + 0.05, 3.4, 1.1, 0.1, mat_idx=7)
    for gx in (-1.5, 1.5):
        add_timber_beam(bm, Vector((gx, -d2 - 0.05, ze - 0.75)), Vector((gx, -d2 - 0.98, ze - 0.02)), width=0.12, depth=0.12, mat_idx=0)
    for gx in (-1.62, -0.55, 0.55, 1.62):
        add_timber_beam(bm, Vector((gx, -d2 - 1.03, ze + 0.1)), Vector((gx, -d2 - 1.03, ze + 1.05)), width=0.08, depth=0.08, mat_idx=0)
    add_timber_beam(bm, Vector((-1.7, -d2 - 1.03, ze + 1.0)), Vector((1.7, -d2 - 1.03, ze + 1.0)), width=0.1, depth=0.1, mat_idx=0)
    for i, (hx, m) in enumerate(((-1.08, 5), (0.0, 4), (1.08, 5))):
        add_box(bm, hx, -d2 - 1.12, ze + 0.32 - 0.1 * i, 0.82, 0.04, 1.3 - 0.1 * (i % 2), mat_idx=m)

    # Six open stave vats: dark tannin, bark liquor and white lime pits, plank walk between
    for vx, vy, liquor in ((4.9, -4.3, 3), (7.2, -4.3, 4), (4.9, -2.0, 8),
                           (7.2, -2.0, 3), (4.9, 0.3, 4), (7.2, 0.3, 3)):
        _ws_tub(bm, vx, vy, 0.0, 0.88, 0.8, mat_wood=7, mat_fill=liquor, mat_hoop=9, segs=14, fill=0.82)
    add_box(bm, 6.05, -2.0, 0.05, 0.4, 6.2, 0.1, mat_idx=7)
    add_timber_beam(bm, Vector((5.3, -2.0, 0.6)), Vector((6.2, -1.6, 2.2)), width=0.06, depth=0.06, mat_idx=7)   # stirring pole

    # A-frame hide racks behind the vats and in the forecourt
    _ws_hide_rack(bm, 4.4, 8.0, 3.6, 2.6, [5, 4, 5, 4], mat_frame=0)
    _ws_hide_rack(bm, 4.4, 7.9, -6.6, 2.5, [4, 5, 4], mat_frame=0)

    # Fleshing beam (log on a trestle) with a hide over it, cured leather stacks, tanbark heap
    _ws_cyl(bm, (-1.4, -6.9, 0.22), (0.2, -7.9, 1.0), 0.2, segs=10, mat=1)
    for lx, ly in ((-0.2, -8.3), (0.6, -7.5)):
        add_timber_beam(bm, Vector((lx, ly, 0.0)), Vector((0.2, -7.9, 0.95)), width=0.1, depth=0.1, mat_idx=0)
    add_timber_beam(bm, Vector((-0.75, -7.3, 0.72)), Vector((-0.25, -7.62, 0.9)), width=0.03, depth=0.22, mat_idx=9)   # drawknife
    for sx, sy in ((-2.4, -7.0), (-2.6, -8.3)):
        for k in range(6):
            jx, jy = 0.05 * ((k * 3) % 3 - 1), 0.04 * ((k * 2) % 3 - 1)
            add_box(bm, sx + jx, sy + jy, 0.06 + k * 0.12, 1.2, 0.9, 0.11, mat_idx=4 if k % 2 else 5)
    add_beehive_dome(bm, 2.4, -7.7, 0.0, 0.9, 0.55, segs_u=10, segs_v=3, mat_idx=4)
    _ws_barrel(bm, 3.3, -6.2, 0.0, r=0.38, h=0.95, mat_wood=7, mat_hoop=9)

    _ws_finish(bm, mat_list, "Mesh_Tanner", "HouseTanner", "house_tanner")


# -------------------------------------------------------------
# 14. Brewer's Malthouse (Slodownia)
# -------------------------------------------------------------
def build_brewer_malthouse(mats):
    """Malthouse (reference_photos/brewer_malthouse): fieldstone ground floor with pointed windows
    and portal, framed upper storey whose bays are slatted malt louvres, shingle roof with a
    louvred ridge vent, copper-kettle sign, cask-washing troughs, stacked lying casks, tables."""
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"],  # 0  (-> StoneFieldstone)
        mats["timber_dark"],      # 1
        mats["roof_shingle"],     # 2
        mats["copper_patina"],    # 3
        mats["timber_plank"],     # 4
        mats["water_clean"],      # 5
        mats["iron_wrought"],     # 6
        mats["glass_dark"],       # 7
        mats["plaster_cream"],    # 8
        mats["soot_black"],       # 9
        mats["timber_weathered"], # 10  louvre slats
    ]

    W, D = 8.6, 13.5
    w2, d2 = W * 0.5, D * 0.5
    zg, zt = 4.2, 7.8
    Wu, Du = W + 0.3, D + 0.3
    wu, du = Wu * 0.5, Du * 0.5

    # Stone ground floor: plinth step, walls, string course
    add_box(bm, 0, 0, zg * 0.5, W, D, zg, mat_idx=0)
    add_box(bm, 0, 0, 0.3, W + 0.2, D + 0.2, 0.6, mat_idx=0)
    add_box(bm, 0, 0, zg - 0.1, W + 0.14, D + 0.14, 0.2, mat_idx=0)

    # Pointed portal with plank door and step; pointed windows on every side
    add_wall_window(bm, Vector((0.0, -d2, 0.6 + 1.25)), (1, 0, 0), (0, -1, 0), 1.5, 2.5, mat_glass=4,
                    mat_frame=0, frame=0.26, pointed=True)
    add_box(bm, 0, -d2 - 0.45, 0.15, 2.2, 0.9, 0.3, mat_idx=0)

    def lancet(c, along, out):
        add_wall_window(bm, c, along, out, 0.8, 1.3, mat_glass=7, mat_frame=0, frame=0.16, pointed=True)

    for wx in (-2.7, 2.7):
        lancet(Vector((wx, -d2, 2.3)), (1, 0, 0), (0, -1, 0))
        lancet(Vector((wx, d2, 2.3)), (1, 0, 0), (0, 1, 0))
    for sx in (-1.0, 1.0):
        for wy in (-4.8, -1.6, 1.6, 4.8):
            lancet(Vector((sx * w2, wy, 2.3)), (0, 1, 0), (sx, 0, 0))

    # Framed upper storey; alternate inner bays are tall malt-drying louvres
    add_box(bm, 0, 0, (zg + zt) * 0.5, Wu, Du, zt - zg, mat_idx=8)
    rails = (0.6, 3.0)
    for a, b, out in _ws_four_sides(wu, du):
        add_half_timber_wall(bm, a, b, zg, zt, Vector(out), mat_timber=1, rails=rails, windows=False,
                             ends=("post", "butt"))
        av, bv = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
        length = (bv - av).length
        t = (bv - av) / length
        n = max(3, round(length / 1.5))                  # same bay layout as add_half_timber_wall
        step = length / n
        for i in range(1, n - 1, 2):
            c = av + t * ((i + 0.5) * step) + Vector((0, 0, zg + (rails[0] + rails[1]) * 0.5))
            _ws_louvre(bm, c, t, Vector(out), step - 0.4, rails[1] - rails[0] - 0.3, mat_back=9, mat_slat=10, slats=7)

    # Shingle roof with framed gables and a louvred ridge ventilator (malt-kiln vent)
    rh = 4.3
    add_gable_roof(bm, 0, 0, zt, Wu, Du, rh, overhang=0.45, mat_roof=2, mat_plaster=8, mat_timber=1, mat_glass=7,
                   frame_wrap=True)
    ridge = zt + rh
    add_box(bm, 0, 2.5, ridge, 1.0, 1.4, 0.8, mat_idx=1)
    for sx in (-1.0, 1.0):
        _ws_louvre(bm, Vector((sx * 0.5, 2.5, ridge + 0.05)), (0, 1, 0), (sx, 0, 0), 1.1, 0.55, mat_back=9, mat_slat=10, slats=3)
    add_sloped_roof(bm, 0, 2.5, ridge + 0.4, 1.0, 1.4, 0.32, overhang=0.15, mat_idx=2)

    # Copper brew-kettle sign hung from an iron bracket at the camera-facing front corner
    sx0, sy0, sz0 = wu + 0.05, -du - 0.1, 6.7
    add_box(bm, sx0, sy0 + 0.05, sz0 - 0.35, 0.1, 0.1, 0.9, mat_idx=6)
    add_timber_beam(bm, Vector((sx0, sy0, sz0)), Vector((sx0 + 1.35, sy0, sz0)), width=0.06, depth=0.06, mat_idx=6)
    add_timber_beam(bm, Vector((sx0, sy0, sz0 - 0.7)), Vector((sx0 + 1.0, sy0, sz0)), width=0.05, depth=0.05, mat_idx=6)
    for hx in (sx0 + 0.45, sx0 + 1.25):
        add_timber_beam(bm, Vector((hx, sy0, sz0)), Vector((hx, sy0, sz0 - 0.25)), width=0.03, depth=0.03, mat_idx=6)
    add_box(bm, sx0 + 0.85, sy0, sz0 - 0.82, 1.0, 0.06, 1.15, mat_idx=4)
    _ws_lathe(bm, sx0 + 0.85, sy0 - 0.3, sz0 - 1.25, [(0.12, 0.0), (0.24, 0.12), (0.25, 0.3), (0.13, 0.45),
                                                    (0.05, 0.6), (0.07, 0.68)], 10, 3)

    # Cask-washing troughs on the +X flank, stacks of lying casks, loose upright casks
    for ty in (-4.6, -1.9, 0.8, 3.5):
        add_water_trough(bm, 5.6, ty, 0, w=1.1, d=2.3, h=0.7, mat_wood=4, mat_water=5)
    r = 0.42
    for y0 in (-3.6, 1.3):
        for yy in (y0, y0 + 1.05):
            for row, count in enumerate((3, 2, 1)):
                for i in range(count):
                    x = 6.82 + row * 0.43 + i * 0.86
                    _ws_cask(bm, (x, yy, r + row * 0.73), (0, 1, 0), r=r, length=1.0, mat_wood=4, mat_hoop=6)
    for bxp, byp in ((5.3, -6.3), (6.2, -6.6), (5.6, -7.4), (5.6, 5.8), (6.5, 5.6)):
        _ws_barrel(bm, bxp, byp, 0.0, r=0.4, h=1.0, mat_wood=4, mat_hoop=6)

    # Forecourt drinking tables
    add_tavern_table_and_benches(bm, -2.2, -d2 - 2.8, 0, mat_wood=4)
    add_tavern_table_and_benches(bm, 2.2, -d2 - 2.8, 0, mat_wood=4)

    _ws_finish(bm, mat_list, "Mesh_Brewer", "HouseBrewer", "house_brewer")


# -------------------------------------------------------------
# 15. Blacksmith's Workshop & Open Forge (Kuznia)
# -------------------------------------------------------------
def build_blacksmith_workshop(mats):
    """Forge (reference_photos/blacksmith_workshop): an open, braced timber forge shed with a
    shingle gable roof and signboard in front of a stone-and-framed dwelling. Inside: stone hearth
    with glowing coals, brick hood and tall stone chimney, leather bellows, anvil on a stump,
    quench trough, tool rack, grindstone, coal heap and an open coal bunker on +X."""
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"], # 0  (-> StoneFieldstone)
        mats["brick_gothic"],    # 1
        mats["timber_dark"],     # 2
        mats["roof_shingle"],    # 3
        mats["iron_steel"],      # 4
        mats["fire_orange"],     # 5
        mats["soot_black"],      # 6
        mats["water_clean"],     # 7
        mats["coal_black"],      # 8
        mats["timber_plank"],    # 9
        mats["glass_dark"],      # 10
        mats["plaster_cream"],   # 11
        mats["iron_wrought"],    # 12
        mats["hide_leather"],    # 13
        mats["timber_weathered"] # 14
    ]

    # Dwelling/workshop behind the forge: y -1.8 .. 6.2
    yb, Wb, Db = 2.2, 6.8, 8.0
    wb, db = Wb * 0.5, Db * 0.5
    zg, zt = 3.4, 6.6
    Wu, Du = Wb + 0.3, Db + 0.3
    wu, du = Wu * 0.5, Du * 0.5
    add_box(bm, 0, yb, zg * 0.5, Wb, Db, zg, mat_idx=0)
    add_box(bm, 0, yb, 0.25, Wb + 0.16, Db + 0.16, 0.5, mat_idx=0)
    add_box(bm, 0, yb, (zg + zt) * 0.5, Wu, Du, zt - zg, mat_idx=11)
    for a, b, out, glass in [((-wu, yb - du), (wu, yb - du), (0, -1, 0), None),   # hidden behind the forge roof
                             ((wu, yb - du), (wu, yb + du), (1, 0, 0), 10),
                             ((wu, yb + du), (-wu, yb + du), (0, 1, 0), 10),
                             ((-wu, yb + du), (-wu, yb - du), (-1, 0, 0), 10)]:
        add_half_timber_wall(bm, a, b, zg, zt, Vector(out), mat_timber=2, mat_glass=glass, ends=("post", "butt"))
    add_gable_roof(bm, 0, yb, zt, Wu, Du, 4.2, overhang=0.35, mat_roof=3, mat_plaster=11, mat_timber=2, mat_glass=10,
                   frame_wrap=True)

    # +X flank: plank door, shuttered windows
    add_box(bm, wb + 0.04, 2.8, 1.05 + 0.25, 0.06, 1.0, 2.1, mat_idx=9)
    for sy in (-1.0, 1.0):
        add_timber_beam(bm, Vector((wb + 0.07, 2.8 + sy * 0.6, 0.25)), Vector((wb + 0.07, 2.8 + sy * 0.6, 2.5)), width=0.14, depth=0.14, mat_idx=2)
    add_timber_beam(bm, Vector((wb + 0.07, 2.05, 2.5)), Vector((wb + 0.07, 3.55, 2.5)), width=0.16, depth=0.16, mat_idx=2)
    add_wall_window(bm, Vector((wb, 4.9, 1.9)), (0, 1, 0), (1, 0, 0), 0.8, 0.8, mat_glass=10, mat_frame=2, frame=0.12, shutters_mat=9)
    add_wall_window(bm, Vector((0.0, yb + db, 1.9)), (1, 0, 0), (0, 1, 0), 0.8, 0.8, mat_glass=10, mat_frame=2, frame=0.12)

    # Open forge shed: braced posts, tie beams, wall plates, shingle gable roof, board gable
    yf0, yf1, hx, ze = -7.2, -1.8, 3.5, 3.3
    for x in (-hx, hx):
        sx = 1.0 if x > 0 else -1.0
        for y in (yf0, -4.5):
            add_timber_beam(bm, Vector((x, y, 0)), Vector((x, y, ze)), width=0.24, depth=0.24, mat_idx=2)
            add_timber_beam(bm, Vector((x, y, ze - 0.9)), Vector((x - sx * 0.9, y, ze)), width=0.13, depth=0.13, mat_idx=2)
        add_timber_beam(bm, Vector((x, yf0, ze - 0.9)), Vector((x, yf0 + 0.9, ze)), width=0.13, depth=0.13, mat_idx=2)
        add_timber_beam(bm, Vector((x, -4.5, ze - 0.9)), Vector((x, -3.6, ze)), width=0.13, depth=0.13, mat_idx=2)
        add_timber_beam(bm, Vector((x, yf0 - 0.15, ze)), Vector((x, yf1, ze)), width=0.2, depth=0.2, mat_idx=2)
    for y in (yf0, -4.5):
        add_timber_beam(bm, Vector((-hx - 0.1, y, ze)), Vector((hx + 0.1, y, ze)), width=0.22, depth=0.22, mat_idx=2)
    add_gable_roof(bm, 0, (yf0 + yf1) * 0.5, ze + 0.12, 2 * hx, yf1 - yf0, 2.6, overhang=0.35,
                   mat_roof=3, mat_plaster=9, mat_timber=2, frame=False, loft_windows=0)
    add_timber_beam(bm, Vector((0, yf0 - 0.05, ze + 0.12)), Vector((0, yf0 - 0.05, ze + 2.4)), width=0.16, depth=0.16, mat_idx=2)
    add_box(bm, 0, yf0 - 0.36, ze - 0.38, 2.6, 0.06, 0.45, mat_idx=9)              # BLACKSMITH signboard
    for hxp in (-1.0, 1.0):
        add_timber_beam(bm, Vector((hxp, yf0 - 0.2, ze - 0.11)), Vector((hxp, yf0 - 0.35, ze - 0.16)), width=0.03, depth=0.03, mat_idx=12)
    hc = Vector((0.75, yf0 - 0.08, ze + 1.05))                                     # iron horseshoe on the gable
    pts = [hc + Vector((0.3 * math.cos(math.radians(a)), 0, 0.3 * math.sin(math.radians(a))))
           for a in range(-50, 231, 40)]
    for p, q in zip(pts[:-1], pts[1:]):
        add_timber_beam(bm, p, q, width=0.07, depth=0.05, mat_idx=12)

    # Hearth: stone base, coal bed with glowing fire, brick back and hood, stone chimney
    fx, fy = 1.6, -2.75
    add_box(bm, fx, fy, 0.45, 2.2, 1.7, 0.9, mat_idx=0)
    add_box(bm, fx, fy - 0.2, 0.95, 1.4, 1.0, 0.1, mat_idx=8)
    add_box(bm, fx, fy - 0.25, 1.03, 0.8, 0.6, 0.06, mat_idx=5)
    add_box(bm, fx, -2.15, 1.6, 2.0, 0.5, 1.3, mat_idx=1)
    add_box(bm, fx, -2.7, 2.5, 2.0, 1.4, 0.5, mat_idx=1)
    add_box(bm, fx, -2.5, 3.0, 1.4, 1.0, 0.5, mat_idx=1)
    add_ashlar_chimney(bm, fx, -2.5, 3.25, w=1.0, d=1.0, h=7.9, mat_stone=0, mat_soot=6)

    # Leather bellows on a stand, nozzle into the hearth
    add_box(bm, -0.1, -2.6, 0.45, 0.6, 0.9, 0.84, mat_idx=14)
    add_box(bm, -0.1, -2.6, 0.9, 0.85, 1.2, 0.06, mat_idx=9)
    add_box(bm, -0.1, -2.65, 1.08, 0.7, 1.0, 0.3, mat_idx=13)
    add_box(bm, -0.1, -2.6, 1.26, 0.85, 1.2, 0.06, mat_idx=9)
    add_timber_beam(bm, Vector((0.3, -2.6, 1.05)), Vector((0.72, -2.75, 1.0)), width=0.08, depth=0.08, mat_idx=12)
    add_timber_beam(bm, Vector((-0.1, -2.0, 1.3)), Vector((-0.1, -1.95, 2.3)), width=0.06, depth=0.06, mat_idx=2)

    # Coal heap and workbench with vise along the back wall
    add_beehive_dome(bm, -1.9, -2.7, 0.0, 0.85, 0.65, segs_u=10, segs_v=3, mat_idx=8)
    add_box(bm, -2.9, -3.6, 0.85, 0.7, 1.8, 0.1, mat_idx=9)
    for lx in (-3.15, -2.65):
        for ly in (-4.35, -2.85):
            add_box(bm, lx, ly, 0.4, 0.1, 0.1, 0.8, mat_idx=2)
    add_box(bm, -2.7, -4.25, 1.0, 0.18, 0.22, 0.2, mat_idx=12)
    for ty in (-3.9, -3.4, -3.0):
        add_timber_beam(bm, Vector((-3.05, ty, 0.93)), Vector((-2.7, ty + 0.1, 0.93)), width=0.04, depth=0.04, mat_idx=2)
        add_box(bm, -2.68, ty + 0.1, 0.95, 0.08, 0.16, 0.07, mat_idx=12)

    # Anvil on an oak stump (base, waist, face, tapering horn)
    ax, ay = -0.2, -5.4
    _ws_cyl(bm, (ax, ay, 0.0), (ax, ay, 0.7), 0.42, segs=10, mat=14)
    add_box(bm, ax, ay, 0.78, 0.42, 0.6, 0.16, mat_idx=4)
    add_box(bm, ax, ay, 0.96, 0.24, 0.36, 0.2, mat_idx=4)
    add_box(bm, ax, ay + 0.05, 1.13, 0.3, 0.75, 0.14, mat_idx=4)
    add_timber_beam(bm, Vector((ax, ay - 0.32, 1.13)), Vector((ax, ay - 0.52, 1.15)), width=0.13, depth=0.12, mat_idx=4)
    add_timber_beam(bm, Vector((ax, ay - 0.52, 1.15)), Vector((ax, ay - 0.72, 1.18)), width=0.06, depth=0.06, mat_idx=4)
    add_timber_beam(bm, Vector((ax + 0.05, ay + 0.1, 1.23)), Vector((ax + 0.45, ay + 0.35, 1.23)), width=0.04, depth=0.04, mat_idx=2)
    add_box(bm, ax + 0.05, ay + 0.1, 1.25, 0.1, 0.18, 0.08, mat_idx=12)

    # Quench trough with tongs, under the shed's camera-side front bay
    add_water_trough(bm, 2.7, -5.6, 0, w=0.9, d=2.2, h=0.7, mat_wood=9, mat_water=7)
    add_timber_beam(bm, Vector((2.2, -5.2, 0.72)), Vector((3.2, -5.5, 0.72)), width=0.04, depth=0.04, mat_idx=12)

    # A-frame tool rack with blades, axes and a poleaxe leaning on it
    rx = -2.7
    for ry in (-7.0, -5.3):
        add_timber_beam(bm, Vector((rx + 0.35, ry, 0)), Vector((rx, ry, 1.6)), width=0.1, depth=0.1, mat_idx=2)
        add_timber_beam(bm, Vector((rx - 0.35, ry, 0)), Vector((rx, ry, 1.6)), width=0.1, depth=0.1, mat_idx=2)
    add_timber_beam(bm, Vector((rx, -7.1, 1.55)), Vector((rx, -5.2, 1.55)), width=0.09, depth=0.09, mat_idx=2)
    for k, ty in enumerate((-6.8, -6.5, -6.2, -5.9, -5.6)):
        if k % 2 == 0:   # blade
            add_timber_beam(bm, Vector((rx + 0.42, ty, 0.05)), Vector((rx + 0.06, ty, 1.75)), width=0.08, depth=0.025, mat_idx=4)
            add_timber_beam(bm, Vector((rx + 0.12, ty - 0.12, 1.35)), Vector((rx + 0.12, ty + 0.12, 1.35)), width=0.04, depth=0.04, mat_idx=12)
        else:            # axe / poleaxe
            add_timber_beam(bm, Vector((rx + 0.42, ty, 0.05)), Vector((rx + 0.04, ty, 1.85)), width=0.045, depth=0.045, mat_idx=9)
            add_box(bm, rx + 0.07, ty, 1.68, 0.06, 0.28, 0.22, mat_idx=4)

    # Iron bar stock and a grindstone on its trestle at the shed front
    for k in range(3):
        for i in range(4 - k):
            add_timber_beam(bm, Vector((-1.9, -7.25 + i * 0.13 + k * 0.065, 0.05 + k * 0.09)),
                            Vector((-0.9, -7.25 + i * 0.13 + k * 0.065, 0.05 + k * 0.09)), width=0.09, depth=0.09, mat_idx=12)
    gx, gy = 1.0, -6.7
    for sy in (-0.3, 0.3):
        add_timber_beam(bm, Vector((gx - 0.35, gy + sy, 0)), Vector((gx - 0.1, gy + sy, 0.8)), width=0.08, depth=0.08, mat_idx=2)
        add_timber_beam(bm, Vector((gx + 0.35, gy + sy, 0)), Vector((gx + 0.1, gy + sy, 0.8)), width=0.08, depth=0.08, mat_idx=2)
    _ws_cyl(bm, (gx, gy - 0.07, 0.82), (gx, gy + 0.07, 0.82), 0.38, segs=14, mat=0)
    _ws_cyl(bm, (gx, gy - 0.4, 0.82), (gx, gy + 0.45, 0.82), 0.03, segs=6, mat=12)
    add_timber_beam(bm, Vector((gx, gy + 0.45, 0.82)), Vector((gx, gy + 0.45, 0.6)), width=0.03, depth=0.03, mat_idx=12)

    # Open coal bunker on the +X flank, barrel by the rack
    add_water_trough(bm, 4.6, 0.0, 0, w=2.1, d=2.2, h=1.0, mat_wood=9, mat_water=8)
    add_beehive_dome(bm, 4.6, 0.0, 0.84, 0.8, 0.42, segs_u=10, segs_v=3, mat_idx=8)
    _ws_barrel(bm, -3.3, -4.4, 0.0, r=0.38, h=0.95, mat_wood=9, mat_hoop=12)

    _ws_finish(bm, mat_list, "Mesh_Blacksmith", "BlacksmithWorkshop", "blacksmith_workshop")


# -------------------------------------------------------------
# 16. Potter's Workshop & Kiln (Garncarnia)
# -------------------------------------------------------------
def build_potter_workshop(mats):
    """Thatched half-timbered cottage (reference_photos/potter_workshop) with a domed brick
    updraft kiln on a fieldstone ring, a stoked fire mouth and stone flue, a three-tier rack of
    jugs, amphorae and bowls, a kick wheel and bench, raw clay heaps and firewood."""
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_cream"],      # 0
        mats["timber_dark"],        # 1
        mats["roof_thatch"],        # 2
        mats["brick_oven"],         # 3
        mats["stone_limestone"],    # 4  (-> StoneFieldstone)
        mats["pottery_terracotta"], # 5
        mats["fire_orange"],        # 6
        mats["soot_black"],         # 7
        mats["timber_plank"],       # 8
        mats["clay_mound"],         # 9
        mats["glass_dark"],         # 10
        mats["birch_bark"],         # 11
        mats["wood_end_grain"],     # 12
        mats["water_clean"],        # 13
        mats["brick_gothic"],       # 14
        mats["iron_wrought"],       # 15
    ]

    W, D = 6.8, 9.2
    w2, d2 = W * 0.5, D * 0.5
    zp, ze = 0.5, 3.4

    # Cottage: fieldstone footing, loam-plaster walls in a timber frame
    add_box(bm, 0, 0, zp * 0.5, W + 0.12, D + 0.12, zp, mat_idx=4)
    add_box(bm, 0, 0, (zp + ze) * 0.5, W, D, ze - zp, mat_idx=0)
    _ws_framed_front(bm, (-w2, -d2), (w2, -d2), zp, ze, (0, -1, 0), 1,
                     [(1.0, 2.1, zp, zp + 2.1), (4.4, 5.4, zp + 1.0, zp + 2.0)], rail=1.0)
    add_box(bm, -1.85, -d2 - 0.04, zp + 1.05, 1.06, 0.06, 2.08, mat_idx=8)
    for zs in (zp + 0.4, zp + 1.7):
        add_box(bm, -1.9, -d2 - 0.08, zs, 0.75, 0.02, 0.07, mat_idx=15)
    _ws_glaze(bm, Vector((1.5, -d2, zp + 1.5)), (1, 0, 0), (0, -1, 0), 0.94, 0.94, 10, 1)
    for (a, b, out), ends in zip(_ws_three_sides(w2, d2), _WS_THREE_SIDE_ENDS):
        add_half_timber_wall(bm, a, b, zp, ze, Vector(out), mat_timber=1, mat_glass=10, rails=(0.9, 2.3), ends=ends)

    # Thick thatch with framed gables, loft window and ridge sticks
    rh, ov = 4.2, 0.55
    add_gable_roof(bm, 0, 0, ze, W, D, rh, overhang=ov, mat_roof=2, mat_plaster=0, mat_timber=1,
                   mat_glass=10, loft_windows=1, eave_lip=0.3)
    _ws_ridge_crosses(bm, 0, (-3.6, -1.2, 1.2, 3.6), ze + rh, rh / (w2 + ov), 1)

    # Updraft kiln: fieldstone ring, brick dome with vent, stokehole arch with fire, stone flue
    kx, ky = 5.6, -0.5
    add_cylinder(bm, kx, ky, 0.55, 1.7, 1.1, segs=16, mat_idx=4)
    add_beehive_dome(bm, kx, ky, 1.1, 1.5, 1.7, segs_u=16, segs_v=6, mat_idx=3)
    add_cylinder(bm, kx, ky, 2.77, 0.32, 0.14, segs=10, mat_idx=7)
    add_box(bm, kx, ky - 1.8, 0.6, 1.2, 0.5, 1.2, mat_idx=14)
    add_box(bm, kx, ky - 1.8, 1.26, 1.35, 0.55, 0.12, mat_idx=14)
    add_box(bm, kx, ky - 2.08, 0.5, 0.65, 0.04, 0.65, mat_idx=6)
    for i in range(3):
        add_box(bm, kx - 0.25 + i * 0.25, ky - 2.12, 0.18, 0.18, 0.04, 0.18, mat_idx=12)
    add_box(bm, kx, 1.15, 1.5, 0.5, 0.6, 0.5, mat_idx=14)
    add_ashlar_chimney(bm, kx, 1.75, 0.0, w=1.0, d=1.0, h=7.6, mat_stone=4, mat_soot=7)

    # Three-tier drying rack loaded with jugs, amphorae and bowls (+X yard)
    rx0, rx1, ry0, ry1 = 7.6, 8.7, -4.6, -0.2
    for x in (rx0, rx1):
        for y in (ry0, (ry0 + ry1) * 0.5, ry1):
            add_timber_beam(bm, Vector((x, y, 0)), Vector((x, y, 2.3)), width=0.1, depth=0.1, mat_idx=1)
    kinds = ("jug", "amphora", "bowl", "jar")
    for t, tz in enumerate((0.5, 1.1, 1.7)):
        add_box(bm, (rx0 + rx1) * 0.5, (ry0 + ry1) * 0.5, tz, rx1 - rx0 + 0.1, ry1 - ry0 + 0.1, 0.06, mat_idx=8)
        for i in range(6):
            for j, px in enumerate((rx0 + 0.28, rx1 - 0.28)):
                kind = kinds[(i + j + t) % 3]
                _ws_pot(bm, px, ry0 + 0.4 + i * 0.72, tz + 0.03, kind, 5, s=1.0 if kind != "bowl" else 1.2)

    # Kick wheel and work bench, water tub, clay heaps, firewood, storage jars
    add_box(bm, 4.6, -3.9, 0.75, 1.4, 0.7, 0.08, mat_idx=8)
    for lx in (4.0, 5.2):
        for ly in (-4.15, -3.65):
            add_box(bm, lx, ly, 0.36, 0.08, 0.08, 0.72, mat_idx=1)
    _ws_pot(bm, 4.2, -3.9, 0.79, "jug", 5, s=0.8)
    _ws_pot(bm, 4.7, -3.95, 0.79, "bowl", 5)
    wx, wy = 5.9, -3.9
    _ws_cyl(bm, (wx, wy, 0.15), (wx, wy, 0.25), 0.42, segs=12, mat=8)
    _ws_cyl(bm, (wx, wy, 0.25), (wx, wy, 0.8), 0.05, segs=6, mat=1)
    _ws_cyl(bm, (wx, wy, 0.8), (wx, wy, 0.86), 0.24, segs=10, mat=8)
    _ws_lathe(bm, wx, wy, 0.86, [(0.12, 0.0), (0.15, 0.1), (0.1, 0.22)], 8, 9)
    add_box(bm, 6.55, -3.9, 0.25, 0.4, 0.4, 0.5, mat_idx=8)
    _ws_tub(bm, 5.3, -4.75, 0.0, 0.26, 0.36, mat_wood=8, mat_fill=13, mat_hoop=15, segs=10)
    for cxm, cym, cr in ((6.8, -4.3, 0.45), (7.0, -3.4, 0.36), (6.5, -4.85, 0.3)):
        add_beehive_dome(bm, cxm, cym, 0.0, cr, cr * 0.85, segs_u=10, segs_v=3, mat_idx=9)
    add_prop_firewood_pile(bm, cx=7.9, cy=2.4, cz=0, w=1.5, d=1.0, h=1.1, mat_bark=11, mat_end=12)
    for jx in (-2.95, -0.75):
        _ws_pot(bm, jx, -4.95, 0.0, "jar", 5, s=0.8)

    _ws_finish(bm, mat_list, "Mesh_Potter", "HousePotter", "house_potter")


# -------------------------------------------------------------
# 17. Weaver's Workshop & Dye Yard (Tkalnia)
# -------------------------------------------------------------
def build_weaver_workshop(mats):
    """Weaver's house (reference_photos/weaver_workshop): framed ground floor, jettied upper storey
    densely braced with St. Andrew's crosses, shingle roof with a front-gable loft door and wool
    hoist, two fired dye vats (madder red, indigo blue), cloth-drying rails, a treadle loom under
    a lean-to in the forecourt and a handcart of cloth bolts."""
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_white"],  # 0
        mats["timber_dark"],    # 1
        mats["roof_shingle"],   # 2
        mats["dye_indigo"],     # 3
        mats["dye_madder"],     # 4
        mats["cloth_indigo"],   # 5
        mats["cloth_madder"],   # 6
        mats["cloth_violet"],   # 7
        mats["cloth_gold"],     # 8
        mats["stone_limestone"],# 9  (-> StoneFieldstone)
        mats["fire_orange"],    # 10
        mats["timber_plank"],   # 11
        mats["flour_sack_cloth"], # 12 wool sacks
        mats["glass_dark"],     # 13
        mats["iron_wrought"],   # 14
        mats["birch_bark"],     # 15
        mats["wood_end_grain"], # 16
        mats["cloth_red"],      # 17
    ]

    W, D = 7.8, 11.5
    w2, d2 = W * 0.5, D * 0.5
    zp, z1, zt = 0.6, 3.9, 7.3
    Wu, Du = W + 0.5, D + 0.5
    wu, du = Wu * 0.5, Du * 0.5

    # Fieldstone plinth, framed ground storey: door and two leaded windows on the street
    add_box(bm, 0, 0, zp * 0.5, W + 0.12, D + 0.12, zp, mat_idx=9)
    add_box(bm, 0, 0, (zp + z1) * 0.5, W, D, z1 - zp, mat_idx=0)
    _ws_framed_front(bm, (-w2, -d2), (w2, -d2), zp, z1, (0, -1, 0), 1,
                     [(0.9, 1.9, zp + 1.0, zp + 2.2), (2.4, 3.5, zp, zp + 2.25), (5.0, 6.6, zp + 1.0, zp + 2.2)], rail=1.0)
    add_box(bm, -0.95, -d2 - 0.04, zp + 1.12, 1.06, 0.06, 2.23, mat_idx=11)
    for zs in (zp + 0.45, zp + 1.8):
        add_box(bm, -1.0, -d2 - 0.08, zs, 0.75, 0.02, 0.07, mat_idx=14)
    _ws_glaze(bm, Vector((-2.5, -d2, zp + 1.6)), (1, 0, 0), (0, -1, 0), 0.94, 1.14, 13, 1)
    _ws_glaze(bm, Vector((1.9, -d2, zp + 1.6)), (1, 0, 0), (0, -1, 0), 1.54, 1.14, 13, 1)
    for (a, b, out), ends in zip(_ws_three_sides(w2, d2), _WS_THREE_SIDE_ENDS):
        add_half_timber_wall(bm, a, b, zp, z1, Vector(out), mat_timber=1, mat_glass=13, ends=ends)

    # Jetty joists, then the upper storey framed in St. Andrew's crosses on all sides
    for i in range(12):
        add_box(bm, -3.6 + i * 0.65, -d2 - 0.16, z1 - 0.11, 0.16, 0.32, 0.2, mat_idx=1)
    for i in range(15):
        add_box(bm, w2 + 0.16, -5.25 + i * 0.75, z1 - 0.11, 0.32, 0.16, 0.2, mat_idx=1)
    add_box(bm, 0, 0, (z1 + zt) * 0.5, Wu, Du, zt - z1, mat_idx=0)
    for a, b, out in _ws_four_sides(wu, du):
        _ws_andrew_wall(bm, a, b, z1, zt, Vector(out), mat_timber=1, mat_glass=13, ends=("post", "butt"))

    # Shingle roof; gable frames drawn here so the front one can carry a loft door and hoist
    rh, ov = 4.7, 0.4
    ridge = zt + rh
    add_gable_roof(bm, 0, 0, zt, Wu, Du, rh, overhang=ov, mat_roof=2, mat_plaster=0, mat_timber=1,
                   frame=False, loft_windows=0)
    z_edge = zt + rh * (ov / (wu + ov))

    def gable_half_width(z):
        return wu * (ridge - z) / (ridge - z_edge)

    zc = 9.5
    for sgn in (-1.0, 1.0):
        yg = sgn * (du + 0.05)
        P = lambda x, z: Vector((x, yg, z))
        add_timber_beam(bm, P(-wu - 0.14, zt + 0.09), P(wu + 0.14, zt + 0.09), width=0.18, depth=0.18, mat_idx=1)
        xc = gable_half_width(zc) - 0.15
        add_timber_beam(bm, P(-xc, zc), P(xc, zc), width=0.18, depth=0.18, mat_idx=1)
        add_timber_beam(bm, P(0, zc + 0.09), P(0, ridge - 0.35), width=0.18, depth=0.18, mat_idx=1)
        for sx in (-1.0, 1.0):
            add_timber_beam(bm, P(sx * 3.4, zt + 0.18), P(sx * 0.8, zc - 0.09), width=0.15, depth=0.15, mat_idx=1)
            add_timber_beam(bm, P(sx * 0.65, zt + 0.18), P(sx * 0.65, zc - 0.09), width=0.16, depth=0.16, mat_idx=1)
            add_timber_beam(bm, P(sx * xc * 0.8, zc + 0.09), P(sx * 0.12, zc + 1.2), width=0.13, depth=0.13, mat_idx=1)
    add_box(bm, 0, -du - 0.02, (zt + 0.18 + zc - 0.09) * 0.5, 1.1, 0.04, zc - zt - 0.27, mat_idx=13)   # loft door
    add_box(bm, 0, du + 0.02, (zt + 0.18 + zc - 0.09) * 0.5, 1.1, 0.04, zc - zt - 0.27, mat_idx=13)
    hz = zc + 0.45                                                                      # hoist beam
    add_timber_beam(bm, Vector((0, -du + 0.4, hz)), Vector((0, -du - 1.7, hz)), width=0.2, depth=0.2, mat_idx=1)
    add_timber_beam(bm, Vector((0, -du - 0.1, hz - 0.9)), Vector((0, -du - 0.9, hz - 0.08)), width=0.12, depth=0.12, mat_idx=1)
    _ws_cyl(bm, (-0.05, -du - 1.5, hz - 0.3), (0.05, -du - 1.5, hz - 0.3), 0.17, segs=10, mat=11)
    add_timber_beam(bm, Vector((0, -du - 1.5, hz - 0.1)), Vector((0, -du - 1.5, hz - 0.3)), width=0.04, depth=0.04, mat_idx=14)
    add_timber_beam(bm, Vector((0, -du - 1.67, hz - 0.3)), Vector((0, -du - 1.67, 8.4)), width=0.03, depth=0.03, mat_idx=12)
    add_box(bm, 0, -du - 1.67, 8.02, 0.62, 0.62, 0.72, mat_idx=12)                    # wool sack
    add_box(bm, 0, -du - 1.67, 8.43, 0.2, 0.2, 0.1, mat_idx=12)

    # Shuttle sign at the camera-facing front corner
    add_timber_beam(bm, Vector((wu + 0.05, -du - 0.1, 6.4)), Vector((wu + 1.05, -du - 0.1, 6.4)), width=0.05, depth=0.05, mat_idx=14)
    add_timber_beam(bm, Vector((wu + 0.05, -du - 0.1, 5.9)), Vector((wu + 0.8, -du - 0.1, 6.4)), width=0.04, depth=0.04, mat_idx=14)
    add_box(bm, wu + 0.65, -du - 0.1, 5.95, 0.75, 0.05, 0.6, mat_idx=11)
    add_box(bm, wu + 0.65, -du - 0.15, 5.95, 0.5, 0.05, 0.12, mat_idx=8)

    # Two fired dye vats on fieldstone hearths, with stirring paddles
    for vy, dye in ((-3.2, 4), (0.0, 3)):
        vx = 5.7
        add_cylinder(bm, vx, vy, 0.4, 1.0, 0.8, segs=12, mat_idx=9)
        add_box(bm, vx, vy - 1.0, 0.3, 0.6, 0.12, 0.45, mat_idx=10)
        for lx in (-0.15, 0.15):
            add_timber_beam(bm, Vector((vx + lx, vy - 1.5, 0.08)), Vector((vx + lx * 0.5, vy - 0.85, 0.22)), width=0.12, depth=0.12, mat_idx=15)
        _ws_tub(bm, vx, vy, 0.8, 0.85, 0.6, mat_wood=11, mat_fill=dye, mat_hoop=14, segs=14, fill=0.82)
        add_timber_beam(bm, Vector((vx + 0.15, vy, 1.0)), Vector((vx + 0.85, vy - 0.45, 2.3)), width=0.06, depth=0.06, mat_idx=11)

    # Cloth-drying rails on the +X flank with dyed broadcloth draped over them
    rx = 7.7
    for ry, cloth in ((-4.4, 6), (-1.6, 5), (1.2, 7), (4.0, 8)):
        for sy in (-1.2, 1.2):
            add_timber_beam(bm, Vector((rx, ry + sy, 0)), Vector((rx, ry + sy, 2.1)), width=0.12, depth=0.12, mat_idx=1)
        add_timber_beam(bm, Vector((rx, ry - 1.3, 2.05)), Vector((rx, ry + 1.3, 2.05)), width=0.1, depth=0.1, mat_idx=1)
        for sx in (-1.0, 1.0):
            _ws_face(bm, [(rx + sx * 0.06, ry - 1.05, 2.0), (rx + sx * 0.06, ry + 1.05, 2.0),
                          (rx + sx * 0.18, ry + 1.05, 0.6), (rx + sx * 0.18, ry - 1.05, 0.6)],
                     cloth, (rx - sx, ry, 1.3))

    # Treadle loom with a madder warp under a shingled lean-to in the forecourt
    lx0, lx1, ly0, ly1 = -4.3, -1.6, -9.0, -6.4
    for x in (lx0 + 0.1, lx1 - 0.1):
        add_timber_beam(bm, Vector((x, ly0 + 0.1, 0)), Vector((x, ly0 + 0.1, 2.2)), width=0.14, depth=0.14, mat_idx=1)
        add_timber_beam(bm, Vector((x, ly1 - 0.1, 0)), Vector((x, ly1 - 0.1, 2.8)), width=0.14, depth=0.14, mat_idx=1)
        add_timber_beam(bm, Vector((x, ly0, 2.2)), Vector((x, ly1, 2.8)), width=0.14, depth=0.14, mat_idx=1)
    _ws_prism(bm, [(lx0 - 0.15, ly0 - 0.15, 2.36), (lx1 + 0.15, ly0 - 0.15, 2.36),
                   (lx1 + 0.15, ly1 + 0.1, 2.96), (lx0 - 0.15, ly1 + 0.1, 2.96)], 0.07, 2)
    cx, cy = (lx0 + lx1) * 0.5, (ly0 + ly1) * 0.5
    for sx in (-0.65, 0.65):
        for sy in (-0.85, 0.85):
            add_timber_beam(bm, Vector((cx + sx, cy + sy, 0)), Vector((cx + sx, cy + sy, 1.5)), width=0.09, depth=0.09, mat_idx=11)
        add_timber_beam(bm, Vector((cx + sx, cy - 0.9, 1.45)), Vector((cx + sx, cy + 0.9, 1.45)), width=0.09, depth=0.09, mat_idx=11)
    for sy in (-0.85, 0.85):
        add_timber_beam(bm, Vector((cx - 0.7, cy + sy, 0.85)), Vector((cx + 0.7, cy + sy, 0.85)), width=0.11, depth=0.11, mat_idx=11)
    add_box(bm, cx, cy, 0.87, 1.1, 1.6, 0.02, mat_idx=6)                                # warp
    add_box(bm, cx, cy - 0.35, 0.89, 1.1, 0.5, 0.02, mat_idx=17)                       # woven cloth
    add_timber_beam(bm, Vector((cx - 0.7, cy, 1.25)), Vector((cx + 0.7, cy, 1.25)), width=0.06, depth=0.06, mat_idx=11)
    add_box(bm, cx, cy - 1.05, 0.45, 1.1, 0.32, 0.08, mat_idx=11)                       # bench
    for sx in (-0.45, 0.45):
        add_box(bm, cx + sx, cy - 1.05, 0.2, 0.08, 0.28, 0.4, mat_idx=11)

    # Handcart loaded with bolts of dyed cloth
    kx, ky = 2.0, -7.6
    add_box(bm, kx, ky, 0.75, 1.3, 2.0, 0.12, mat_idx=11)
    for sx in (-0.62, 0.62):
        add_box(bm, kx + sx, ky, 0.95, 0.06, 2.0, 0.3, mat_idx=11)
        _ws_cyl(bm, (kx + sx * 1.2, ky + 0.2, 0.45), (kx + sx * 1.2 + sx * 0.1, ky + 0.2, 0.45), 0.45, segs=12, mat=1)
        add_timber_beam(bm, Vector((kx + sx * 0.5, ky - 1.0, 0.72)), Vector((kx + sx * 0.45, ky - 1.55, 0.45)), width=0.07, depth=0.07, mat_idx=1)
    _ws_cyl(bm, (kx - 1.25, ky + 0.2, 0.45), (kx + 1.25, ky + 0.2, 0.45), 0.04, segs=6, mat=14)
    add_box(bm, kx, ky + 0.2, 0.6, 0.3, 0.2, 0.2, mat_idx=11)
    for k, m in enumerate((5, 6, 7, 8, 17)):
        _ws_cyl(bm, (kx - 0.55, ky - 0.8 + k * 0.38, 0.95), (kx + 0.55, ky - 0.8 + k * 0.38, 0.95), 0.15, segs=8, mat=m)
    for k, m in enumerate((8, 5, 17, 6)):
        _ws_cyl(bm, (kx - 0.5, ky - 0.61 + k * 0.38, 1.22), (kx + 0.5, ky - 0.61 + k * 0.38, 1.22), 0.14, segs=8, mat=m)

    # Firewood for the dye fires, wool sacks by the door
    add_prop_firewood_pile(bm, cx=5.8, cy=3.5, cz=0, w=1.6, d=1.0, h=1.2, mat_bark=15, mat_end=16)
    add_prop_flour_sacks(bm, [(0.45, -6.4, 0, 0), (1.05, -6.45, 0, 0)], mat_sack=12)

    _ws_finish(bm, mat_list, "Mesh_Weaver", "HouseWeaver", "house_weaver")

def build_watermill(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"],  # 0
        mats["timber_dark"],      # 1
        mats["roof_shingle"],     # 2
        mats["water_clean"],      # 3
        mats["flour_sack_cloth"],       # 4
        mats["timber_plank"],     # 5
        mats["iron_wrought"],     # 6
        mats["plaster_cream"],    # 7
        mats["soot_black"]        # 8
    ]

    W, D = 7.0, 9.2
    w2, d2 = W * 0.5, D * 0.5

    # 1. Heavy Stone Ashlar River Foundation (Z: 0 to 4.2m)
    add_box(bm, 0, 0, 2.1, W, D, 4.2, mat_idx=0)
    # 2. Upper Half-Timber Millhouse (Z: 4.2 to 7.8m)
    add_box(bm, 0, 0, 6.0, W + 0.3, D + 0.3, 3.6, mat_idx=7)
    for cx in [-w2 - 0.15, w2 + 0.15]:
        for cy in [-d2 - 0.15, d2 + 0.15]:
            add_timber_beam(bm, Vector((cx, cy, 4.2)), Vector((cx, cy, 7.8)), width=0.22, depth=0.22, mat_idx=1)
    # 3. High-Pitched Shingle Roof
    add_pantile_roof(bm, 0, 0, 7.8, W + 0.3, D + 0.3, 4.5, overhang=0.45, courses=8, mat_tile=2, mat_trim=1, mat_plaster=7)
    # Stone Chimney
    add_ashlar_chimney(bm, 1.8, 2.2, 7.8, w=1.0, d=1.0, h=5.5, mat_stone=0, mat_soot=8)

    # -------------------------------------------------------------
    # GIANT PADDLE WATERWHEEL & ELEVATED TIMBER FLUME RACE (-X flank)
    # -------------------------------------------------------------
    wheel_x = w2 + 1.4
    wheel_y = 0.0
    wheel_z = 2.4
    wheel_radius = 2.4
    wheel_width = 1.2

    # Axle
    add_cylinder(bm, wheel_x, wheel_y, wheel_z, radius=0.35, height=wheel_width + 0.6, segs=10, mat_idx=6)
    # 16 Radial Wooden Paddles
    for i in range(16):
        ang = (i / 16) * math.pi * 2.0
        py = wheel_y + math.cos(ang) * (wheel_radius * 0.8)
        pz = wheel_z + math.sin(ang) * (wheel_radius * 0.8)
        # Paddle board
        p1 = Vector((wheel_x - wheel_width * 0.5, py, pz))
        p2 = Vector((wheel_x + wheel_width * 0.5, py, pz))
        add_timber_beam(bm, p1, p2, width=0.35, depth=0.08, mat_idx=1)
        # Internal spokes
        p_hub = Vector((wheel_x, wheel_y, wheel_z))
        add_timber_beam(bm, p_hub, Vector((wheel_x, py, pz)), width=0.10, depth=0.10, mat_idx=1)

    # Elevated Timber Flume Race (delivering water over wheel)
    flume_z = wheel_z + wheel_radius + 0.2
    flume_len = 8.5
    # Trough
    add_water_trough(bm, wheel_x, wheel_y + 1.2, flume_z - 0.4, w=1.4, d=flume_len, h=0.6, mat_wood=5, mat_water=3)
    # Flume support trestle bents
    for ty in [-1.5, 1.5, 4.0]:
        add_timber_beam(bm, Vector((wheel_x - 0.6, ty, 0)), Vector((wheel_x - 0.6, ty, flume_z)), width=0.18, depth=0.18, mat_idx=1)
        add_timber_beam(bm, Vector((wheel_x + 0.6, ty, 0)), Vector((wheel_x + 0.6, ty, flume_z)), width=0.18, depth=0.18, mat_idx=1)

    # -------------------------------------------------------------
    # TIMBER LOADING DOCK / PIER WITH FLOUR SACKS (+X flank)
    # -------------------------------------------------------------
    dock_x = 0.0
    dock_y = -d2 - 2.8
    dock_w, dock_d, dock_h = 4.2, 6.5, 1.8
    # Dock deck
    add_box(bm, dock_x, dock_y, dock_h, dock_w, dock_d, 0.16, mat_idx=5)
    # Pilings
    for px in [dock_x - dock_w * 0.4, dock_x, dock_x + dock_w * 0.4]:
        for py in [dock_y - dock_d * 0.4, dock_y, dock_y + dock_d * 0.4]:
            add_timber_beam(bm, Vector((px, py, 0)), Vector((px, py, dock_h)), width=0.22, depth=0.22, mat_idx=1)
    # Stacked flour sacks on dock
    for i in range(6):
        add_box(bm, dock_x - 0.8 + (i % 3) * 0.7, dock_y + (i // 3) * 0.7, dock_h + 0.35, 0.65, 0.52, 0.65, mat_idx=4)
    # Barrels on dock
    add_barrel(bm, dock_x + 1.2, dock_y - 1.2, dock_h + 0.55, radius=0.42, height=1.05, mat_wood=5, mat_iron=6)
    add_barrel(bm, dock_x + 1.2, dock_y + 0.2, dock_h + 0.55, radius=0.42, height=1.05, mat_wood=5, mat_iron=6)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Watermill")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("Watermill", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "watermill")

# ==============================================================================
# 6. UPGRADED WEAVER'S WORKSHOP (weaver_workshop/front.jpg)
# ==============================================================================

def build_windmill(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_weathered"], mats["timber_plank"],
        mats["roof_shingle"], mats["plaster_white"], mats["stone_limestone"]
    ]

    # Central oak post (Kozioł) and cross trestle with pad footings
    add_box(bm, 0, 0, 0.3, 7.0, 7.0, 0.6, mat_idx=5) # stone base pads
    add_box(bm, 0, 0, 2.0, 0.6, 0.6, 4.0, mat_idx=0) # central oak post
    for cx, cy in [(-2.0, -2.0), (2.0, -2.0), (-2.0, 2.0), (2.0, 2.0)]:
        add_box(bm, cx * 0.5, cy * 0.5, 1.8, 0.3, 0.3, 2.8, mat_idx=0) # diagonal struts

    # Rotating timber body: 6.5m wide x 6.5m deep x 9.0m high (base at z=3.8)
    add_box(bm, 0, 0, 8.3, 6.5, 6.5, 9.0, mat_idx=1)
    # Gabled shingle roof
    add_sloped_roof(bm, 0, 0, 12.8, 6.5, 6.5, 3.8, overhang=0.4, mat_idx=3)

    # 4-BLADE CANVAS SAILS (-Y front facade): 16m total tip-to-tip span
    hub_z = 11.5
    hub_y = -3.4
    add_box(bm, 0, hub_y, hub_z, 0.4, 0.6, 0.4, mat_idx=0) # axle hub
    # 4 sail arms and lattice frames
    sail_len = 7.5
    # Vertical arm
    add_box(bm, 0, hub_y - 0.1, hub_z, 0.2, 0.1, sail_len * 2, mat_idx=0)
    add_box(bm, 0.5, hub_y - 0.15, hub_z + sail_len * 0.5, 0.8, 0.05, sail_len * 0.85, mat_idx=4)
    add_box(bm, -0.5, hub_y - 0.15, hub_z - sail_len * 0.5, 0.8, 0.05, sail_len * 0.85, mat_idx=4)
    # Horizontal arm
    add_box(bm, 0, hub_y - 0.1, hub_z, sail_len * 2, 0.1, 0.2, mat_idx=0)
    add_box(bm, sail_len * 0.5, hub_y - 0.15, hub_z - 0.5, sail_len * 0.85, 0.05, 0.8, mat_idx=4)
    add_box(bm, -sail_len * 0.5, hub_y - 0.15, hub_z + 0.5, sail_len * 0.85, 0.05, 0.8, mat_idx=4)

    # Massive diagonal tail-pole (Dyszel) reaching to ground (+Y rear)
    add_box(bm, 0, 5.5, 3.0, 0.3, 6.5, 0.3, mat_idx=0)
    # Rear access ladder
    add_box(bm, 0, 3.8, 2.2, 1.2, 0.2, 4.4, mat_idx=2)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Windmill")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("Windmill", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "windmill")

# -------------------------------------------------------------
# 20. Stepped Limestone Quarry & Stonemasons' Yard
# -------------------------------------------------------------
def build_stone_quarry(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"], mats["timber_dark"], mats["timber_plank"],
        mats["iron_wrought"]
    ]

    # Stepped quarry pit excavation (3 terraced rock ledges)
    add_box(bm, 0, 0, -2.0, 20.0, 20.0, 4.0, mat_idx=0) # lower pit floor
    add_box(bm, -6.0, 0, 0.5, 6.0, 18.0, 2.0, mat_idx=0) # step 1
    add_box(bm, 0, 6.0, 1.5, 18.0, 6.0, 2.0, mat_idx=0) # step 2

    # Timber A-Frame Jib Crane Derrick (7m high)
    add_box(bm, 2.0, -2.0, 1.8, 0.3, 0.3, 3.6, mat_idx=1) # vertical mast
    add_box(bm, 3.5, -0.5, 3.2, 3.5, 0.25, 0.25, mat_idx=1) # boom arm
    add_box(bm, 0.8, -3.2, 0.6, 1.4, 1.4, 1.0, mat_idx=0) # stone counterweight box
    add_box(bm, 5.0, 1.0, 1.2, 1.0, 1.0, 0.8, mat_idx=0) # suspended stone block

    # Masons' outdoor timber work trestles
    add_box(bm, -3.0, -4.5, 0.5, 1.0, 2.4, 0.8, mat_idx=2)
    # Rows of dressed limestone ashlar blocks
    for bx in [-2.0, -0.5, 1.0]:
        for by in [-4.5, -3.0]:
            add_box(bm, bx, by, 0.4, 0.9, 0.9, 0.7, mat_idx=0)

    # Rock rubble talus mounds
    add_box(bm, 6.0, 5.0, 1.0, 3.0, 3.0, 1.4, mat_idx=0)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_StoneQuarry")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("StoneQuarry", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "stone_quarry")

# -------------------------------------------------------------
# 21. Logging Camp & Pit Sawmill (Trak Ciesielski)
# -------------------------------------------------------------
def build_logging_camp(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_weathered"], mats["timber_plank"],
        mats["roof_shingle"], mats["goods_cheese_bread"], mats["roof_thatch"]
    ]

    # Open-sided timber post-and-beam drying shelter: 6.0m x 8.0m
    for px in [-2.8, 2.8]:
        for py in [-3.8, 3.8]:
            add_box(bm, px, py, 1.8, 0.25, 0.25, 3.6, mat_idx=0)
    add_sloped_roof(bm, 0, 0, 3.6, 6.0, 8.0, 2.2, overhang=0.4, mat_idx=3)

    # ELEVATED TWO-MAN PIT-SAW TRESTLE (Trak)
    trestle_x = 5.5
    add_box(bm, trestle_x, 0, 1.0, 1.6, 5.0, 0.2, mat_idx=2) # top sawyer deck
    add_box(bm, trestle_x - 0.7, 0, 0.9, 0.2, 5.0, 1.8, mat_idx=0) # trestle legs
    add_box(bm, trestle_x + 0.7, 0, 0.9, 0.2, 5.0, 1.8, mat_idx=0)
    # Log being sawed into planks on the trestle
    add_cylinder(bm, trestle_x, 0, 2.2, radius=0.35, height=4.5, segs=8, mat_idx=0)
    # Yellow sawdust pile beneath trestle
    add_box(bm, trestle_x, 0, 0.2, 2.2, 4.0, 0.4, mat_idx=4)

    # 3 Stacks of peeled pine logs braced by vertical stakes
    for lx in [-5.5, -5.5]:
        add_box(bm, lx, -1.5, 0.8, 1.8, 5.0, 1.4, mat_idx=1)
        add_box(bm, lx, 3.0, 0.8, 1.8, 4.0, 1.4, mat_idx=1)

    # Chopping tree stumps with felling axes
    add_cylinder(bm, 2.0, -4.5, 0.4, radius=0.45, height=0.8, segs=8, mat_idx=0)
    add_cylinder(bm, -2.0, -4.5, 0.35, radius=0.4, height=0.7, segs=8, mat_idx=0)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_LoggingCamp")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("LoggingCamp", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "logging_camp")

# -------------------------------------------------------------
# 22. Riverside Harbor Wharves & Trade Basin
# -------------------------------------------------------------
def build_river_harbor(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_plank"], mats["roof_shingle"],
        mats["stone_limestone"], mats["iron_wrought"], mats["flour_sack_cloth"],
        mats["goods_fabrics"]
    ]

    # Oak boardwalk wharf on stilts along river edge: 22m long x 8m wide
    add_box(bm, 0, 0, 0.8, 22.0, 8.0, 0.4, mat_idx=1)
    for px in range(-9, 10, 3):
        for py in [-3.5, 3.5]:
            add_box(bm, px, py, -0.2, 0.35, 0.35, 2.0, mat_idx=0)

    # Moored 14m Clinker-Built River Cog ship (side facing wharf)
    cog_y = -7.0
    add_box(bm, 0, cog_y, 0.5, 14.0, 3.8, 2.2, mat_idx=0) # hull
    add_box(bm, 5.5, cog_y, 1.8, 3.0, 3.8, 1.4, mat_idx=1) # sterncastle
    add_box(bm, 0, cog_y, 5.0, 0.35, 0.35, 8.0, mat_idx=0) # mast
    add_box(bm, 0, cog_y, 7.5, 6.0, 0.15, 0.15, mat_idx=1) # yardarm

    # Cylindrical wooden treadwheel harbor crane
    add_cylinder(bm, -7.0, 1.5, 2.2, radius=1.6, height=3.5, segs=8, mat_idx=0)
    add_box(bm, -7.0, -1.0, 4.2, 0.35, 4.0, 0.35, mat_idx=1) # crane boom

    # Cargo piles on wharf (barrels, crates, grain sacks)
    for bx in [2.0, 3.5, 5.0]:
        add_cylinder(bm, bx, 2.0, 1.4, radius=0.45, height=1.0, segs=8, mat_idx=0)
    add_box(bm, 7.0, 1.5, 1.3, 1.6, 2.0, 1.0, mat_idx=5) # flour sacks

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_RiverHarbor")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("RiverHarbor", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "river_harbor")

# -------------------------------------------------------------
# 23. Kraków Gate & Barbican Drawbridge (Brama Krakowska)
# -------------------------------------------------------------
def build_krakow_gate(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["stone_limestone"], mats["copper_patina"],
        mats["timber_dark"], mats["iron_wrought"], mats["roof_tile_red"],
        mats["glass_dark"], mats["timber_plank"], mats["plaster_white"],
        mats["roof_shingle"], mats["gold_sign"]
    ]
    BR, LS, CU, TD, IR, RT, GL, TP, PL, SH, GD = range(11)
    X, Y, Z = Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), _LM_Z

    # Orientation (as placed by populateCityScene): the curtain wall meets the tower along
    # the model's Y axis, the Kraków road runs through it along X, and +X is outside the town.
    L, W, PW = 10.5, 10.0, 4.4            # depth along the road, width along the wall, passage
    ZS, ZT, TOP = 3.8, 7.0, 17.0           # passage springing, vault top, tower-body top
    hl, hw = L * 0.5, W * 0.5
    _lm_gate_passage(bm, L, W, PW, ZS, ZT, BR, LS, LS)

    # Half-raised iron portcullis behind the outer portal; oak leaves opened against the walls
    gx = hl - 0.7
    for k in range(9):
        y = -2.0 + k * 0.5
        add_timber_beam(bm, Vector((gx, y, 2.5)), Vector((gx, y, 6.6)), width=0.1, depth=0.1, mat_idx=IR)
    for z in (2.7, 3.5, 4.3):
        add_timber_beam(bm, Vector((gx, -PW * 0.5, z)), Vector((gx, PW * 0.5, z)), width=0.1, depth=0.1, mat_idx=IR)
    for s in (-1.0, 1.0):
        add_box(bm, -hl + 1.6, s * (PW * 0.5 - 0.08), 1.8, 2.0, 0.12, 3.6, mat_idx=TP)

    # Square Gothic brick body: string courses, blind niches, arrow loops, wall-walk door
    add_box(bm, 0, 0, (ZT + TOP) * 0.5, L, W, TOP - ZT, mat_idx=BR)
    for zb in (ZT, 12.0):
        add_box(bm, 0, 0, zb, L + 0.2, W + 0.2, 0.25, mat_idx=LS)
    for out, along, half in ((X, Y, hl), (-X, Y, hl), (-Y, X, hw), (Y, X, hw)):
        base = out * half
        for o in (-2.4, 2.4):
            _lm_blind(bm, base + along * o + Z * 7.6, along, out, 1.0, 3.2, PL)
        if out.x < 0.5:                   # +X carries the hoarding
            for o in (-2.6, 0.0, 2.6):
                _lm_lancet(bm, base + along * o + Z * 13.4, along, out, 0.28, 1.3, GL, LS, frame=0.1, sill=False)
    _lm_lancet(bm, Vector((0, hw, 8.0)), X, Y, 1.0, 1.9, TP, LS, frame=0.18, sill=False)

    # Gatekeeper's timber hoarding gallery over the highway approach (+X)
    hx0, hx1 = hl, hl + 1.5
    add_box(bm, (hx0 + hx1) * 0.5, 0, 12.7, hx1 - hx0, 7.4, 0.2, mat_idx=TP)
    add_box(bm, hx1 - 0.1, 0, 13.9, 0.2, 7.4, 2.2, mat_idx=TP)
    for s in (-1.0, 1.0):
        add_box(bm, (hx0 + hx1 - 0.2) * 0.5, s * 3.6, 13.9, hx1 - hx0 - 0.2, 0.2, 2.2, mat_idx=TP)
    for yy in (-3.0, 0.0, 3.0):
        add_timber_beam(bm, Vector((hx0, yy, 11.4)), Vector((hx1 - 0.2, yy, 12.6)), width=0.2, depth=0.2, mat_idx=TD)
    for yy in (-3.6, -1.2, 1.2, 3.6):
        add_timber_beam(bm, Vector((hx1, yy, 12.6)), Vector((hx1, yy, 15.05)), width=0.16, depth=0.16, mat_idx=TD)
    for yy in (-2.4, 0.0, 2.4):
        add_box(bm, hx1 + 0.01, yy, 13.9, 0.04, 0.3, 0.8, mat_idx=GL)
    # lean-to roof: one plane wound up/out (a closed slab would put as much area facing down)
    rv = [bm.verts.new(Vector(p)) for p in ((hx0, -3.95, 16.0), (hx1 + 0.35, -3.95, 14.8),
                                             (hx1 + 0.35, 3.95, 14.8), (hx0, 3.95, 16.0))]
    bm.faces.new(rv).material_index = SH
    add_timber_beam(bm, Vector((hx1 + 0.35, -3.95, 14.74)), Vector((hx1 + 0.35, 3.95, 14.74)), width=0.12, depth=0.12, mat_idx=TD)

    # Machicolated corbel table and crenellated parapet
    PO = 0.45
    for s in (-1.0, 1.0):
        for k in range(7):
            add_box(bm, s * (hl + PO * 0.5), -hw + 0.6 + k * (W - 1.2) / 6, TOP - 0.25, PO, 0.35, 0.5, mat_idx=LS)
            add_box(bm, -hl + 0.6 + k * (L - 1.2) / 6, s * (hw + PO * 0.5), TOP - 0.25, 0.35, PO, 0.5, mat_idx=LS)
    _lm_parapet_rect(bm, 0, 0, TOP, L + 2 * PO, W + 2 * PO, 1.1, 0.4, BR, merlon_h=0.9, merlon_w=0.7, pitch=1.45)

    # Octagonal brick belfry and copper-clad helm spire
    r8 = 3.6 / math.cos(math.pi / 8)
    _lm_ngon_prism(bm, 0, 0, TOP, 23.2, r8, 8, BR)
    for k in range(8):
        a = k * math.pi / 4
        out, along = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
        if k % 2 == 0:
            _lm_lancet(bm, out * 3.6 + Z * 19.4, along, out, 0.9, 2.2, GL, LS, frame=0.14, mullion=True)
        else:
            _lm_blind(bm, out * 3.6 + Z * 19.4, along, out, 0.6, 2.0, PL)
    _lm_ngon_prism(bm, 0, 0, 23.2, 23.5, r8 + 0.25, 8, LS)
    _lm_spire(bm, 0, 0, 23.5, r8 + 0.35, 10.0, 8, CU, base_cap=False)
    _lm_finial(bm, 0, 0, 33.5, IR, GD, h=1.6)

    # Timber drawbridge on chains over the (dry) moat, with a stone abutment
    bx0, bx1 = hl, hl + 7.5
    add_box(bm, (bx0 + bx1) * 0.5, 0, 0.35, bx1 - bx0, 4.0, 0.3, mat_idx=TP)
    add_box(bm, bx1 + 0.3, 0, 0.3, 0.6, 4.6, 0.6, mat_idx=LS)
    for s in (-1.0, 1.0):
        add_timber_beam(bm, Vector((bx0, s * 1.9, 0.6)), Vector((bx1, s * 1.9, 0.6)), width=0.22, depth=0.22, mat_idx=TD)
        for xx in (bx0 + 0.6, (bx0 + bx1) * 0.5, bx1 - 0.3):
            add_timber_beam(bm, Vector((xx, s * 1.9, 0.7)), Vector((xx, s * 1.9, 1.5)), width=0.12, depth=0.12, mat_idx=TD)
        add_timber_beam(bm, Vector((bx0 + 0.6, s * 1.9, 1.45)), Vector((bx1 - 0.3, s * 1.9, 1.45)), width=0.1, depth=0.1, mat_idx=TD)
        add_timber_beam(bm, Vector((bx1 - 0.3, s * 1.75, 0.7)), Vector((hl + 0.05, s * 2.75, 6.9)), width=0.07, depth=0.07, mat_idx=IR)
        add_box(bm, hl + 0.01, s * 2.75, 6.9, 0.04, 0.3, 0.3, mat_idx=GL)

    _lm_finish(bm, mat_list, "gate_krakow", "GateKrakow")

# -------------------------------------------------------------
# 24. Grodzka Gate (Brama Grodzka)
# -------------------------------------------------------------
def build_grodzka_gate(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["stone_limestone"], mats["roof_tile_red"],
        mats["timber_dark"], mats["iron_wrought"], mats["plaster_white"],
        mats["glass_dark"], mats["timber_plank"], mats["roof_shingle"], mats["gold_sign"]
    ]
    BR, LS, RT, TD, IR, PL, GL, TP, SH, GD = range(10)
    X, Y, Z = Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), _LM_Z

    # Same orientation as the Kraków Gate: wall along Y, road along X, +X towards Castle Hill.
    L, W, PW = 9.5, 9.0, 4.0
    ZS, ZT, TOP = 3.4, 6.6, 13.6
    hl, hw = L * 0.5, W * 0.5
    _lm_gate_passage(bm, L, W, PW, ZS, ZT, BR, LS, LS, frame=0.4)

    # Heavy oak portcullis with iron-shod spikes; open gate leaves
    gx = hl - 0.6
    for k in range(8):
        y = -1.75 + k * 0.5
        add_timber_beam(bm, Vector((gx, y, 2.2)), Vector((gx, y, 6.0)), width=0.14, depth=0.14, mat_idx=TD)
        add_timber_beam(bm, Vector((gx, y, 2.0)), Vector((gx, y, 2.2)), width=0.08, depth=0.08, mat_idx=IR)
    for z in (2.4, 3.2, 4.0):
        add_timber_beam(bm, Vector((gx + 0.1, -PW * 0.5, z)), Vector((gx + 0.1, PW * 0.5, z)), width=0.12, depth=0.12, mat_idx=TD)
    for s in (-1.0, 1.0):
        add_box(bm, -hl + 1.5, s * (PW * 0.5 - 0.08), 1.6, 1.8, 0.12, 3.2, mat_idx=TP)

    # Brick body: string courses, blind niches, small lancet windows, wall-walk door
    add_box(bm, 0, 0, (ZT + TOP) * 0.5, L, W, TOP - ZT, mat_idx=BR)
    for zb in (ZT, 10.1):
        add_box(bm, 0, 0, zb, L + 0.2, W + 0.2, 0.25, mat_idx=LS)
    for out, along, half in ((X, Y, hl), (-X, Y, hl), (-Y, X, hw), (Y, X, hw)):
        base = out * half
        if out.y < 0.5:
            for o in (-2.0, 2.0):
                _lm_blind(bm, base + along * o + Z * 6.95, along, out, 0.9, 2.4, PL)
        for o in (-2.6, 0.0, 2.6):
            _lm_lancet(bm, base + along * o + Z * 10.8, along, out, 0.55, 1.1, GL, LS, frame=0.12)
    _lm_lancet(bm, Vector((0, hw, 8.0)), X, Y, 1.0, 1.7, TP, LS, frame=0.18, sill=False)

    # Machicolated overhanging parapet with loops, then a hipped tile roof
    PO = 0.4
    for s in (-1.0, 1.0):
        for k in range(6):
            add_box(bm, s * (hl + PO * 0.5), -hw + 0.6 + k * (W - 1.2) / 5, TOP - 0.25, PO, 0.35, 0.5, mat_idx=LS)
            add_box(bm, -hl + 0.6 + k * (L - 1.2) / 5, s * (hw + PO * 0.5), TOP - 0.25, 0.35, PO, 0.5, mat_idx=LS)
    pw_, pd_ = L + 2 * PO, W + 2 * PO
    ZP = TOP + 1.4
    _lm_parapet_rect(bm, 0, 0, TOP, pw_, pd_, ZP - TOP, 0.4, BR)
    for s in (-1.0, 1.0):
        for o in (-3.0, -1.0, 1.0, 3.0):
            add_box(bm, s * (pw_ * 0.5 + 0.01), o, TOP + 0.75, 0.04, 0.25, 0.6, mat_idx=GL)
            add_box(bm, o, s * (pd_ * 0.5 + 0.01), TOP + 0.75, 0.25, 0.04, 0.6, mat_idx=GL)
    add_box(bm, 0, 0, ZP + 0.05, pw_ + 0.1, pd_ + 0.1, 0.1, mat_idx=LS)       # coping
    r0, r1 = _lm_hip_roof(bm, 0, 0, ZP + 0.1, pw_, pd_, 6.2, RT, overhang=0.35)
    for p in (r0, r1):
        _lm_finial(bm, p.x, p.y, p.z, IR, GD, h=1.2)

    # Octagonal timber toll booth by the outer portal, with counter, scales and toll chest
    bx, by = hl + 1.9, -3.6
    _lm_ngon_prism(bm, bx, by, 0.0, 0.3, 1.5, 8, LS)
    _lm_ngon_prism(bm, bx, by, 0.3, 2.9, 1.3, 8, TP)
    for k in range(8):
        a = math.pi / 8 + k * math.pi / 4
        add_timber_beam(bm, Vector((bx + 1.31 * math.cos(a), by + 1.31 * math.sin(a), 0.3)),
                        Vector((bx + 1.31 * math.cos(a), by + 1.31 * math.sin(a), 2.9)), width=0.14, depth=0.14, mat_idx=TD)
    fl = 1.3 * math.cos(math.pi / 8)
    _lm_lancet(bm, Vector((bx, by - fl, 1.2)), X, -Y, 0.8, 0.9, GL, TD, frame=0.1)
    add_box(bm, bx, by - fl - 0.25, 1.15, 1.1, 0.5, 0.08, mat_idx=TD)                  # counter
    add_timber_beam(bm, Vector((bx, by - fl - 0.3, 1.19)), Vector((bx, by - fl - 0.3, 1.75)), width=0.05, depth=0.05, mat_idx=IR)
    add_timber_beam(bm, Vector((bx - 0.35, by - fl - 0.3, 1.75)), Vector((bx + 0.35, by - fl - 0.3, 1.75)), width=0.04, depth=0.04, mat_idx=IR)
    for sx in (-0.35, 0.35):
        _lm_ngon_prism(bm, bx + sx, by - fl - 0.3, 1.45, 1.5, 0.12, 6, IR)
    _lm_lancet(bm, Vector((bx + fl, by, 0.3)), Y, X, 0.8, 1.6, TD, None)              # door
    add_box(bm, bx + 1.6, by - 1.3, 0.25, 0.6, 0.4, 0.5, mat_idx=IR)                  # toll chest
    _lm_ngon_prism(bm, bx, by, 2.9, 3.0, 1.45, 8, TD)
    _lm_spire(bm, bx, by, 3.0, 1.75, 1.9, 8, SH, base_cap=False)
    _lm_finial(bm, bx, by, 4.9, IR, GD, h=0.6)

    _lm_finish(bm, mat_list, "gate_grodzka", "GateGrodzka")

# -------------------------------------------------------------
# 25. Dominican Monastery & Cloister Garden (Klasztor Dominikanów)
# -------------------------------------------------------------
def build_monastery_cloister(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["plaster_white"], mats["roof_tile_red"],
        mats["stone_limestone"], mats["foliage_green"], mats["timber_dark"],
        mats["glass_dark"], mats["timber_plank"], mats["copper_patina"],
        mats["gold_sign"], mats["water_clean"], mats["iron_wrought"]
    ]
    BR, PL, RT, LS, FG, TD, GL, TP, CU, GD, WA, IR = range(12)
    X, Y, Z = Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), _LM_Z

    # 24 m square quadrangle around a 13 m garth. N/S ranges (dormitory, refectory) are two
    # storeys with crow-stepped gables; E/W ranges are one storey + attic, their roofs running
    # into the N/S roofs. A 2 m vaulted cloister walk with pointed arcades lines the garth.
    O, I, K = 12.0, 6.5, 8.5                    # outer half, garth half, walk back wall
    Z1, ZN, ZE = 3.6, 7.5, 5.0                  # walk ceiling, N/S eaves, E/W eaves
    for s in (-1.0, 1.0):
        add_box(bm, 0, s * (K + O) * 0.5, Z1 * 0.5, 2 * O, O - K, Z1, mat_idx=BR)
        add_box(bm, 0, s * (I + O) * 0.5, (Z1 + ZN) * 0.5, 2 * O, O - I, ZN - Z1, mat_idx=BR)
        add_box(bm, s * (K + O) * 0.5, 0, Z1 * 0.5, O - K, 2 * K, Z1, mat_idx=BR)
        add_box(bm, s * (I + O) * 0.5, 0, (Z1 + ZE) * 0.5, O - I, 2 * I, ZE - Z1, mat_idx=BR)
        add_box(bm, 0, s * (O - 0.425), 0.3, 2 * O + 0.3, 1.15, 0.6, mat_idx=LS)    # outer plinth
        add_box(bm, s * (O - 0.425), 0, 0.3, 1.15, 2 * O + 0.3 - 2.3, 0.6, mat_idx=LS)

    # Cloister arcades (the N/S arcades carry the corner piers)
    piers = [-I - 0.3 + k * (2 * I + 0.6) / 6 for k in range(7)]
    bays = [(a + b) * 0.5 for a, b in zip(piers, piers[1:])]
    for s in (-1.0, 1.0):
        _lm_arcade(bm, (0, s * I, 0), X, -s * Y, piers, 0.6, 0.6, 2.2, Z1, BR, mat_cap=LS)
        _lm_arcade(bm, (s * I, 0, 0), Y, -s * X, piers, 0.6, 0.6, 2.2, Z1, BR, mat_cap=LS, end_piers=False)
        for bx in bays:                                                       # upper-floor cells
            _lm_lancet(bm, Vector((bx, s * I, 4.6)), X, -s * Y, 0.6, 1.2, GL, LS, frame=0.1)
        _lm_lancet(bm, Vector((1.1, s * K, 0.0)), X, -s * Y, 1.2, 2.0, TP, LS, frame=0.18, sill=False)
        _lm_lancet(bm, Vector((s * K, -1.1, 0.0)), Y, -s * X, 1.2, 2.0, TP, LS, frame=0.18, sill=False)

    # Outer facades: buttressed south front with the gate, windows elsewhere
    for bx in (-10.5, -7.5, -4.5, -1.5, 1.5, 4.5, 7.5, 10.5):
        _lm_buttress(bm, (bx, -O), -Y, X, 0.6, [(3.0, 0.8), (2.8, 0.45)], BR)
    for s in (-1.0, 1.0):
        for wx in (-9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0):
            _lm_lancet(bm, Vector((wx, s * O, 4.4)), X, s * Y, 0.9, 1.7, GL, LS, frame=0.14)
            if wx != 0.0:
                _lm_lancet(bm, Vector((wx, s * O, 1.0)), X, s * Y, 0.6, 1.0, GL, LS, frame=0.12)
        for wy in (-4.5, -1.5, 1.5, 4.5):
            _lm_lancet(bm, Vector((s * O, wy, 1.0)), Y, s * X, 0.7, 1.4, GL, LS, frame=0.12)
        for wy in (-9.25, 9.25):
            _lm_lancet(bm, Vector((s * O, wy, 4.4)), Y, s * X, 0.9, 1.7, GL, LS, frame=0.14)
    _lm_blind(bm, Vector((0, -O, 0.0)), X, -Y, 2.4, 2.6, LS, proud=0.2)                 # gate portal
    _lm_lancet(bm, Vector((0, -O - 0.2, 0.0)), X, -Y, 1.5, 2.3, TP, LS, frame=0.22, sill=False)

    # Roofs: N/S saddles between crow-stepped gables; E/W saddles dying into them
    for s in (-1.0, 1.0):
        _lm_saddle_roof(bm, 0, s * (I + O) * 0.5, ZN, 2 * O - 1.0, O - I, 4.5, 'x', RT, overhang=0.35)
        for sx in (-1.0, 1.0):
            _lm_crow_gable(bm, (sx * (O - 0.5), s * (I + O) * 0.5), Y, sx * X, ZN, O - I, 3, 1.7, BR, PL, thick=0.5)
        _lm_saddle_roof(bm, s * (I + O) * 0.5, 0, ZE, 14.4, O - I, 3.5, 'y', RT, overhang=0.35)

    # Bell turret (sygnaturka) on the south range
    tz = ZN + 4.5
    _lm_ngon_prism(bm, 3.0, -(I + O) * 0.5, tz - 0.8, tz + 1.6, 0.55, 8, CU)
    _lm_spire(bm, 3.0, -(I + O) * 0.5, tz + 1.6, 0.68, 2.8, 8, CU, base_cap=False)
    _lm_finial(bm, 3.0, -(I + O) * 0.5, tz + 4.4, IR, GD, h=0.9, cross=True)

    # Garth: crossing gravel paths, eight raised herb beds, central fountain
    add_box(bm, 0, 0, 0.025, 2 * I, 1.2, 0.05, mat_idx=LS)
    add_box(bm, 0, 0, 0.03, 1.0, 2 * I, 0.06, mat_idx=LS)
    for bi, bx in enumerate((-4.4, -1.5, 1.5, 4.4)):
        for bj, by in enumerate((-3.4, 3.4)):
            add_box(bm, bx, by, 0.2, 2.2, 1.8, 0.4, mat_idx=TD)
            add_box(bm, bx, by, 0.45, 2.0, 1.6, 0.1, mat_idx=FG)
            for ci, cx in enumerate((-0.6, 0.0, 0.6)):
                for cj, cy in enumerate((-0.4, 0.4)):
                    hgt = 0.18 + 0.12 * ((bi * 3 + bj * 5 + ci * 2 + cj * 7) % 4)
                    add_box(bm, bx + cx, by + cy, 0.5 + hgt * 0.5, 0.42, 0.42, hgt, mat_idx=FG)
    _lm_ngon_prism(bm, 0, 0, 0.0, 0.7, 1.35, 8, LS)
    _lm_ngon_prism(bm, 0, 0, 0.55, 0.75, 1.12, 8, WA)
    _lm_ngon_prism(bm, 0, 0, 0.75, 1.9, 0.18, 8, LS)
    _lm_ngon_prism(bm, 0, 0, 1.5, 1.7, 0.55, 8, LS, r_top=0.62)

    _lm_finish(bm, mat_list, "monastery_cloister", "MonasteryCloister")

# -------------------------------------------------------------
# 26. Castle Archery & Training Yard (Strzelnica Zamkowa)
# -------------------------------------------------------------
def build_archery_yard(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_plank"], mats["roof_thatch"],
        mats["awning_red_white"], mats["iron_wrought"], mats["stone_limestone"]
    ]

    # Perimeter split-rail fence: 14m wide x 22m long
    for py in [-10.0, 10.0]:
        add_box(bm, 0, py, 0.6, 14.0, 0.15, 0.8, mat_idx=0)
    for px in [-6.8, 6.8]:
        add_box(bm, px, 0, 0.6, 0.15, 20.0, 0.8, mat_idx=0)

    # Barracks lean-to shelter shed at rear (-Y)
    add_box(bm, 0, -8.5, 1.8, 8.0, 3.5, 3.6, mat_idx=1)
    add_box(bm, 0, -8.5, 3.8, 8.4, 4.0, 0.2, mat_idx=2)

    # 3 Circular coiled straw archery targets on wooden tripods at 6m, 12m, 18m
    for ty in [-2.0, 3.0, 8.0]:
        tx = 2.5
        # Tripod legs
        add_box(bm, tx - 0.4, ty, 0.8, 0.1, 0.1, 1.6, mat_idx=0)
        add_box(bm, tx + 0.4, ty, 0.8, 0.1, 0.1, 1.6, mat_idx=0)
        add_box(bm, tx, ty + 0.4, 0.8, 0.1, 0.1, 1.6, mat_idx=0)
        # Straw target disc with red bullseye
        add_cylinder(bm, tx, ty - 0.1, 1.4, radius=0.6, height=0.15, segs=8, mat_idx=1)
        add_cylinder(bm, tx, ty - 0.15, 1.4, radius=0.25, height=0.08, segs=8, mat_idx=3)

    # Spinning wooden quintain dummy on pivot pole
    add_cylinder(bm, -2.5, 2.0, 1.1, radius=0.15, height=2.2, segs=6, mat_idx=0) # pole
    add_box(bm, -2.5, 2.0, 1.6, 1.8, 0.15, 0.15, mat_idx=1) # crossbar
    add_box(bm, -3.3, 2.0, 1.6, 0.1, 0.6, 0.6, mat_idx=1) # shield target
    add_cylinder(bm, -1.7, 2.0, 1.4, radius=0.2, height=0.5, segs=6, mat_idx=4) # counter sandbag

    # Vertical crossbow and polearm rack
    add_box(bm, -4.5, -6.5, 1.0, 0.2, 2.4, 1.8, mat_idx=0)
    add_box(bm, -4.5, -6.5, 1.2, 0.1, 2.0, 1.2, mat_idx=4) # weapons

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_ArcheryYard")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("ArcheryYard", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "archery_yard")

# -------------------------------------------------------------
# Main Execution: Compiling All 28 Historical 3D Assets
# -------------------------------------------------------------
def main():
    print("==================================================")
    print("  Compiling High-Quality 3D Assets via Blender CLI")
    print("==================================================")
    mats = get_materials()

    # Output GLB name -> builder. Order is the build order.
    builders = {
        # Civic & Religious
        "town_hall": build_town_hall,
        "szmatruz": build_szmatruz,
        "church_gothic": build_church_gothic,
        "monastery_cloister": build_monastery_cloister,
        # Fortifications & Military
        "castle_donjon": build_castle_donjon,
        "gate_krakow": build_krakow_gate,
        "gate_grodzka": build_grodzka_gate,
        "archery_yard": build_archery_yard,
        "curtain_wall": build_curtain_wall,
        "curtain_tower": build_defense_tower,
        # Industrial & Resource Production
        "watermill": build_watermill,
        "windmill": build_windmill,
        "stone_quarry": build_stone_quarry,
        "logging_camp": build_logging_camp,
        "river_harbor": build_river_harbor,
        "blacksmith_workshop": build_blacksmith_workshop,
        # Specialized Artisan Guild Workshops
        "house_baker": build_baker_house,
        "house_tanner": build_tanner_workshop,
        "house_brewer": build_brewer_malthouse,
        "house_potter": build_potter_workshop,
        "house_weaver": build_weaver_workshop,
        # Residential & Vernacular
        "house_patrician_brick": build_house_patrician_brick,
        "house_half_timber": build_house_half_timber,
        "house_timber_log": build_house_timber_log,
        "shed_timber": build_shed_timber,
        # Market & Clutter Infrastructure
        "market_stall_red_white": lambda m: build_market_stall(m, "awning_red_white", "red_white"),
        "market_stall_blue_white": lambda m: build_market_stall(m, "awning_blue_white", "blue_white"),
        "market_stall_yellow_white": lambda m: build_market_stall(m, "awning_yellow_white", "yellow_white"),
        "market_cart": build_market_cart,
        "town_well": build_town_well,
        "tree_oak": build_tree_oak,
    }

    # Optional model filter after "--": blender ... --python build_assets.py -- house_half_timber town_hall
    wanted = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    unknown = [w for w in wanted if w not in builders]
    if unknown:
        raise SystemExit(f"Unknown model(s): {', '.join(unknown)}. Known: {', '.join(builders)}")

    for name, build in builders.items():
        if not wanted or name in wanted:
            build(mats)

    print("==================================================")
    print(f"  {len(wanted) or len(builders)} 3D asset(s) compiled to GLB")
    print("==================================================")

if __name__ == "__main__":
    main()
