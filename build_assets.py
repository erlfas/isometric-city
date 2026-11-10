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
        "flour_sack_cloth": create_mat("FlourSack", (0.78, 0.74, 0.64)),
        "hide_leather": create_mat("HideLeather", (0.62, 0.44, 0.28))
    }

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

def add_cylinder(bm, cx, cy, cz, radius, height, segs=12, mat_idx=0):
    h2 = height * 0.5
    top_verts = []
    bot_verts = []
    for i in range(segs):
        ang = (i / segs) * math.pi * 2
        x = cx + math.cos(ang) * radius
        y = cy + math.sin(ang) * radius
        bot_verts.append(bm.verts.new(Vector((x, y, cz - h2))))
        top_verts.append(bm.verts.new(Vector((x, y, cz + h2))))

    for i in range(segs):
        i_next = (i + 1) % segs
        f = bm.faces.new([bot_verts[i], bot_verts[i_next], top_verts[i_next], top_verts[i]])
        f.material_index = mat_idx

    f_top = bm.faces.new(top_verts)
    f_top.material_index = mat_idx
    f_bot = bm.faces.new(list(reversed(bot_verts)))
    f_bot.material_index = mat_idx

def export_object(obj, name):
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
        mats["stone_limestone"], mats["brick_gothic"], mats["timber_plank"]
    ]

    # Ground floor: stone/brick plinth
    add_box(bm, 0, 0, 2.2, 8.0, 12.0, 4.4, mat_idx=3)
    # Shop opening with fold-down wooden counter shutters
    add_box(bm, -1.8, -6.05, 1.8, 1.4, 0.15, 2.6, mat_idx=1)
    add_box(bm, 1.8, -6.05, 2.0, 2.2, 0.15, 1.6, mat_idx=5) # shutter
    add_box(bm, 1.8, -6.3, 1.3, 2.4, 0.5, 0.1, mat_idx=5) # display shelf

    # Overhanging 2nd floor jetty (0.6m overhang)
    add_box(bm, 0, 0, 6.2, 8.8, 12.6, 3.8, mat_idx=0)
    for x in [-4.42, 4.42]:
        add_box(bm, x, 0, 6.2, 0.12, 12.6, 3.8, mat_idx=1)
    for y in [-6.32, 6.32]:
        add_box(bm, 0, y, 6.2, 8.8, 0.12, 3.8, mat_idx=1)

    # Carved wooden corbels under jetty
    for cx in [-4.0, -2.0, 0.0, 2.0, 4.0]:
        add_box(bm, cx, -6.2, 4.3, 0.35, 0.5, 0.7, mat_idx=1)

    # Clay tiled medieval gable roof with attic dormer
    add_sloped_roof(bm, 0, 0, 8.1, 8.8, 12.6, 5.5, overhang=0.4, mat_idx=2)
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
        mats["plaster_cream"], mats["timber_dark"], mats["roof_tile_red"],
        mats["brick_gothic"], mats["stone_limestone"], mats["timber_plank"],
        mats["flour_sack_cloth"], mats["fire_orange"], mats["awning_yellow_white"]
    ]

    # Main Bakery House: 7.5m wide x 10.5m deep x 7.8m high
    # Ground floor shop plinth
    add_box(bm, 0, 0, 2.2, 7.5, 10.5, 4.4, mat_idx=4) # limestone base
    # Half-timbered upper story
    add_box(bm, 0, 0, 5.8, 7.8, 10.8, 3.2, mat_idx=0)
    for cx in [-3.9, 3.9]:
        add_box(bm, cx, 0, 5.8, 0.15, 10.8, 3.2, mat_idx=1)
    for cy in [-5.4, 5.4]:
        add_box(bm, 0, cy, 5.8, 7.8, 0.15, 3.2, mat_idx=1)

    # Clay pantile roof
    add_sloped_roof(bm, 0, 0, 7.4, 7.8, 10.8, 4.5, overhang=0.4, mat_idx=2)

    # Front bakery shop window & counter
    add_box(bm, -1.5, -5.35, 1.8, 2.2, 0.15, 1.8, mat_idx=5)
    add_box(bm, -1.5, -5.6, 1.2, 2.4, 0.5, 0.1, mat_idx=5) # bread display sill

    # Hanging gilded pretzel sign on forged iron bracket
    add_box(bm, -3.2, -5.6, 3.2, 0.1, 0.8, 0.1, mat_idx=1)
    add_box(bm, -3.2, -5.9, 2.8, 0.1, 0.6, 0.6, mat_idx=8) # pretzel emblem

    # EXTERIOR WORKSPACE: Side yard masonry baking oven complex (+X flank)
    # Raised stone foundation for bread oven
    add_box(bm, 5.2, -1.5, 0.8, 3.2, 3.5, 1.6, mat_idx=4)
    # Domed brick oven body
    add_box(bm, 5.2, -1.5, 2.2, 2.8, 2.8, 1.4, mat_idx=3)
    add_box(bm, 5.2, -1.5, 3.1, 2.0, 2.0, 0.8, mat_idx=3)
    # Oven stokehole arch with glowing fire interior
    add_box(bm, 5.2, -3.15, 1.2, 1.1, 0.15, 1.1, mat_idx=7) # glowing fire
    # Soot-stained masonry chimney stack
    add_box(bm, 5.2, 0.1, 3.5, 1.0, 1.0, 4.2, mat_idx=3)

    # Protective timber lean-to canopy over the oven
    add_box(bm, 6.8, -3.2, 1.8, 0.16, 0.16, 3.6, mat_idx=1)
    add_box(bm, 6.8, 0.2, 1.8, 0.16, 0.16, 3.6, mat_idx=1)
    add_box(bm, 5.4, -1.5, 3.8, 3.6, 4.0, 0.15, mat_idx=5) # canopy roof

    # Birch firewood cords stacked in yard
    add_box(bm, 5.2, 2.4, 0.8, 1.8, 1.2, 1.6, mat_idx=1)
    # Stacked burlap flour sacks
    add_box(bm, 2.5, -5.6, 0.4, 1.2, 0.8, 0.8, mat_idx=6)
    # Baker's long wooden bread peel shovel leaning on wall
    add_box(bm, 3.7, -3.0, 1.5, 0.08, 0.08, 2.8, mat_idx=5)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HouseBaker")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseBaker", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_baker")

# -------------------------------------------------------------
# 13. Tanner's Riverside Workshop (Garbarnia)
# -------------------------------------------------------------
def build_tanner_workshop(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_weathered"], mats["roof_thatch"],
        mats["stone_limestone"], mats["tannin_water"], mats["hide_leather"],
        mats["timber_plank"]
    ]

    # Rustic timber workshop: 8.0m wide x 12.5m deep x 7.5m high
    add_box(bm, -1.5, 0, 0.4, 7.5, 12.0, 0.8, mat_idx=3) # low stone footings
    add_box(bm, -1.5, 0, 2.6, 7.0, 11.5, 3.6, mat_idx=0) # timber log ground floor
    # Open-sided timber drying gallery on upper story
    add_box(bm, -1.5, 0, 5.0, 7.2, 11.8, 1.8, mat_idx=1)
    # Steep thatched roof with sagging eaves
    add_sloped_roof(bm, -1.5, 0, 5.8, 7.4, 12.0, 4.2, overhang=0.6, mat_idx=2)

    # Hanging guild sign: stretched ox hide
    add_box(bm, -1.5, -6.1, 4.0, 0.1, 0.8, 0.1, mat_idx=0)
    add_box(bm, -1.5, -6.5, 3.4, 0.05, 0.7, 0.9, mat_idx=5) # hide pelt

    # EXTERIOR WORKSPACE: Riverfront hide soaking & curing yard (+X flank)
    # 4 sunken rectangular wooden tanning vats filled with dark tannin liquor
    for vy in [-3.6, -1.2, 1.2, 3.6]:
        add_box(bm, 4.0, vy, 0.4, 2.4, 1.8, 0.8, mat_idx=0) # vat timber rim
        add_box(bm, 4.0, vy, 0.5, 2.0, 1.4, 0.6, mat_idx=4) # dark tannin water

    # 2 Tall wooden vertical stretching frames with stretched pelts
    for fy in [-2.5, 2.5]:
        add_box(bm, 6.2, fy, 1.8, 0.12, 2.4, 3.2, mat_idx=0) # timber frame
        add_box(bm, 6.2, fy, 1.8, 0.05, 1.8, 2.4, mat_idx=5) # stretched animal skin

    # Low wooden fleshing beam with curved drawknife
    add_box(bm, 2.4, -4.5, 0.6, 0.8, 1.8, 0.6, mat_idx=6)
    # Stacked cured leather pelts
    add_box(bm, 2.4, 4.5, 0.5, 1.2, 1.4, 1.0, mat_idx=5)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HouseTanner")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseTanner", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_tanner")

# -------------------------------------------------------------
# 14. Brewer's Malthouse & Cask Yard (Browar)
# -------------------------------------------------------------
def build_brewer_malthouse(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["plaster_cream"], mats["timber_dark"],
        mats["timber_plank"], mats["roof_shingle"], mats["copper_patina"],
        mats["stone_limestone"], mats["iron_wrought"]
    ]

    # Sturdy Gothic brick ground floor: 9.5m wide x 14.0m deep x 4.8m high
    add_box(bm, -1.0, 0, 2.4, 9.5, 14.0, 4.8, mat_idx=0)
    # Arched entrance portal with stone surround
    add_box(bm, -1.0, -7.05, 1.8, 2.2, 0.15, 3.2, mat_idx=6)

    # Half-timbered upper story with wooden ventilation louvers for malt drying
    add_box(bm, -1.0, 0, 6.6, 9.8, 14.4, 3.6, mat_idx=1)
    # Malt louvers (horizontal ventilation slits)
    for ly in [-4.5, -1.5, 1.5, 4.5]:
        for lx in [-5.95, 3.95]:
            add_box(bm, lx, ly, 6.8, 0.12, 1.8, 2.0, mat_idx=2)

    # Weathered oak shingle roof
    add_sloped_roof(bm, -1.0, 0, 8.4, 9.8, 14.4, 5.0, overhang=0.4, mat_idx=4)

    # Copper brew kettle and mash paddle guild sign
    add_box(bm, -1.0, -7.3, 4.2, 0.1, 0.9, 0.1, mat_idx=2)
    add_box(bm, -1.0, -7.7, 3.6, 0.08, 0.8, 0.8, mat_idx=5)

    # EXTERIOR WORKSPACE: Cask Yard & Barrel-washing station (+X flank)
    # 2 Long wooden soak wash troughs
    add_box(bm, 5.2, -3.5, 0.4, 1.4, 3.6, 0.8, mat_idx=3)
    add_box(bm, 5.2, 1.5, 0.4, 1.4, 3.6, 0.8, mat_idx=3)

    # Pyramid stack of 6 oak beer barrels / casks
    # Bottom row of 3
    for by in [-1.2, 0.0, 1.2]:
        add_cylinder(bm, 7.5, by, 0.5, radius=0.48, height=1.1, segs=8, mat_idx=2)
    # Second row of 2
    for by in [-0.6, 0.6]:
        add_cylinder(bm, 7.5, by, 1.4, radius=0.48, height=1.1, segs=8, mat_idx=2)
    # Top barrel
    add_cylinder(bm, 7.5, 0.0, 2.3, radius=0.48, height=1.1, segs=8, mat_idx=2)

    # 2 Outdoor heavy wooden tavern tables with benches
    add_box(bm, 7.5, -5.0, 0.75, 1.2, 2.4, 0.1, mat_idx=3) # table
    add_box(bm, 6.6, -5.0, 0.45, 0.4, 2.4, 0.1, mat_idx=3) # bench
    add_box(bm, 8.4, -5.0, 0.45, 0.4, 2.4, 0.1, mat_idx=3) # bench

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HouseBrewer")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseBrewer", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_brewer")

# -------------------------------------------------------------
# 15. Blacksmith's Workshop & Open Forge (Kuźnia)
# -------------------------------------------------------------
def build_blacksmith_workshop(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["stone_limestone"], mats["brick_gothic"], mats["timber_dark"],
        mats["timber_plank"], mats["roof_shingle"], mats["iron_wrought"],
        mats["fire_orange"]
    ]

    # Workshop main building: 8.4m wide x 11.2m deep x 8.6m high
    # Limestone ground floor workshop
    add_box(bm, -1.2, 0, 2.2, 8.4, 11.2, 4.4, mat_idx=0)
    # Upper timber quarters
    add_box(bm, -1.2, 0, 5.8, 8.6, 11.4, 3.2, mat_idx=2)
    # Shingle roof
    add_sloped_roof(bm, -1.2, 0, 7.4, 8.6, 11.4, 4.5, overhang=0.4, mat_idx=4)
    # Massive masonry chimney stack with soot stain
    add_box(bm, 2.0, -1.0, 7.5, 1.4, 1.4, 6.5, mat_idx=1)

    # EXTERIOR FORGE CANOPY (+X flank): 5.5m wide x 5.0m deep
    # Open timber corner posts
    add_box(bm, 5.8, -4.8, 1.8, 0.25, 0.25, 3.6, mat_idx=2)
    add_box(bm, 5.8, 0.8, 1.8, 0.25, 0.25, 3.6, mat_idx=2)
    # Slanted lean-to timber canopy roof
    add_box(bm, 4.4, -2.0, 4.0, 4.8, 6.0, 0.15, mat_idx=3)

    # Masonry hearth furnace with glowing orange embers
    add_box(bm, 3.6, -2.0, 1.2, 1.8, 2.2, 1.4, mat_idx=1)
    add_box(bm, 3.6, -2.0, 1.95, 1.4, 1.6, 0.15, mat_idx=6) # glowing coals

    # Heavy cast iron anvil mounted on oak tree stump
    add_cylinder(bm, 5.2, -2.0, 0.45, radius=0.45, height=0.9, segs=8, mat_idx=2) # stump
    add_box(bm, 5.2, -2.0, 1.15, 0.4, 0.9, 0.5, mat_idx=5) # iron anvil

    # Water-quenching wooden trough
    add_box(bm, 5.2, 0.2, 0.45, 0.8, 1.8, 0.8, mat_idx=3)

    # Vertical weapon and tool rack
    add_box(bm, 5.6, -4.0, 1.0, 0.1, 1.6, 1.8, mat_idx=2)
    add_box(bm, 5.6, -4.0, 1.2, 0.05, 1.4, 1.2, mat_idx=5) # forged blades

    # Stack of iron billets and coal mound
    add_box(bm, 3.2, 0.2, 0.3, 1.0, 1.2, 0.6, mat_idx=5) # iron bars
    add_box(bm, 3.2, -4.0, 0.3, 1.2, 1.2, 0.6, mat_idx=5) # coal

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Blacksmith")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("BlacksmithWorkshop", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "blacksmith_workshop")

# -------------------------------------------------------------
# 16. Potter's Shed & Kiln Yard (Garncarnia)
# -------------------------------------------------------------
def build_potter_workshop(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_cream"], mats["timber_weathered"], mats["roof_thatch"],
        mats["brick_gothic"], mats["stone_limestone"], mats["pottery_terracotta"],
        mats["timber_plank"], mats["fire_orange"]
    ]

    # Rustic wattle-and-daub cottage: 7.2m wide x 9.8m deep x 6.8m high
    add_box(bm, -1.8, 0, 0.3, 7.2, 9.8, 0.6, mat_idx=4) # limestone base
    add_box(bm, -1.8, 0, 2.4, 6.8, 9.4, 3.6, mat_idx=0) # cream loam plaster walls
    for cx in [-5.2, 1.6]:
        for cy in [-4.7, 4.7]:
            add_box(bm, cx, cy, 2.4, 0.2, 0.2, 3.6, mat_idx=1)
    add_sloped_roof(bm, -1.8, 0, 4.2, 6.8, 9.4, 3.8, overhang=0.5, mat_idx=2)

    # Hanging glazed clay amphora sign
    add_box(bm, -1.8, -4.9, 3.2, 0.1, 0.8, 0.1, mat_idx=1)
    add_cylinder(bm, -1.8, -5.4, 2.6, radius=0.25, height=0.6, segs=8, mat_idx=5)

    # EXTERIOR KILN YARD (+X flank)
    # Domed red-brick updraft pottery kiln (2.8m diameter x 3.2m high)
    segs = 12
    radius = 1.4
    for i in range(segs):
        a1 = (i / segs) * math.pi * 2
        a2 = ((i + 1) / segs) * math.pi * 2
        x1, y1 = 4.2 + math.cos(a1) * radius, -1.5 + math.sin(a1) * radius
        x2, y2 = 4.2 + math.cos(a2) * radius, -1.5 + math.sin(a2) * radius
        mx, my = (x1 + x2) * 0.5, (y1 + y2) * 0.5
        seg_len = math.hypot(x2 - x1, y2 - y1)
        add_box(bm, mx, my, 1.0, 0.3, seg_len, 2.0, mat_idx=3)
    # Upper brick dome
    add_box(bm, 4.2, -1.5, 2.4, 2.2, 2.2, 1.2, mat_idx=3)
    # Kiln stone chimney
    add_box(bm, 4.2, -1.5, 4.0, 0.8, 0.8, 2.4, mat_idx=4)
    # Stokehole with glowing fire
    add_box(bm, 4.2, -2.95, 0.6, 0.8, 0.2, 0.8, mat_idx=7)

    # 3-Tiered wooden drying shelves filled with pottery (pots, jugs, amphorae)
    add_box(bm, 4.2, 2.8, 1.4, 1.2, 3.6, 2.6, mat_idx=6) # shelves
    for sy in [1.6, 2.8, 4.0]:
        add_cylinder(bm, 4.0, sy, 0.8, radius=0.2, height=0.45, segs=6, mat_idx=5)
        add_cylinder(bm, 4.4, sy, 1.6, radius=0.22, height=0.5, segs=6, mat_idx=5)
        add_cylinder(bm, 4.2, sy, 2.4, radius=0.18, height=0.4, segs=6, mat_idx=5)

    # Outdoor potter's workbench with foot-kick wheel
    add_box(bm, 2.0, -3.2, 0.8, 1.0, 1.6, 0.8, mat_idx=6)
    add_cylinder(bm, 2.0, -3.2, 1.25, radius=0.35, height=0.08, segs=8, mat_idx=6)

    # Raw clay mound
    add_box(bm, 2.0, 2.0, 0.4, 1.2, 1.2, 0.7, mat_idx=1)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HousePotter")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HousePotter", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_potter")

# -------------------------------------------------------------
# 17. Weaver's Half-Timber Workshop (Warsztat Tkacki)
# -------------------------------------------------------------
def build_weaver_workshop(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_white"], mats["timber_dark"], mats["timber_plank"],
        mats["roof_tile_red"], mats["cloth_indigo"], mats["cloth_red"],
        mats["stone_limestone"], mats["copper_patina"]
    ]

    # Half-timbered workshop: 8.0m wide x 11.0m deep x 8.2m high
    add_box(bm, -1.2, 0, 0.4, 8.0, 11.0, 0.8, mat_idx=6)
    add_box(bm, -1.2, 0, 4.0, 7.8, 10.8, 6.4, mat_idx=0)

    # Diagonal St. Andrew's cross braces (Krzyże św. Andrzeja)
    for x in [-5.15, 2.75]:
        add_box(bm, x, 0, 4.0, 0.12, 10.8, 6.4, mat_idx=1)
    for y in [-5.45, 5.45]:
        add_box(bm, -1.2, y, 4.0, 7.8, 0.12, 6.4, mat_idx=1)

    # Clay pantile roof with dormer and goods hoist beam
    add_sloped_roof(bm, -1.2, 0, 7.2, 7.8, 10.8, 4.8, overhang=0.4, mat_idx=3)
    add_box(bm, -1.2, -3.0, 9.8, 2.0, 2.2, 1.8, mat_idx=0) # dormer
    add_box(bm, -1.2, -4.5, 10.8, 0.15, 1.6, 0.15, mat_idx=1) # hoist beam

    # Hanging shuttle and spindle guild sign
    add_box(bm, -1.2, -5.6, 4.2, 0.1, 0.8, 0.1, mat_idx=1)
    add_box(bm, -1.2, -6.0, 3.6, 0.08, 0.8, 0.4, mat_idx=7)

    # EXTERIOR CLOTHIERS & DYE YARD (+X flank)
    # 2 Large circular stone dye vats (steaming with indigo and red dyes)
    add_cylinder(bm, 4.8, -3.0, 0.7, radius=0.9, height=1.4, segs=8, mat_idx=6)
    add_cylinder(bm, 4.8, -3.0, 1.3, radius=0.8, height=0.1, segs=8, mat_idx=4) # indigo dye
    add_cylinder(bm, 4.8, 0.5, 0.7, radius=0.9, height=1.4, segs=8, mat_idx=6)
    add_cylinder(bm, 4.8, 0.5, 1.3, radius=0.8, height=0.1, segs=8, mat_idx=5) # red dye

    # Long horizontal timber rails with draped dyed cloth drying in wind
    add_box(bm, 4.8, 3.6, 1.2, 0.1, 3.2, 2.2, mat_idx=1) # rail
    add_box(bm, 4.8, 2.6, 1.1, 0.12, 1.4, 1.6, mat_idx=4) # blue cloth
    add_box(bm, 4.8, 4.4, 1.1, 0.12, 1.4, 1.6, mat_idx=5) # red cloth

    # Outdoor wooden yarn-stretching warping frame
    add_box(bm, 3.0, -4.5, 1.0, 1.8, 0.1, 1.8, mat_idx=1)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HouseWeaver")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseWeaver", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_weaver")

# =============================================================
# NEW INDUSTRIAL & RESOURCE COMPLEXES
# =============================================================

# -------------------------------------------------------------
# 18. Riverside Watermill (Młyn Wodny)
# -------------------------------------------------------------
def build_watermill(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_weathered"], mats["timber_plank"],
        mats["roof_thatch"], mats["stone_limestone"], mats["flour_sack_cloth"],
        mats["iron_wrought"]
    ]

    # Watermill built on heavy oak stilts / pilings
    # 8 Stilts extending down to riverbed (-Z)
    for sx in [-4.0, 0.0, 4.0]:
        for sy in [-5.0, 5.0]:
            add_box(bm, sx, sy, 0.0, 0.4, 0.4, 3.0, mat_idx=0)

    # Main mill timber cabin: 9.0m wide x 12.0m deep x 6.5m high (elevated)
    add_box(bm, 0, 0, 3.5, 9.0, 12.0, 4.0, mat_idx=1)
    # Steep thatched roof with mossy eaves
    add_sloped_roof(bm, 0, 0, 5.5, 9.0, 12.0, 4.5, overhang=0.6, mat_idx=3)

    # UNDERSHOT WATERWHEEL (-X flank): 4.2m diameter x 1.4m wide
    wheel_x = -5.2
    wheel_z = 1.6
    radius = 2.1
    paddles = 12
    # Axle
    add_box(bm, wheel_x + 0.5, 0, wheel_z, 1.6, 0.35, 0.35, mat_idx=6)
    # Hub & radiating spokes
    for i in range(paddles):
        ang = (i / paddles) * math.pi * 2
        py = math.cos(ang) * (radius * 0.5)
        pz = wheel_z + math.sin(ang) * (radius * 0.5)
        add_box(bm, wheel_x, py, pz, 1.2, 0.12, radius, mat_idx=0)
    # Perimeter paddles
    for i in range(paddles):
        ang = (i / paddles) * math.pi * 2
        py = math.cos(ang) * radius
        pz = wheel_z + math.sin(ang) * radius
        add_box(bm, wheel_x, py, pz, 1.4, 0.6, 0.1, mat_idx=2)

    # Timber flume race chute directing water onto wheel
    add_box(bm, wheel_x, -4.5, 2.2, 1.6, 5.0, 0.4, mat_idx=2)

    # Quayside wooden deck / pier (+X flank) loaded with flour sacks
    add_box(bm, 5.8, 0, 1.6, 2.6, 10.0, 0.2, mat_idx=2)
    # Stacked burlap flour sacks
    for sy in [-2.0, 0.0, 2.0]:
        add_box(bm, 5.8, sy, 2.1, 1.0, 1.2, 0.8, mat_idx=5)
    # Wooden hand barrow
    add_box(bm, 5.8, -4.0, 2.0, 0.8, 1.6, 0.4, mat_idx=0)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_Watermill")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("Watermill", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "watermill")

# -------------------------------------------------------------
# 19. Hilltop Post Windmill (Wiatrak Koźlak)
# -------------------------------------------------------------
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
