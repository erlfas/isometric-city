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

def add_half_timber_wall(bm, a, b, z0, z1, outward, mat_timber, mat_glass=None,
                         bay=1.5, timber=0.18, proud=0.05, rails=(1.0, 2.5), windows=True):
    """Timber frame (szachulec) over a plaster wall running from a to b, between z0 and z1.

    a, b: (x, y) corners on the plaster face; outward: unit vector out of the wall.
    Square timbers sit `proud` m in front of the plaster, so the infill reads as recessed
    and catches shadow along every member (KEY_FINDINGS section 13).
    Layout: sill and head plates, posts every ~`bay` m, long corner braces in the two
    end bays, and in the inner bays two rails (window sill / lintel) with a St. Andrew's
    cross below and a glazed window between them in alternate bays.
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

    def P(s, z):
        return a + t * s + off + Vector((0.0, 0.0, z))

    def beam(p, q, size=timber):
        add_timber_beam(bm, p, q, width=size, depth=size, mat_idx=mat_timber)

    beam(P(0.0, z0 + h), P(length, z0 + h))                  # sill plate
    beam(P(0.0, z1 - h), P(length, z1 - h))                  # head plate
    for i in range(n + 1):                                    # posts
        s = min(max(i * step, h), length - h)
        beam(P(s, z0 + timber), P(s, z1 - timber))

    for i in range(n):
        s0, s1 = i * step + h, (i + 1) * step - h
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
                   mat_glass=None, timber=0.18, proud=0.05):
    """Saddle roof (ridge along Y) with framed plaster gables instead of tiled gable ends.

    Slopes follow add_sloped_roof (eaves at z_base, extended by `overhang`). The gables sit
    on the wall planes y = cy +/- d/2 as plaster pentagons that close up under the eaves,
    framed with a sill, king post, collar beam and struts, plus bargeboards and a ridge.
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

    hw = w * 0.5
    z_edge = z_base + h * (overhang / w2)        # roof height straight above the wall line
    for sgn in (-1.0, 1.0):
        y = cy + sgn * d * 0.5
        pts = [(cx - hw, z_base), (cx + hw, z_base), (cx + hw, z_edge), (cx, ridge), (cx - hw, z_edge)]
        if sgn > 0:
            pts.reverse()                        # keep the face normal pointing out of the gable
        verts = [bm.verts.new(Vector((px, y, pz))) for px, pz in pts]
        bm.faces.new(verts).material_index = mat_plaster

        # bargeboards along the verge
        ye = cy + sgn * (d2 - 0.08)
        add_timber_beam(bm, Vector((cx - w2, ye, z_base)), Vector((cx, ye, ridge)), width=0.16, depth=0.18, mat_idx=mat_timber)
        add_timber_beam(bm, Vector((cx + w2, ye, z_base)), Vector((cx, ye, ridge)), width=0.16, depth=0.18, mat_idx=mat_timber)

        # gable frame, proud of the plaster
        yb = y + sgn * proud
        zc = z_base + h * 0.42                                   # collar height
        xc = (w2 * (1.0 - (zc - z_base) / h)) - 0.25             # collar reaches the roof line
        add_timber_beam(bm, Vector((cx - hw, yb, z_base + timber * 0.5)), Vector((cx + hw, yb, z_base + timber * 0.5)),
                        width=timber, depth=timber, mat_idx=mat_timber)
        add_timber_beam(bm, Vector((cx, yb, z_base + timber)), Vector((cx, yb, ridge - 0.3)),
                        width=timber, depth=timber, mat_idx=mat_timber)
        add_timber_beam(bm, Vector((cx - xc, yb, zc)), Vector((cx + xc, yb, zc)),
                        width=timber, depth=timber, mat_idx=mat_timber)
        for sx in (-1.0, 1.0):
            add_timber_beam(bm, Vector((cx + sx * hw * 0.8, yb, z_base + timber)), Vector((cx + sx * 0.35, yb, zc - 0.1)),
                            width=timber * 0.8, depth=timber * 0.8, mat_idx=mat_timber)
            if mat_glass is not None:                            # small loft windows
                add_box(bm, cx + sx * 1.0, y + sgn * 0.02, zc + (ridge - zc) * 0.3, 0.55, 0.04, 0.7, mat_idx=mat_glass)


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

# -------------------------------------------------------------
# 1. Old Town Hall (Ratusz Miejski)
# -------------------------------------------------------------
def build_town_hall(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["plaster_white"], mats["roof_tile_red"],
        mats["copper_patina"], mats["stone_limestone"], mats["timber_dark"]
    ]

    add_box(bm, 0, 0, 5.0, 18.0, 12.0, 10.0, mat_idx=0)
    for x in [-6.0, -3.0, 3.0, 6.0]:
        add_box(bm, x, -6.05, 5.5, 1.4, 0.15, 6.0, mat_idx=1)
    add_sloped_roof(bm, 0, 0, 10.0, 18.0, 12.0, 6.5, overhang=0.4, mat_idx=2)

    for x in [-9.0, 9.0]:
        for s in range(5):
            sw = 12.0 - s * 2.2
            add_box(bm, x, 0, 10.0 + s * 1.5, 0.6, sw, 1.5, mat_idx=0)
            add_box(bm, x, -sw * 0.5 + 0.3, 11.0 + s * 1.5, 0.7, 0.4, 0.8, mat_idx=1)
            add_box(bm, x, sw * 0.5 - 0.3, 11.0 + s * 1.5, 0.7, 0.4, 0.8, mat_idx=1)

    add_box(bm, 0, 0, 16.0, 5.5, 5.5, 12.0, mat_idx=0)
    for y in [-2.78, 2.78]:
        add_box(bm, 0, y, 18.0, 2.2, 0.1, 7.0, mat_idx=1)
    add_box(bm, 0, -2.85, 20.0, 2.4, 0.1, 2.4, mat_idx=1)

    add_box(bm, 0, 0, 23.5, 5.0, 5.0, 3.0, mat_idx=4)
    add_box(bm, 0, 0, 27.5, 4.2, 4.2, 5.0, mat_idx=3)
    add_box(bm, 0, 0, 31.0, 2.0, 2.0, 2.5, mat_idx=3)

    for cx in [-8.5, 8.5]:
        for cy in [-5.5, 5.5]:
            add_box(bm, cx, cy, 11.5, 1.8, 1.8, 3.5, mat_idx=0)
            add_box(bm, cx, cy, 14.5, 2.0, 2.0, 2.8, mat_idx=3)

    for st in range(8):
        add_box(bm, 9.5 + st * 0.55, -4.5, 0.3 + st * 0.45, 0.6, 2.2, 0.6 + st * 0.9, mat_idx=4)
    add_box(bm, 11.5, -3.3, 3.5, 4.5, 0.3, 1.2, mat_idx=4)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_TownHall")
    bm.to_mesh(mesh)
    bm.free()

    for m in mat_list:
        mesh.materials.append(m)
    obj = bpy.data.objects.new("TownHall", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "town_hall")

# -------------------------------------------------------------
# 2. Szmatruz (Cloth & Bread Hall)
# -------------------------------------------------------------
def build_szmatruz(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["stone_limestone"], mats["roof_tile_red"],
        mats["timber_dark"], mats["awning_red_white"], mats["awning_blue_white"]
    ]

    for x in range(-10, 11, 2):
        for y in [-4.0, 4.0]:
            add_box(bm, x, y, 2.5, 0.9, 0.9, 5.0, mat_idx=0)
            add_box(bm, x, y, 5.2, 1.2, 1.2, 0.4, mat_idx=1)

    add_sloped_roof(bm, 0, 0, 5.4, 24.0, 10.0, 4.5, overhang=0.5, mat_idx=2)

    for x in range(-8, 9, 4):
        add_box(bm, x, -3.2, 1.0, 2.8, 1.4, 1.8, mat_idx=3)
        add_box(bm, x, 3.2, 1.0, 2.8, 1.4, 1.8, mat_idx=3)
        m_awn = 4 if (x % 8 == 0) else 5
        add_box(bm, x, -3.2, 2.6, 3.0, 1.6, 0.2, mat_idx=m_awn)
        add_box(bm, x, 3.2, 2.6, 3.0, 1.6, 0.2, mat_idx=m_awn)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Szmatruz")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("Szmatruz", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "szmatruz")

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
        mats["stone_limestone"], mats["brick_gothic"], mats["foliage_green"]
    ]

    # Limestone plinth
    add_box(bm, 0, 0, 0.4, 8.4, 11.4, 0.8, mat_idx=3)

    # Interlocking dark pine log body
    add_box(bm, 0, 0, 3.2, 8.0, 11.0, 4.8, mat_idx=0)
    for cx in [-4.15, 4.15]:
        for cy in [-5.65, 5.65]:
            add_box(bm, cx, cy, 3.2, 0.45, 0.45, 4.8, mat_idx=1)

    # Wooden framed door and windows with shutters
    add_box(bm, 0, -5.55, 1.6, 1.2, 0.15, 2.2, mat_idx=1)
    add_box(bm, -2.4, -5.55, 2.2, 1.0, 0.15, 1.2, mat_idx=1)
    add_box(bm, 2.4, -5.55, 2.2, 1.0, 0.15, 1.2, mat_idx=1)

    # Thick thatched roof with mossy eaves and ridge cross-timbers (kozły)
    add_sloped_roof(bm, 0, 0, 5.6, 8.0, 11.0, 5.2, overhang=0.6, mat_idx=2)
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
        add_half_timber_wall(bm, a, b, z0, z1, Vector(out), mat_timber=1, mat_glass=6)

    # Carved wooden corbels under jetty
    for cx in [-4.0, -2.0, 0.0, 2.0, 4.0]:
        add_box(bm, cx, -6.2, 4.3, 0.35, 0.5, 0.7, mat_idx=1)

    # Clay tiled medieval gable roof (framed plaster gables) with attic dormer
    add_gable_roof(bm, 0, 0, z1, W, D, 5.5, overhang=0.4, mat_roof=2, mat_plaster=0, mat_timber=1, mat_glass=6)
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
        mats["stone_limestone"], mats["iron_wrought"]
    ]

    # Ground + 1st floors in Polish Gothic Brick: 9m wide x 14m deep x 8m high
    add_box(bm, 0, 0, 4.0, 9.0, 14.0, 8.0, mat_idx=0)

    # White plaster gothic lancet niches (blendówki)
    for x in [-2.5, 0, 2.5]:
        add_box(bm, x, -7.05, 5.0, 1.4, 0.12, 4.5, mat_idx=1)
        add_box(bm, x, -7.05, 2.0, 1.2, 0.12, 2.2, mat_idx=1)

    # Arched limestone portal & cellar street trapdoor
    add_box(bm, 0, -7.1, 1.5, 1.8, 0.2, 2.8, mat_idx=3)
    add_box(bm, 2.8, -7.6, 0.2, 1.6, 1.2, 0.3, mat_idx=4) # cellar iron hatch

    # High pitched clay tile roof
    add_sloped_roof(bm, 0, 0, 8.0, 9.0, 14.0, 6.0, overhang=0.2, mat_idx=2)

    # Crow-stepped gable on front (Szczyt schodkowy ze sterczynami)
    steps = 5
    for s in range(steps):
        sw = 9.0 - s * 1.6
        sz = 8.0 + s * 1.3
        add_box(bm, 0, -7.05, sz + 0.65, sw, 0.5, 1.3, mat_idx=0)
        add_box(bm, -sw * 0.5 + 0.25, -7.05, sz + 1.6, 0.4, 0.4, 0.8, mat_idx=1)
        add_box(bm, sw * 0.5 - 0.25, -7.05, sz + 1.6, 0.4, 0.4, 0.8, mat_idx=1)

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
        mats["stone_limestone"], mats["copper_patina"]
    ]

    add_box(bm, 0, 0, 7.0, 16.0, 30.0, 14.0, mat_idx=0)

    for cy in [-11.0, -5.5, 0.0, 5.5, 11.0]:
        for cx, sx in [(-8.4, -1), (8.4, 1)]:
            add_box(bm, cx + sx * 0.45, cy, 4.5, 1.1, 1.4, 9.0, mat_idx=0)
            add_box(bm, cx + sx * 0.45, cy, 9.2, 1.1, 1.4, 0.4, mat_idx=3)
            add_box(bm, cx + sx * 0.25, cy, 11.5, 0.7, 1.2, 4.2, mat_idx=0)
            add_box(bm, cx + sx * 0.25, cy, 13.8, 0.7, 1.2, 0.4, mat_idx=3)

    for cy in [-8.25, -2.75, 2.75, 8.25]:
        for cx in [-8.05, 8.05]:
            add_box(bm, cx, cy, 8.5, 0.12, 1.8, 7.0, mat_idx=1)

    add_sloped_roof(bm, 0, 0, 14.0, 16.0, 30.0, 11.0, overhang=0.4, mat_idx=2)

    for cy in [15.1, -15.1]:
        for s in range(6):
            sw = 16.0 - s * 2.4
            sz = 14.0 + s * 1.8
            add_box(bm, 0, cy, sz + 0.9, sw, 0.4, 1.8, mat_idx=0)
            add_box(bm, -sw * 0.5 + 0.3, cy, sz + 2.0, 0.4, 0.4, 0.8, mat_idx=1)
            add_box(bm, sw * 0.5 - 0.3, cy, sz + 2.0, 0.4, 0.4, 0.8, mat_idx=1)

    add_box(bm, 0, -17.5, 13.0, 8.0, 8.0, 26.0, mat_idx=0)
    add_box(bm, 0, -17.5, 26.8, 9.2, 9.2, 1.6, mat_idx=3)
    add_box(bm, 0, -17.5, 30.5, 7.0, 7.0, 6.0, mat_idx=0)
    add_box(bm, 0, -21.05, 30.5, 2.2, 0.12, 4.0, mat_idx=1)

    add_box(bm, 0, -17.5, 36.5, 6.0, 6.0, 6.0, mat_idx=4)
    add_box(bm, 0, -17.5, 42.0, 3.2, 3.2, 6.0, mat_idx=4)
    add_box(bm, 0, -17.5, 46.0, 1.2, 1.2, 3.0, mat_idx=4)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_ChurchGothic")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("ChurchGothic", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "church_gothic")

def build_castle_donjon(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"], mats["brick_gothic"], mats["roof_tile_red"],
        mats["timber_dark"]
    ]

    segs = 16
    radius = 7.0
    height = 22.0
    for i in range(segs):
        a1 = (i / segs) * math.pi * 2
        a2 = ((i + 1) / segs) * math.pi * 2
        x1, y1 = math.cos(a1) * radius, math.sin(a1) * radius
        x2, y2 = math.cos(a2) * radius, math.sin(a2) * radius
        mx, my = (x1 + x2) * 0.5, (y1 + y2) * 0.5
        seg_len = math.hypot(x2 - x1, y2 - y1)
        add_box(bm, mx, my, height * 0.5, 2.8, seg_len, height, mat_idx=0)

    r_top = 7.8
    for i in range(segs):
        a1 = (i / segs) * math.pi * 2
        a2 = ((i + 1) / segs) * math.pi * 2
        x1, y1 = math.cos(a1) * r_top, math.sin(a1) * r_top
        x2, y2 = math.cos(a2) * r_top, math.sin(a2) * r_top
        mx, my = (x1 + x2) * 0.5, (y1 + y2) * 0.5
        seg_len = math.hypot(x2 - x1, y2 - y1)
        add_box(bm, mx, my, 22.8, 1.2, seg_len, 1.6, mat_idx=0)
        if i % 2 == 0:
            add_box(bm, mx, my, 24.4, 0.8, seg_len, 1.6, mat_idx=1)

    add_box(bm, 0, 0, 25.5, 14.5, 14.5, 2.5, mat_idx=2)
    add_box(bm, 0, 0, 27.5, 9.5, 9.5, 2.5, mat_idx=2)
    add_box(bm, 0, 0, 29.5, 4.5, 4.5, 2.5, mat_idx=2)
    add_box(bm, 0, 0, 31.0, 1.5, 1.5, 1.5, mat_idx=3)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_CastleDonjon")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("CastleDonjon", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "castle_donjon")

# =============================================================
# NEW DIFFERENTIATED ARTISAN GUILD WORKSHOPS
# =============================================================

# -------------------------------------------------------------
# 12. Baker's House & Masonry Bread Oven (Piekarnia)
# -------------------------------------------------------------
def build_baker_house(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_cream"],      # 0
        mats["timber_dark"],        # 1
        mats["roof_tile_red"],      # 2
        mats["brick_gothic"],       # 3
        mats["stone_limestone"],    # 4
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

    # Ground floor shop plinth
    add_box(bm, 0, 0, 0.9, W, D, 1.8, mat_idx=4)
    for cx in [-w2 + 0.2, w2 - 0.2]:
        for cy in [-d2 + 0.2, d2 - 0.2]:
            add_box(bm, cx, cy, 0.9, 0.55, 0.55, 1.84, mat_idx=4)

    add_box(bm, 0, 0, 2.8, W - 0.1, D - 0.1, 2.0, mat_idx=0)
    add_timber_beam(bm, Vector((-w2, -d2, 1.8)), Vector((w2, -d2, 1.8)), width=0.22, depth=0.22, mat_idx=1)
    add_timber_beam(bm, Vector((-w2, d2, 1.8)), Vector((w2, d2, 1.8)), width=0.22, depth=0.22, mat_idx=1)
    add_timber_beam(bm, Vector((-w2, -d2, 1.8)), Vector((-w2, d2, 1.8)), width=0.22, depth=0.22, mat_idx=1)
    add_timber_beam(bm, Vector((w2, -d2, 1.8)), Vector((w2, d2, 1.8)), width=0.22, depth=0.22, mat_idx=1)

    # Bakery Street Front Entrance Door (-Y)
    add_box(bm, -1.8, -d2 - 0.05, 1.6, 1.4, 0.16, 2.4, mat_idx=1)
    add_box(bm, -1.8, -d2 - 0.02, 1.55, 1.1, 0.08, 2.2, mat_idx=5)
    add_box(bm, -1.3, -d2 - 0.08, 1.5, 0.08, 0.10, 0.14, mat_idx=9)

    # Open Bakery Shop Window & Bread Display Sill (-Y)
    add_box(bm, 1.5, -d2 - 0.05, 2.2, 2.2, 0.16, 1.6, mat_idx=1)
    add_box(bm, 1.5, -d2 + 0.05, 2.2, 1.9, 0.08, 1.3, mat_idx=13)
    add_box(bm, 1.5, -d2 - 0.35, 1.45, 2.4, 0.65, 0.12, mat_idx=5)
    add_timber_beam(bm, Vector((0.6, -d2, 0.8)), Vector((0.6, -d2 - 0.32, 1.4)), width=0.10, depth=0.10, mat_idx=1)
    add_timber_beam(bm, Vector((2.4, -d2, 0.8)), Vector((2.4, -d2 - 0.32, 1.4)), width=0.10, depth=0.10, mat_idx=1)
    for bx in [0.7, 1.2, 1.7, 2.2]:
        add_box(bm, bx, -d2 - 0.32, 1.58, 0.35, 0.24, 0.14, mat_idx=14)

    # Jettied 2nd Floor
    W_j, D_j = W + 0.50, D + 0.60
    w2_j, d2_j = W_j * 0.5, D_j * 0.5
    z_j, h_j = 3.8, 3.6
    for cx in [-2.8, -1.4, 0.0, 1.4, 2.8]:
        add_box(bm, cx, -d2 - 0.18, z_j - 0.32, 0.24, 0.45, 0.65, mat_idx=1)
    add_box(bm, 0, 0, z_j + h_j * 0.5, W_j - 0.15, D_j - 0.15, h_j, mat_idx=0)
    add_timber_beam(bm, Vector((-w2_j, -d2_j, z_j)), Vector((w2_j, -d2_j, z_j)), width=0.20, depth=0.20, mat_idx=1)
    add_timber_beam(bm, Vector((-w2_j, d2_j, z_j)), Vector((w2_j, d2_j, z_j)), width=0.20, depth=0.20, mat_idx=1)
    add_timber_beam(bm, Vector((-w2_j, -d2_j, z_j + h_j)), Vector((w2_j, -d2_j, z_j + h_j)), width=0.20, depth=0.20, mat_idx=1)
    add_timber_beam(bm, Vector((-w2_j, d2_j, z_j + h_j)), Vector((w2_j, d2_j, z_j + h_j)), width=0.20, depth=0.20, mat_idx=1)
    for px in [-w2_j, w2_j]:
        for py in [-d2_j, d2_j]:
            add_timber_beam(bm, Vector((px, py, z_j)), Vector((px, py, z_j + h_j)), width=0.22, depth=0.22, mat_idx=1)

    # Center vertical stud & diagonal braces
    add_timber_beam(bm, Vector((0, -d2_j, z_j)), Vector((0, -d2_j, z_j + h_j)), width=0.18, depth=0.18, mat_idx=1)
    add_timber_beam(bm, Vector((-w2_j, -d2_j, z_j)), Vector((0, -d2_j, z_j + h_j * 0.7)), width=0.16, depth=0.16, mat_idx=1)
    add_timber_beam(bm, Vector((w2_j, -d2_j, z_j)), Vector((0, -d2_j, z_j + h_j * 0.7)), width=0.16, depth=0.16, mat_idx=1)
    add_box(bm, 0, -d2_j - 0.05, z_j + h_j * 0.55, 1.4, 0.15, 1.4, mat_idx=1)
    add_box(bm, 0, -d2_j + 0.02, z_j + h_j * 0.55, 1.1, 0.08, 1.1, mat_idx=13)

    for fy in [-3.2, 0.0, 3.2]:
        add_timber_beam(bm, Vector((w2_j, fy, z_j)), Vector((w2_j, fy, z_j + h_j)), width=0.18, depth=0.18, mat_idx=1)
    add_timber_beam(bm, Vector((w2_j, -d2_j, z_j)), Vector((w2_j, -1.6, z_j + h_j)), width=0.14, depth=0.14, mat_idx=1)
    add_timber_beam(bm, Vector((w2_j, d2_j, z_j)), Vector((w2_j, 1.6, z_j + h_j)), width=0.14, depth=0.14, mat_idx=1)
    add_box(bm, w2_j + 0.05, -1.6, z_j + 1.8, 0.16, 1.2, 1.3, mat_idx=1)
    add_box(bm, w2_j - 0.02, -1.6, z_j + 1.8, 0.08, 0.9, 1.0, mat_idx=13)
    add_box(bm, w2_j + 0.05, 1.6, z_j + 1.8, 0.16, 1.2, 1.3, mat_idx=1)
    add_box(bm, w2_j - 0.02, 1.6, z_j + 1.8, 0.08, 0.9, 1.0, mat_idx=13)

    # Attic flour chute
    add_box(bm, w2_j + 0.05, 0.0, z_j + 1.8, 0.16, 1.2, 2.0, mat_idx=1)
    add_box(bm, w2_j - 0.02, 0.0, z_j + 1.8, 0.08, 0.9, 1.7, mat_idx=5)
    add_flour_chute(bm, w2_j, 0.0, z_j + 1.4, length=2.4, width=0.6, depth=0.22, angle_deg=38, mat_wood=5)

    # Roof
    add_pantile_roof(bm, 0, 0, z_j + h_j, W_j, D_j, 4.8, overhang=0.45, courses=9, mat_tile=2, mat_trim=1, mat_plaster=0)

    # Gilded pretzel sign
    bracket_x, bracket_y, bracket_z = -w2_j - 0.05, -d2_j - 0.15, z_j + h_j * 0.75
    add_box(bm, bracket_x, bracket_y, bracket_z, 0.12, 0.20, 0.70, mat_idx=9)
    add_timber_beam(bm, Vector((bracket_x, bracket_y, bracket_z)), Vector((bracket_x - 1.2, bracket_y - 0.3, bracket_z)), width=0.06, depth=0.06, mat_idx=9)
    add_timber_beam(bm, Vector((bracket_x, bracket_y, bracket_z - 0.5)), Vector((bracket_x - 0.9, bracket_y - 0.22, bracket_z)), width=0.05, depth=0.05, mat_idx=9)
    add_curved_pretzel(bm, bracket_x - 1.0, bracket_y - 0.25, bracket_z - 0.45, size=0.85, mat_gold=8)

    # Outdoor bake oven complex
    oven_x, oven_y, oven_base_w, oven_base_d, oven_base_h = 5.2, -1.2, 3.2, 3.6, 1.4
    add_box(bm, oven_x, oven_y, oven_base_h * 0.5, oven_base_w, oven_base_d, oven_base_h, mat_idx=4)
    add_box(bm, oven_x, oven_y - oven_base_d * 0.5 + 0.3, 0.45, 1.4, 0.7, 0.9, mat_idx=12)
    for wy in [-0.2, 0.0, 0.2]:
        add_box(bm, oven_x, oven_y - oven_base_d * 0.5 + 0.3 + wy, 0.35, 1.1, 0.18, 0.4, mat_idx=10)
    add_beehive_dome(bm, oven_x, oven_y, oven_base_h, radius=1.25, height=1.45, segs_u=14, segs_v=6, mat_idx=15)
    add_box(bm, oven_x, oven_y - 1.25 + 0.15, oven_base_h + 0.55, 1.0, 0.45, 0.95, mat_idx=3)
    add_box(bm, oven_x, oven_y - 1.25 - 0.05, oven_base_h + 0.45, 0.65, 0.12, 0.65, mat_idx=7)
    add_ashlar_chimney(bm, oven_x, oven_y + 1.2, oven_base_h, w=1.1, d=1.1, h=5.8, mat_stone=4, mat_soot=12)

    # Canopy
    canopy_y1, canopy_y2 = oven_y - oven_base_d * 0.5 - 0.2, oven_y + oven_base_d * 0.5 + 0.2
    canopy_x, post_h = oven_x + oven_base_w * 0.5 + 0.1, 3.4
    add_timber_beam(bm, Vector((canopy_x, canopy_y1, 0)), Vector((canopy_x, canopy_y1, post_h)), width=0.18, depth=0.18, mat_idx=1)
    add_timber_beam(bm, Vector((canopy_x, canopy_y2, 0)), Vector((canopy_x, canopy_y2, post_h)), width=0.18, depth=0.18, mat_idx=1)
    add_timber_beam(bm, Vector((canopy_x, canopy_y1, post_h)), Vector((canopy_x, canopy_y2, post_h)), width=0.18, depth=0.18, mat_idx=1)
    add_timber_beam(bm, Vector((canopy_x, canopy_y1, post_h - 0.8)), Vector((canopy_x, canopy_y1 + 0.7, post_h)), width=0.12, depth=0.12, mat_idx=1)
    add_timber_beam(bm, Vector((canopy_x, canopy_y2, post_h - 0.8)), Vector((canopy_x, canopy_y2 - 0.7, post_h)), width=0.12, depth=0.12, mat_idx=1)
    canopy_w = canopy_x - w2_j + 0.4
    canopy_mid_x = (canopy_x + w2_j) * 0.5
    canopy_len_y = canopy_y2 - canopy_y1 + 0.6
    canopy_mid_y = (canopy_y1 + canopy_y2) * 0.5
    add_box(bm, canopy_mid_x, canopy_mid_y, post_h + 0.25, canopy_w, canopy_len_y, 0.14, mat_idx=2)
    add_timber_beam(bm, Vector((oven_x - 1.2, oven_y - oven_base_d * 0.5 - 0.4, 0.1)), Vector((oven_x - 0.9, oven_y - oven_base_d * 0.5 + 0.2, 2.4)), width=0.08, depth=0.08, mat_idx=5)
    add_box(bm, oven_x - 0.85, oven_y - oven_base_d * 0.5 + 0.25, 2.45, 0.32, 0.04, 0.45, mat_idx=5)

    # Firewood & flour sacks
    add_prop_firewood_pile(bm, cx=oven_x + 1.25, cy=oven_y - oven_base_d * 0.5 + 0.7, cz=0, w=1.7, d=1.1, h=1.15, mat_bark=10, mat_end=11)
    add_prop_firewood_pile(bm, cx=oven_x, cy=oven_y + 3.2, cz=0, w=2.0, d=1.2, h=1.4, mat_bark=10, mat_end=11)

    sack_positions = [
        (-w2_j - 0.4, -d2 + 1.2, 0, 0.1),
        (-w2_j - 0.4, -d2 + 1.8, 0, -0.2),
        (-w2_j - 0.35, -d2 + 1.5, 0.55, 0.4),
        (w2_j + 0.5, -d2 + 1.5, 0, 0.2),
        (w2_j + 0.45, -d2 + 2.1, 0, -0.3)
    ]
    add_prop_flour_sacks(bm, sack_positions, mat_sack=6)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HouseBaker")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseBaker", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_baker")

def build_tanner_workshop(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"],       # 0
        mats["timber_weathered"],  # 1
        mats["roof_thatch"],       # 2
        mats["tannin_water"],      # 3
        mats["hide_leather"],      # 4
        mats["hide_raw"],          # 5
        mats["stone_limestone"],   # 6
        mats["timber_plank"]       # 7
    ]

    W, D = 7.2, 11.5
    w2, d2 = W * 0.5, D * 0.5
    # Weathered timber log building
    add_box(bm, 0, 0, 1.8, W, D, 3.6, mat_idx=1)
    for cx in [-w2, w2]:
        for cy in [-d2, d2]:
            add_timber_beam(bm, Vector((cx, cy, 0)), Vector((cx, cy, 3.6)), width=0.24, depth=0.24, mat_idx=0)
    add_pantile_roof(bm, 0, 0, 3.6, W, D, 4.2, overhang=0.55, courses=7, mat_tile=2, mat_trim=0, mat_plaster=1)

    # -------------------------------------------------------------
    # 6 CIRCULAR SUNKEN WOODEN TANNING VATS (Riverfront Flank)
    # -------------------------------------------------------------
    vat_r = 0.95
    vat_h = 0.65
    vat_x_start = w2 + 1.8
    for col in [0, 1]:
        for row in range(3):
            vx = vat_x_start + col * (vat_r * 2.2)
            vy = -3.2 + row * (vat_r * 2.3)
            # Wooden tub rim
            add_cylinder(bm, vx, vy, vat_h * 0.5, radius=vat_r, height=vat_h, segs=12, mat_idx=0)
            # Dark tannin liquor
            add_cylinder(bm, vx, vy, vat_h * 0.85, radius=vat_r * 0.88, height=0.08, segs=12, mat_idx=3)

    # -------------------------------------------------------------
    # 2 TALL HIDE-STRETCHING FRAMES WITH ANIMAL PELTS
    # -------------------------------------------------------------
    for idx, fy in enumerate([-2.8, 2.8]):
        fx = w2 + 4.2
        # Wooden outer frame
        add_timber_beam(bm, Vector((fx, fy - 1.2, 0)), Vector((fx, fy - 1.2, 3.4)), width=0.14, depth=0.14, mat_idx=0)
        add_timber_beam(bm, Vector((fx, fy + 1.2, 0)), Vector((fx, fy + 1.2, 3.4)), width=0.14, depth=0.14, mat_idx=0)
        add_timber_beam(bm, Vector((fx, fy - 1.2, 3.2)), Vector((fx, fy + 1.2, 3.2)), width=0.14, depth=0.14, mat_idx=0)
        add_timber_beam(bm, Vector((fx, fy - 1.2, 0.4)), Vector((fx, fy + 1.2, 0.4)), width=0.14, depth=0.14, mat_idx=0)
        # Pinned ox hide pelt
        add_box(bm, fx, fy, 1.8, 0.04, 1.8, 2.2, mat_idx=5 if idx % 2 == 0 else 4)

    # Fleshing beam (curved log on trestle)
    add_timber_beam(bm, Vector((0, -d2 - 1.8, 0.5)), Vector((0, -d2 - 3.2, 0.9)), width=0.35, depth=0.35, mat_idx=1)
    # Stack of cured leather hides
    add_box(bm, -2.2, -d2 - 2.2, 0.4, 1.2, 1.6, 0.8, mat_idx=4)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Tanner")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseTanner", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_tanner")

# ==============================================================================
# 5. UPGRADED RIVERSIDE WATERMILL (watermill/front.jpg)
# ==============================================================================

def build_brewer_malthouse(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"], # 0
        mats["timber_dark"],     # 1
        mats["roof_shingle"],    # 2
        mats["copper_patina"],   # 3
        mats["timber_plank"],    # 4
        mats["water_clean"],     # 5
        mats["iron_wrought"],    # 6
        mats["glass_dark"],      # 7
        mats["plaster_cream"]    # 8
    ]

    W, D = 8.6, 13.5
    w2, d2 = W * 0.5, D * 0.5

    # 1. Sturdy Limestone Ashlar Ground Floor (Z: 0 to 4.2m)
    add_box(bm, 0, 0, 2.1, W, D, 4.2, mat_idx=0)
    # Arched limestone window surrounds & portals
    for wy in [-4.2, -1.4, 1.4, 4.2]:
        add_box(bm, -w2 - 0.05, wy, 2.2, 0.15, 1.2, 1.8, mat_idx=0)
        add_box(bm, -w2 + 0.04, wy, 2.2, 0.08, 0.85, 1.4, mat_idx=7)
    # Front entrance door
    add_box(bm, 0, -d2 - 0.05, 1.8, 1.8, 0.15, 2.6, mat_idx=1)
    add_box(bm, 0, -d2 - 0.02, 1.75, 1.4, 0.08, 2.4, mat_idx=4)

    # 2. Upper Half-Timber Story with Malt Ventilation Louvers (Z: 4.2 to 7.8m)
    z_u = 4.2
    h_u = 3.6
    add_box(bm, 0, 0, z_u + h_u * 0.5, W + 0.3, D + 0.3, h_u, mat_idx=8) # plaster core
    # Timber posts
    for cx in [-w2 - 0.15, w2 + 0.15]:
        for cy in [-d2 - 0.15, d2 + 0.15]:
            add_timber_beam(bm, Vector((cx, cy, z_u)), Vector((cx, cy, z_u + h_u)), width=0.22, depth=0.22, mat_idx=1)
    # Prominent Malt Drying Louvers (horizontal wooden ventilation slats)
    for ly in [-3.5, 0.0, 3.5]:
        # Both walls have louvers!
        for wx_sign in [-1, 1]:
            wx = (w2 + 0.18) * wx_sign
            add_box(bm, wx, ly, z_u + 1.8, 0.14, 1.8, 2.2, mat_idx=1) # frame
            for s in range(5):
                add_box(bm, wx + 0.04 * wx_sign, ly, z_u + 0.9 + s * 0.45, 0.08, 1.6, 0.12, mat_idx=4) # slats

    # 3. Weathered Oak Shingle Roof
    add_pantile_roof(bm, 0, 0, z_u + h_u, W + 0.3, D + 0.3, 4.8, overhang=0.45, courses=9, mat_tile=2, mat_trim=1, mat_plaster=8)

    # 4. Hanging Copper Alembic Brew Kettle Sign
    sign_x = w2 + 0.2
    sign_y = -d2 - 0.2
    sign_z = z_u + 2.4
    add_timber_beam(bm, Vector((sign_x, sign_y, sign_z)), Vector((sign_x + 1.2, sign_y, sign_z)), width=0.08, depth=0.08, mat_idx=6)
    # Copper alembic kettle emblem
    add_cylinder(bm, sign_x + 0.8, sign_y, sign_z - 0.4, radius=0.35, height=0.55, segs=10, mat_idx=3)
    add_cylinder(bm, sign_x + 0.8, sign_y, sign_z - 0.05, radius=0.12, height=0.4, segs=8, mat_idx=3) # swan neck flue

    # 5. OUTDOOR CASK YARD (+X flank & front)
    # 4 Long Wooden Soak Wash Troughs
    for idx, ty in enumerate([-4.0, -1.2, 1.6, 4.4]):
        add_water_trough(bm, w2 + 2.0, ty, 0, w=1.1, d=2.4, h=0.7, mat_wood=4, mat_water=5)

    # Pyramid Stacks of Oak Beer Barrels
    add_barrel_pyramid(bm, w2 + 4.2, -2.4, 0, rot_y=False, mat_wood=4, mat_iron=6)
    add_barrel_pyramid(bm, w2 + 4.2, 2.4, 0, rot_y=False, mat_wood=4, mat_iron=6)

    # Outdoor Wooden Drinking Tables & Benches (Front forecourt)
    add_tavern_table_and_benches(bm, -2.2, -d2 - 2.8, 0, mat_wood=4)
    add_tavern_table_and_benches(bm, 2.2, -d2 - 2.8, 0, mat_wood=4)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Brewer")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseBrewer", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_brewer")

# ==============================================================================
# 3. UPGRADED POTTER'S WORKSHOP & KILN (potter_workshop/front.jpg)
# ==============================================================================

def build_blacksmith_workshop(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"], # 0
        mats["brick_gothic"],    # 1
        mats["timber_dark"],     # 2
        mats["roof_shingle"],    # 3
        mats["iron_steel"],      # 4
        mats["fire_orange"],     # 5
        mats["soot_black"],      # 6
        mats["water_clean"],     # 7
        mats["coal_black"],      # 8
        mats["timber_plank"],    # 9
        mats["glass_dark"]       # 10
    ]

    # Rear Workshop Building: 6.8m wide x 8.0m deep x 8.5m high (Z=0 to 11.0m)
    W_b, D_b = 6.8, 8.0
    w2_b, d2_b = W_b * 0.5, D_b * 0.5
    y_b_offset = 2.2 # pushed back to make room for open forge

    # Ground floor in sturdy brick & limestone quoin blocks
    add_box(bm, 0, y_b_offset, 1.8, W_b, D_b, 3.6, mat_idx=1)
    for cx in [-w2_b + 0.2, w2_b - 0.2]:
        for cy in [y_b_offset - d2_b + 0.2, y_b_offset + d2_b - 0.2]:
            add_box(bm, cx, cy, 1.8, 0.5, 0.5, 3.65, mat_idx=0)

    # Upper floor: Half-timbered quarters (Z: 3.6 to 6.8)
    add_box(bm, 0, y_b_offset, 5.2, W_b + 0.3, D_b + 0.3, 3.2, mat_idx=1) # brick infill
    # Timber framing posts and diagonals on upper floor
    for cx in [-w2_b - 0.1, w2_b + 0.1]:
        for cy in [y_b_offset - d2_b - 0.1, y_b_offset + d2_b + 0.1]:
            add_timber_beam(bm, Vector((cx, cy, 3.6)), Vector((cx, cy, 6.8)), width=0.2, depth=0.2, mat_idx=2)
    # Upper window
    add_box(bm, 0, y_b_offset - d2_b - 0.2, 5.2, 1.2, 0.15, 1.2, mat_idx=2)
    add_box(bm, 0, y_b_offset - d2_b - 0.25, 5.2, 0.9, 0.05, 0.9, mat_idx=10)

    # Shingle Roof on main building
    add_pantile_roof(bm, 0, y_b_offset, 6.8, W_b + 0.3, D_b + 0.3, 4.2, overhang=0.4, courses=8, mat_tile=3, mat_trim=2, mat_plaster=1)

    # -------------------------------------------------------------
    # FRONT OPEN FORGE CANOPY (Forecourt -Y)
    # -------------------------------------------------------------
    canopy_w = 7.6
    canopy_d = 5.6
    canopy_y_front = y_b_offset - d2_b - canopy_d
    canopy_h = 4.2

    # 4 Heavy Corner Timber Posts
    add_timber_beam(bm, Vector((-canopy_w * 0.5, canopy_y_front, 0)), Vector((-canopy_w * 0.5, canopy_y_front, canopy_h)), width=0.24, depth=0.24, mat_idx=2)
    add_timber_beam(bm, Vector((canopy_w * 0.5, canopy_y_front, 0)), Vector((canopy_w * 0.5, canopy_y_front, canopy_h)), width=0.24, depth=0.24, mat_idx=2)
    # Top plate beam & Carved Signboard
    add_timber_beam(bm, Vector((-canopy_w * 0.5, canopy_y_front, canopy_h)), Vector((canopy_w * 0.5, canopy_y_front, canopy_h)), width=0.24, depth=0.24, mat_idx=2)
    add_box(bm, 0, canopy_y_front - 0.14, canopy_h - 0.4, 3.2, 0.08, 0.55, mat_idx=9) # "BLACKSMITH" wooden signboard

    # Diagonal knee braces to posts
    add_timber_beam(bm, Vector((-canopy_w * 0.5, canopy_y_front, canopy_h - 0.9)), Vector((-canopy_w * 0.5 + 0.8, canopy_y_front, canopy_h)), width=0.14, depth=0.14, mat_idx=2)
    add_timber_beam(bm, Vector((canopy_w * 0.5, canopy_y_front, canopy_h - 0.9)), Vector((canopy_w * 0.5 - 0.8, canopy_y_front, canopy_h)), width=0.14, depth=0.14, mat_idx=2)

    # Sloped timber plank canopy roof (sloping from building wall to front posts)
    rafter_z_wall = 5.2
    add_timber_beam(bm, Vector((-canopy_w * 0.5, y_b_offset - d2_b, rafter_z_wall)), Vector((-canopy_w * 0.5, canopy_y_front, canopy_h)), width=0.18, depth=0.18, mat_idx=2)
    add_timber_beam(bm, Vector((canopy_w * 0.5, y_b_offset - d2_b, rafter_z_wall)), Vector((canopy_w * 0.5, canopy_y_front, canopy_h)), width=0.18, depth=0.18, mat_idx=2)
    canopy_mid_y = (canopy_y_front + (y_b_offset - d2_b)) * 0.5
    canopy_mid_z = (canopy_h + rafter_z_wall) * 0.5 + 0.1
    add_box(bm, 0, canopy_mid_y, canopy_mid_z, canopy_w + 0.4, canopy_d + 0.4, 0.14, mat_idx=9) # timber roof deck

    # -------------------------------------------------------------
    # FORGE HEARTH & TALL MASONRY CHIMNEY
    # -------------------------------------------------------------
    hearth_x = 1.2
    hearth_y = y_b_offset - d2_b + 0.4
    hearth_w, hearth_d, hearth_h = 2.4, 2.2, 1.4

    # Heavy Stone Ashlar Hearth Base
    add_box(bm, hearth_x, hearth_y, hearth_h * 0.5, hearth_w, hearth_d, hearth_h, mat_idx=0)
    # Arched furnace mouth with glowing orange fire
    add_box(bm, hearth_x, hearth_y - hearth_d * 0.5 - 0.1, hearth_h * 0.7, 1.2, 0.4, 0.8, mat_idx=1)
    add_box(bm, hearth_x, hearth_y - hearth_d * 0.5 - 0.05, hearth_h * 0.65, 0.9, 0.1, 0.5, mat_idx=5) # glowing fire

    # Massive Stone Chimney Stack rising through roof
    add_ashlar_chimney(bm, hearth_x, hearth_y, hearth_h, w=1.3, d=1.3, h=10.2, mat_stone=0, mat_soot=6)

    # -------------------------------------------------------------
    # OUTDOOR BLACKSMITH EQUIPMENT (Matching front.jpg & side.jpg)
    # -------------------------------------------------------------
    # 1. Oak Tree Stump & Cast Iron Anvil
    stump_x = -0.4
    stump_y = canopy_y_front + 2.0
    add_cylinder(bm, stump_x, stump_y, 0.4, radius=0.48, height=0.8, segs=10, mat_idx=2) # tree stump
    # Anvil (base, waist, horn, flat face)
    add_box(bm, stump_x, stump_y, 0.85, 0.45, 0.9, 0.12, mat_idx=4) # base
    add_box(bm, stump_x, stump_y, 1.05, 0.28, 0.5, 0.30, mat_idx=4) # waist
    add_box(bm, stump_x, stump_y, 1.25, 0.34, 1.1, 0.16, mat_idx=4) # table & horn

    # 2. Water Quench Trough (Long timber basin filled with water)
    trough_x = 3.2
    trough_y = canopy_y_front + 1.4
    add_water_trough(bm, trough_x, trough_y, 0, w=1.0, d=2.6, h=0.75, mat_wood=9, mat_water=7)

    # 3. A-Frame Weapon & Tool Display Rack
    rack_x = -2.8
    rack_y = canopy_y_front + 1.2
    add_timber_beam(bm, Vector((rack_x - 0.6, rack_y, 0)), Vector((rack_x - 0.6, rack_y, 1.8)), width=0.12, depth=0.12, mat_idx=2)
    add_timber_beam(bm, Vector((rack_x + 0.6, rack_y, 0)), Vector((rack_x + 0.6, rack_y, 1.8)), width=0.12, depth=0.12, mat_idx=2)
    add_timber_beam(bm, Vector((rack_x - 0.8, rack_y, 1.4)), Vector((rack_x + 0.8, rack_y, 1.4)), width=0.10, depth=0.10, mat_idx=2)
    # Displayed broadswords & poleaxes
    for sx in [-0.4, 0.0, 0.4]:
        add_box(bm, rack_x + sx, rack_y - 0.08, 1.1, 0.08, 0.04, 1.6, mat_idx=4)

    # 4. Sharpening Grindstone Wheel on Trestle
    grind_x = -2.6
    grind_y = canopy_y_front + 3.4
    add_box(bm, grind_x, grind_y, 0.45, 0.6, 1.1, 0.9, mat_idx=2) # wooden stand
    add_cylinder(bm, grind_x, grind_y, 0.85, radius=0.38, height=0.14, segs=12, mat_idx=0) # stone wheel

    # 5. Timber Coal Bunker with Black Charcoal (Side +X flank)
    bunker_x = w2_b + 1.4
    bunker_y = y_b_offset - 1.2
    add_box(bm, bunker_x, bunker_y, 0.6, 2.2, 2.4, 1.2, mat_idx=9) # timber bin
    add_box(bm, bunker_x, bunker_y, 0.95, 1.9, 2.1, 0.5, mat_idx=8) # mound of black coal!

    # 6. Stack of Iron Billets / Ingots
    add_box(bm, -1.8, canopy_y_front + 1.0, 0.25, 0.8, 1.2, 0.5, mat_idx=4)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Blacksmith")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("BlacksmithWorkshop", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "blacksmith_workshop")

# ==============================================================================
# 2. UPGRADED BREWER'S MALTHOUSE (brewer_malthouse/front.jpg)
# ==============================================================================

def build_potter_workshop(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_cream"],      # 0
        mats["timber_dark"],        # 1
        mats["roof_thatch"],        # 2
        mats["brick_oven"],         # 3
        mats["stone_limestone"],    # 4
        mats["pottery_terracotta"], # 5
        mats["fire_orange"],        # 6
        mats["soot_black"],         # 7
        mats["timber_plank"],       # 8
        mats["clay_mound"]          # 9
    ]

    # Thatched Wattle-and-Daub Cottage: 6.8m wide x 9.2m deep x 6.8m high
    W, D = 6.8, 9.2
    w2, d2 = W * 0.5, D * 0.5
    add_box(bm, 0, 0, 1.8, W, D, 3.6, mat_idx=0) # loam plaster walls
    # Rustic timber posts & corner crucks
    for cx in [-w2, w2]:
        for cy in [-d2, d2]:
            add_timber_beam(bm, Vector((cx, cy, 0)), Vector((cx, cy, 3.6)), width=0.22, depth=0.22, mat_idx=1)
    # Heavy thatched roof with cross timbers (kozły)
    add_pantile_roof(bm, 0, 0, 3.6, W, D, 4.4, overhang=0.55, courses=7, mat_tile=2, mat_trim=1, mat_plaster=0)

    # -------------------------------------------------------------
    # DOMED BRICK POTTERY KILN (Updraft Kiln in Yard)
    # -------------------------------------------------------------
    kiln_x = w2 + 2.6
    kiln_y = -0.5
    kiln_radius = 1.6
    kiln_stone_h = 1.4
    kiln_dome_h = 1.8

    # Circular stone plinth base
    add_cylinder(bm, kiln_x, kiln_y, kiln_stone_h * 0.5, radius=kiln_radius, height=kiln_stone_h, segs=14, mat_idx=4)
    # Arched stokehole fire mouth
    add_box(bm, kiln_x, kiln_y - kiln_radius - 0.1, kiln_stone_h * 0.55, 1.1, 0.4, 0.85, mat_idx=3)
    add_box(bm, kiln_x, kiln_y - kiln_radius - 0.05, kiln_stone_h * 0.5, 0.7, 0.1, 0.55, mat_idx=6) # glowing fire

    # Domed brick kiln body
    add_beehive_dome(bm, kiln_x, kiln_y, kiln_stone_h, radius=kiln_radius * 0.95, height=kiln_dome_h, segs_u=14, segs_v=6, mat_idx=3)
    # Chimney stack puffing smoke behind kiln
    add_ashlar_chimney(bm, kiln_x, kiln_y + 1.2, kiln_stone_h, w=1.0, d=1.0, h=6.4, mat_stone=4, mat_soot=7)

    # -------------------------------------------------------------
    # 3-TIER POTTERY DRYING SHELVES (Filled with Amphorae & Pots)
    # -------------------------------------------------------------
    shelf_x = w2 + 4.8
    shelf_y = -0.5
    shelf_w, shelf_d, shelf_h = 1.2, 4.5, 2.5
    # 4 Corner Posts
    for sx in [-shelf_w * 0.5, shelf_w * 0.5]:
        for sy in [-shelf_d * 0.5, shelf_d * 0.5]:
            add_timber_beam(bm, Vector((shelf_x + sx, shelf_y + sy, 0)), Vector((shelf_x + sx, shelf_y + sy, shelf_h)), width=0.12, depth=0.12, mat_idx=1)
    # 3 Shelves
    for tier in [0.7, 1.4, 2.1]:
        add_box(bm, shelf_x, shelf_y, tier, shelf_w, shelf_d, 0.08, mat_idx=8)
        # Pots & Amphorae on each shelf!
        for py in [-1.8, -0.9, 0.0, 0.9, 1.8]:
            add_cylinder(bm, shelf_x - 0.25, shelf_y + py, tier + 0.25, radius=0.18, height=0.45, segs=8, mat_idx=5)
            add_cylinder(bm, shelf_x + 0.25, shelf_y + py, tier + 0.25, radius=0.16, height=0.38, segs=8, mat_idx=5)

    # -------------------------------------------------------------
    # POTTER'S KICK-WHEEL & WORKBENCH
    # -------------------------------------------------------------
    bench_x = kiln_x - 1.2
    bench_y = -3.2
    add_box(bm, bench_x, bench_y, 0.5, 1.4, 2.2, 0.8, mat_idx=8) # workbench
    add_cylinder(bm, bench_x, bench_y + 0.5, 0.95, radius=0.32, height=0.08, segs=10, mat_idx=8) # kick wheel
    add_cylinder(bm, bench_x, bench_y + 0.5, 1.15, radius=0.20, height=0.32, segs=8, mat_idx=5) # clay pot in progress!
    # Clay mounds & firewood
    add_cylinder(bm, kiln_x + 1.2, -2.8, 0.35, radius=0.6, height=0.7, segs=8, mat_idx=9)
    add_cylinder(bm, kiln_x + 2.2, -2.5, 0.3, radius=0.5, height=0.6, segs=8, mat_idx=9)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Potter")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HousePotter", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_potter")

# ==============================================================================
# 4. UPGRADED TANNER'S RIVERSIDE WORKSHOP (tanner_workshop/front.jpg)
# ==============================================================================

def build_weaver_workshop(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_cream"],  # 0
        mats["timber_dark"],    # 1
        mats["roof_shingle"],   # 2
        mats["dye_indigo"],     # 3
        mats["dye_madder"],     # 4
        mats["cloth_indigo"],   # 5
        mats["cloth_madder"],   # 6
        mats["cloth_violet"],   # 7
        mats["cloth_gold"],     # 8
        mats["stone_limestone"],# 9
        mats["fire_orange"],    # 10
        mats["timber_plank"],   # 11
        mats["flour_sack_cloth"]      # 12
    ]

    W, D = 7.8, 11.5
    w2, d2 = W * 0.5, D * 0.5

    # 1. Ground Floor (Z: 0 to 4.0m)
    add_box(bm, 0, 0, 2.0, W, D, 4.0, mat_idx=0)
    # 2. Jettied Second Floor with PROMINENT ST. ANDREW'S CROSSES (Z: 4.0 to 7.6m)
    z_u, h_u = 4.0, 3.6
    add_box(bm, 0, 0, z_u + h_u * 0.5, W + 0.4, D + 0.4, h_u, mat_idx=0)
    # Side Wall (+X) St. Andrews X-Braces!
    for sy in [-2.8, 2.8]:
        add_timber_beam(bm, Vector((w2 + 0.22, sy - 1.4, z_u)), Vector((w2 + 0.22, sy + 1.4, z_u + h_u)), width=0.15, depth=0.15, mat_idx=1)
        add_timber_beam(bm, Vector((w2 + 0.22, sy - 1.4, z_u + h_u)), Vector((w2 + 0.22, sy + 1.4, z_u)), width=0.15, depth=0.15, mat_idx=1)
    # St. Andrew's X-Bracing along all bays!
    w_bay = (W + 0.4) * 0.5
    for bay_x in [-w_bay * 0.5, w_bay * 0.5]:
        add_timber_beam(bm, Vector((bay_x - 1.2, -d2 - 0.22, z_u)), Vector((bay_x + 1.2, -d2 - 0.22, z_u + h_u)), width=0.15, depth=0.15, mat_idx=1)
        add_timber_beam(bm, Vector((bay_x - 1.2, -d2 - 0.22, z_u + h_u)), Vector((bay_x + 1.2, -d2 - 0.22, z_u)), width=0.15, depth=0.15, mat_idx=1)

    # 3. High-Pitched Shingle Roof with Attic Hoist Arm
    add_pantile_roof(bm, 0, 0, z_u + h_u, W + 0.4, D + 0.4, 4.6, overhang=0.45, courses=8, mat_tile=2, mat_trim=1, mat_plaster=0)
    # Projecting attic hoist arm & pulley with wool sack
    hoist_z = z_u + h_u + 3.2
    add_timber_beam(bm, Vector((0, -d2 - 0.2, hoist_z)), Vector((0, -d2 - 1.8, hoist_z)), width=0.18, depth=0.18, mat_idx=1)
    add_cylinder(bm, 0, -d2 - 1.6, hoist_z - 0.15, radius=0.22, height=0.08, segs=10, mat_idx=1) # pulley
    add_box(bm, 0, -d2 - 1.6, hoist_z - 1.4, 0.65, 0.65, 0.8, mat_idx=12) # suspended wool sack

    # -------------------------------------------------------------
    # 2 MASONRY DYE CAULDRONS (Indigo & Madder Dye Liquors)
    # -------------------------------------------------------------
    for idx, (cy, mat_dye) in enumerate([(-2.2, 4), (1.4, 3)]):
        cx = w2 + 2.2
        # Circular stone base
        add_cylinder(bm, cx, cy, 0.65, radius=1.1, height=1.3, segs=12, mat_idx=9)
        # Fire opening below
        add_box(bm, cx, cy - 1.1, 0.4, 0.6, 0.2, 0.5, mat_idx=10) # fire
        # Steaming dye vat liquid
        add_cylinder(bm, cx, cy, 1.22, radius=0.95, height=0.1, segs=12, mat_idx=mat_dye)

    # -------------------------------------------------------------
    # CLOTH DRYING RAILS WITH DRAPED WOOL TEXTILES
    # -------------------------------------------------------------
    rail_x = w2 + 4.2
    # 3 Drying Rails
    for idx, (ry, mat_cloth) in enumerate([(-3.2, 6), (0.0, 5), (3.2, 7)]):
        add_timber_beam(bm, Vector((rail_x, ry - 1.4, 0)), Vector((rail_x, ry - 1.4, 2.2)), width=0.12, depth=0.12, mat_idx=1)
        add_timber_beam(bm, Vector((rail_x, ry + 1.4, 0)), Vector((rail_x, ry + 1.4, 2.2)), width=0.12, depth=0.12, mat_idx=1)
        add_timber_beam(bm, Vector((rail_x, ry - 1.5, 2.1)), Vector((rail_x, ry + 1.5, 2.1)), width=0.10, depth=0.10, mat_idx=1)
        # Draped cloth textile sheet
        add_box(bm, rail_x, ry, 1.3, 0.04, 2.6, 1.6, mat_idx=mat_cloth)

    # Handcart loaded with rolled colored fabric bolts (Front yard)
    cart_x = 2.4
    cart_y = -d2 - 2.4
    add_box(bm, cart_x, cart_y, 0.5, 1.2, 2.0, 0.4, mat_idx=11)
    # Fabric bolts
    for i, m in enumerate([5, 6, 7, 8]):
        add_cylinder(bm, cart_x - 0.3 + (i % 2) * 0.6, cart_y - 0.5 + (i // 2) * 1.0, 0.85, radius=0.16, height=1.1, segs=8, mat_idx=m)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Weaver")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseWeaver", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_weaver")

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
        mats["timber_dark"], mats["iron_wrought"], mats["roof_tile_red"]
    ]

    # Kraków Gate Tower: 11.0m wide x 13.0m deep x 24.0m high
    # Tier 1: Arched stone carriage portal base
    add_box(bm, 0, 0, 3.0, 11.0, 13.0, 6.0, mat_idx=1)
    # Portal carriage passage (opening)
    add_box(bm, 0, 0, 2.5, 4.5, 13.2, 5.0, mat_idx=3)
    # Iron portcullis slot
    add_box(bm, 0, -5.5, 3.2, 4.2, 0.2, 4.0, mat_idx=4)

    # Tier 2: Square Gothic brick body with arrow loops
    add_box(bm, 0, 0, 9.5, 10.2, 12.0, 7.0, mat_idx=0)

    # Tier 3: Transition to Octagonal brick belfry with machicolations
    add_box(bm, 0, 0, 14.5, 11.0, 12.8, 1.4, mat_idx=1) # corbel gallery
    add_box(bm, 0, 0, 18.0, 8.5, 8.5, 6.0, mat_idx=0) # octagonal tier

    # Tier 4: Copper-clad spire apex
    add_box(bm, 0, 0, 22.5, 7.5, 7.5, 3.0, mat_idx=2)
    add_box(bm, 0, 0, 25.5, 3.5, 3.5, 3.5, mat_idx=2)

    # Outer timber drawbridge spanning dry moat (-Y highway approach)
    add_box(bm, 0, -10.0, 0.4, 4.5, 8.0, 0.35, mat_idx=3)
    add_box(bm, -2.1, -10.0, 0.9, 0.15, 8.0, 0.8, mat_idx=3) # drawbridge railing
    add_box(bm, 2.1, -10.0, 0.9, 0.15, 8.0, 0.8, mat_idx=3)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_GateKrakow")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("GateKrakow", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "gate_krakow")

# -------------------------------------------------------------
# 24. Grodzka Gate (Brama Grodzka)
# -------------------------------------------------------------
def build_grodzka_gate(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["stone_limestone"], mats["roof_tile_red"],
        mats["timber_dark"], mats["iron_wrought"], mats["plaster_white"]
    ]

    # Grodzka Gate Tower: 9.5m wide x 11.0m deep x 18.0m high
    # Ground arched passage
    add_box(bm, 0, 0, 3.0, 9.5, 11.0, 6.0, mat_idx=1)
    add_box(bm, 0, 0, 2.5, 4.0, 11.2, 5.0, mat_idx=3)
    # Heavy oak portcullis
    add_box(bm, 0, -4.5, 3.0, 3.8, 0.2, 4.0, mat_idx=4)

    # 2 Upper brick defensive tiers
    add_box(bm, 0, 0, 9.0, 9.0, 10.4, 6.0, mat_idx=0)
    add_box(bm, 0, 0, 13.5, 9.6, 11.0, 1.4, mat_idx=1) # machicolation

    # Hipped clay pantile roof
    add_box(bm, 0, 0, 15.5, 9.4, 10.8, 2.6, mat_idx=2)
    add_box(bm, 0, 0, 17.2, 5.0, 6.0, 1.8, mat_idx=2)

    # Projecting wooden royal toll collector's booth (+X flank)
    add_box(bm, 5.6, -3.0, 1.8, 2.4, 2.4, 3.6, mat_idx=3)
    add_sloped_roof(bm, 5.6, -3.0, 3.6, 2.4, 2.4, 1.2, overhang=0.2, mat_idx=2)
    # Toll clerk desk and ledger
    add_box(bm, 5.6, -4.4, 1.0, 1.6, 0.6, 0.8, mat_idx=3)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_GateGrodzka")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("GateGrodzka", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "gate_grodzka")

# -------------------------------------------------------------
# 25. Dominican Monastery & Cloister Garden (Klasztor Dominikanów)
# -------------------------------------------------------------
def build_monastery_cloister(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["plaster_white"], mats["roof_tile_red"],
        mats["stone_limestone"], mats["foliage_green"], mats["timber_dark"]
    ]

    # Enclosed 4-sided quadrangle: 24.0m x 24.0m enclosing 12.0m x 12.0m inner quad
    # 4 Cloister wings
    wing_w = 5.5
    wing_len = 24.0
    wing_h = 7.5

    # North and South wings
    for wy in [-9.25, 9.25]:
        add_box(bm, 0, wy, wing_h * 0.5, wing_len, wing_w, wing_h, mat_idx=0)
        add_sloped_roof(bm, 0, wy, wing_h, wing_len, wing_w, 4.0, overhang=0.3, mat_idx=2)

    # East and West wings (connecting)
    for wx in [-9.25, 9.25]:
        add_box(bm, wx, 0, wing_h * 0.5, wing_w, 13.0, wing_h, mat_idx=0)
        add_sloped_roof(bm, wx, 0, wing_h, wing_w, 13.0, 4.0, overhang=0.3, mat_idx=2)

    # Inner pointed arcades facing the courtyard
    for wy in [-6.4, 6.4]:
        for wx in [-4.0, -1.5, 1.5, 4.0]:
            add_box(bm, wx, wy, 2.2, 1.4, 0.15, 3.2, mat_idx=1)
    for wx in [-6.4, 6.4]:
        for wy in [-3.0, 0.0, 3.0]:
            add_box(bm, wx, wy, 2.2, 0.15, 1.4, 3.2, mat_idx=1)

    # INNER CLOISTER GARDEN: 6 raised geometric timber herb beds
    for hx in [-3.0, 3.0]:
        for hy in [-3.0, 0.0, 3.0]:
            add_box(bm, hx, hy, 0.35, 2.2, 1.8, 0.4, mat_idx=5) # timber bed rim
            add_box(bm, hx, hy, 0.55, 2.0, 1.6, 0.2, mat_idx=4) # medicinal herb greenery

    # Central carved limestone fountain basin
    add_cylinder(bm, 0, 0, 0.5, radius=1.2, height=1.0, segs=8, mat_idx=3)
    add_box(bm, 0, 0, 1.4, 0.25, 0.25, 1.2, mat_idx=3) # central fountain pillar

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_MonasteryCloister")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("MonasteryCloister", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "monastery_cloister")

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

    # Civic & Religious
    build_town_hall(mats)
    build_szmatruz(mats)
    build_church_gothic(mats)
    build_monastery_cloister(mats)

    # Fortifications & Military
    build_castle_donjon(mats)
    build_krakow_gate(mats)
    build_grodzka_gate(mats)
    build_archery_yard(mats)
    build_curtain_wall(mats)
    build_defense_tower(mats)

    # Industrial & Resource Production
    build_watermill(mats)
    build_windmill(mats)
    build_stone_quarry(mats)
    build_logging_camp(mats)
    build_river_harbor(mats)
    build_blacksmith_workshop(mats)

    # Specialized Artisan Guild Workshops
    build_baker_house(mats)
    build_tanner_workshop(mats)
    build_brewer_malthouse(mats)
    build_potter_workshop(mats)
    build_weaver_workshop(mats)

    # Residential & Vernacular
    build_house_patrician_brick(mats)
    build_house_half_timber(mats)
    build_house_timber_log(mats)
    build_shed_timber(mats)

    # Market & Clutter Infrastructure
    build_market_stall(mats, "awning_red_white", "red_white")
    build_market_stall(mats, "awning_blue_white", "blue_white")
    build_market_stall(mats, "awning_yellow_white", "yellow_white")
    build_market_cart(mats)
    build_town_well(mats)
    build_tree_oak(mats)

    print("==================================================")
    print("  All 31 3D Assets Successfully Compiled to GLB!  ")
    print("==================================================")

if __name__ == "__main__":
    main()
