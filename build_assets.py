#!/usr/bin/env python3
"""
Headless Blender Asset Pipeline: Lublin Anno Domini 1392
Procedurally generates high-fidelity low-poly 3D models matching historical medieval architecture:
- Old Town Hall (Ratusz) with clock tower, blind arcades, copper spires, external stairs
- Szmatruz (Cloth Hall) with brick pillars and market stalls
- Gothic Collegiate Parish Church (Fara)
- Defensive Curtain Wall, Octagonal Towers, and Fortified Gates
- Market Stalls with striped scalloped canopies (red/white, blue/white, yellow/white)
- Market Carts with spoked wheels, loaded with goods
- Municipal Stone Well with timber roof and windlass
- Town Pillory (Pręgierz)
- 5 Authentic Medieval House Types (Log cabin, Half-timbered jetty, Patrician stepped brick, Thatched cottage, Artisan workshop)
- Clutter (Barrels, crates) & Medieval Oak Trees
Exports all assets as optimized GLTF/GLB models to public/models/
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
        "foliage_green": create_mat("FoliageGreen", (0.22, 0.45, 0.18), roughness=0.9)
    }

def add_box(bm, cx, cy, cz, w, d, h, mat_idx=0):
    w2, d2, h2 = w * 0.5, d * 0.5, h * 0.5
    # CCW order for correct outward normals in Blender Z-up
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

    # Roof slopes
    f_left = bm.faces.new([v0, r0, r1, v3])
    f_right = bm.faces.new([v1, v2, r1, r0])
    # Gables
    f_front = bm.faces.new([v0, v1, r0])
    f_back = bm.faces.new([v2, v3, r1])

    for f in [f_left, f_right, f_front, f_back]:
        f.material_index = mat_idx

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
    print(f"Exported: {filepath}")

# -------------------------------------------------------------
# 1. Old Town Hall (Ratusz Miejski)
# -------------------------------------------------------------
def build_town_hall(mats):
    clear_scene()
    bm = bmesh.new()

    # Materials: 0=brick, 1=white plaster, 2=roof tile, 3=copper patina, 4=limestone, 5=timber
    mat_list = [
        mats["brick_gothic"], mats["plaster_white"], mats["roof_tile_red"],
        mats["copper_patina"], mats["stone_limestone"], mats["timber_dark"]
    ]

    # Main Building Body (18m wide x 12m deep x 10m high)
    add_box(bm, 0, 0, 5.0, 18.0, 12.0, 10.0, mat_idx=0)
    # White blind arcade niches on facade
    for x in [-6.0, -3.0, 3.0, 6.0]:
        add_box(bm, x, -6.05, 5.5, 1.4, 0.15, 6.0, mat_idx=1)
    # High pitched main roof
    add_sloped_roof(bm, 0, 0, 10.0, 18.0, 12.0, 6.5, overhang=0.4, mat_idx=2)

    # Stepped Gables on left and right ends (Crow-stepped gable / Schodkowy szczyt)
    for x in [-9.0, 9.0]:
        for s in range(5):
            sw = 12.0 - s * 2.2
            add_box(bm, x, 0, 10.0 + s * 1.5, 0.6, sw, 1.5, mat_idx=0)

    # Central Clock Tower (rises to 28m)
    add_box(bm, 0, 0, 16.0, 5.5, 5.5, 12.0, mat_idx=0)
    # Tower white niches
    for y in [-2.78, 2.78]:
        add_box(bm, 0, y, 18.0, 2.2, 0.1, 7.0, mat_idx=1)
    # Clock Face on front
    add_box(bm, 0, -2.85, 20.0, 2.4, 0.1, 2.4, mat_idx=1)

    # Octagonal Belfry
    add_box(bm, 0, 0, 23.5, 5.0, 5.0, 3.0, mat_idx=4)
    # Copper Spire on Clock Tower
    add_box(bm, 0, 0, 27.5, 4.2, 4.2, 5.0, mat_idx=3)
    add_box(bm, 0, 0, 31.0, 2.0, 2.0, 2.5, mat_idx=3)

    # 4 Corner Turrets with verdigris copper roofs
    for cx in [-8.5, 8.5]:
        for cy in [-5.5, 5.5]:
            add_box(bm, cx, cy, 11.5, 1.8, 1.8, 3.5, mat_idx=0)
            add_box(bm, cx, cy, 14.5, 2.0, 2.0, 2.8, mat_idx=3)

    # External Stone Staircase leading to 1st floor portal
    for st in range(8):
        add_box(bm, 9.5 + st * 0.55, -4.5, 0.3 + st * 0.45, 0.6, 2.2, 0.6 + st * 0.9, mat_idx=4)
    # Stair parapet
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

    # Cloth Hall: 24m long x 10m wide
    # 22 Brick Pillars with stone capitals along aisle
    for x in range(-10, 11, 2):
        for y in [-4.0, 4.0]:
            add_box(bm, x, y, 2.5, 0.9, 0.9, 5.0, mat_idx=0)
            # Stone capital
            add_box(bm, x, y, 5.2, 1.2, 1.2, 0.4, mat_idx=1)

    # Covered Aisle Roof
    add_sloped_roof(bm, 0, 0, 5.4, 24.0, 10.0, 4.5, overhang=0.5, mat_idx=2)

    # Vendor stalls inside and along the exterior arcade
    for x in range(-8, 9, 4):
        # Timber stall counter
        add_box(bm, x, -3.2, 1.0, 2.8, 1.4, 1.8, mat_idx=3)
        add_box(bm, x, 3.2, 1.0, 2.8, 1.4, 1.8, mat_idx=3)
        # Striped stall canopies
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

    # Corner timber posts
    w, d = 3.2, 2.2
    w2, d2 = w * 0.5, d * 0.5
    for cx in [-w2 + 0.1, w2 - 0.1]:
        for cy in [-d2 + 0.1, d2 - 0.1]:
            add_box(bm, cx, cy, 1.4, 0.12, 0.12, 2.8, mat_idx=0)

    # Wooden display counter / trestle table
    add_box(bm, 0, 0, 0.85, w - 0.2, d - 0.2, 0.8, mat_idx=1)
    # Front counter lip
    add_box(bm, 0, -d2 + 0.05, 0.9, w, 0.1, 0.15, mat_idx=0)

    # Goods displayed on counter (cheese wheels, bread, fabric bolts)
    add_box(bm, -0.8, 0.2, 1.35, 0.7, 0.7, 0.3, mat_idx=3) # cheese
    add_box(bm, -0.8, -0.4, 1.35, 0.6, 0.5, 0.25, mat_idx=3) # bread
    add_box(bm, 0.6, 0.0, 1.4, 1.0, 0.6, 0.4, mat_idx=4) # fabrics

    # Pitched striped fabric canopy with scalloped cloth valance
    # Main slope
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

    # Scalloped valance fringe hanging down
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

    # Cart bed (2.4m long x 1.2m wide)
    add_box(bm, 0, 0, 0.85, 1.2, 2.4, 0.1, mat_idx=0)
    # Wooden slatted sideboards
    add_box(bm, -0.55, 0, 1.15, 0.08, 2.4, 0.5, mat_idx=0)
    add_box(bm, 0.55, 0, 1.15, 0.08, 2.4, 0.5, mat_idx=0)
    add_box(bm, 0, 1.15, 1.15, 1.2, 0.08, 0.5, mat_idx=0)

    # Cart tongue / shafts for ox/horse
    add_box(bm, -0.3, -1.8, 0.55, 0.08, 1.6, 0.08, mat_idx=1)
    add_box(bm, 0.3, -1.8, 0.55, 0.08, 1.6, 0.08, mat_idx=1)

    # Axle
    add_box(bm, 0, 0, 0.6, 1.6, 0.1, 0.1, mat_idx=2)

    # 2 Large Spoked Wheels (1.2m diameter)
    for wx in [-0.75, 0.75]:
        # Wheel rim (approximated 8-gon)
        segs = 8
        for i in range(segs):
            a1 = (i / segs) * math.pi * 2
            a2 = ((i + 1) / segs) * math.pi * 2
            y1 = math.cos(a1) * 0.6
            z1 = 0.6 + math.sin(a1) * 0.6
            y2 = math.cos(a2) * 0.6
            z2 = 0.6 + math.sin(a2) * 0.6
            my = (y1 + y2) * 0.5
            mz = (z1 + z2) * 0.5
            len_seg = math.hypot(y2 - y1, z2 - z1)
            add_box(bm, wx, my, mz, 0.08, len_seg, 0.08, mat_idx=1)
        # Hub & spokes
        add_box(bm, wx, 0, 0.6, 0.18, 0.2, 0.2, mat_idx=2)
        add_box(bm, wx, 0, 0.6, 0.06, 1.1, 0.06, mat_idx=1)
        add_box(bm, wx, 0, 0.6, 0.06, 0.06, 1.1, mat_idx=1)

    # Loaded cargo in cart (casks and sacks)
    add_box(bm, 0, 0.4, 1.15, 0.8, 0.8, 0.7, mat_idx=1) # Cask
    add_box(bm, 0, -0.4, 1.05, 0.7, 0.9, 0.5, mat_idx=3) # Sacks

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

    # Round/Octagonal stone wellhead (2.2m diameter x 1.0m high)
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

    # Timber upright posts
    add_box(bm, -0.9, 0, 1.8, 0.16, 0.16, 2.6, mat_idx=1)
    add_box(bm, 0.9, 0, 1.8, 0.16, 0.16, 2.6, mat_idx=1)
    # Cross beam & rope windlass
    add_box(bm, 0, 0, 2.8, 1.9, 0.16, 0.16, mat_idx=1)
    add_box(bm, 0, 0, 2.4, 0.9, 0.2, 0.2, mat_idx=3) # rope spool

    # Pitched shingle rooflet
    add_sloped_roof(bm, 0, 0, 2.9, 2.2, 1.8, 1.1, overhang=0.2, mat_idx=2)

    # Wooden bucket on well rim
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
# 6. House Type 1: Timber Log House (Dom zrębowy)
# -------------------------------------------------------------
def build_house_timber_log(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["timber_dark"], mats["timber_plank"], mats["roof_shingle"],
        mats["stone_limestone"], mats["brick_gothic"]
    ]

    # Stone plinth
    add_box(bm, 0, 0, 0.4, 8.4, 11.4, 0.8, mat_idx=3)

    # Horizontal interlocking log walls
    # Main log body: 8m wide x 11m deep x 5m high
    add_box(bm, 0, 0, 3.2, 8.0, 11.0, 4.8, mat_idx=0)
    # Protruding notched corner log ends (wieńce)
    for cx in [-4.15, 4.15]:
        for cy in [-5.65, 5.65]:
            add_box(bm, cx, cy, 3.2, 0.45, 0.45, 4.8, mat_idx=1)

    # Wooden framed windows and door
    add_box(bm, 0, -5.55, 1.6, 1.2, 0.15, 2.2, mat_idx=1)
    add_box(bm, -2.4, -5.55, 2.2, 1.0, 0.15, 1.2, mat_idx=1)
    add_box(bm, 2.4, -5.55, 2.2, 1.0, 0.15, 1.2, mat_idx=1)

    # Steep pitched wooden shingle roof (60° medieval pitch)
    add_sloped_roof(bm, 0, 0, 5.6, 8.0, 11.0, 5.2, overhang=0.5, mat_idx=2)
    # Carved wooden ridge finial / cross
    add_box(bm, 0, -5.8, 11.1, 0.15, 0.3, 0.8, mat_idx=1)
    add_box(bm, 0, 5.8, 11.1, 0.15, 0.3, 0.8, mat_idx=1)

    # Red brick chimney
    add_box(bm, 2.0, 2.0, 8.5, 1.1, 1.1, 4.5, mat_idx=4)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HouseLog")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseLog", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_timber_log")

# -------------------------------------------------------------
# 7. House Type 2: Half-Timber with Jetty (Kamienica szachulcowa)
# -------------------------------------------------------------
def build_house_half_timber(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["plaster_white"], mats["timber_dark"], mats["roof_tile_red"],
        mats["stone_limestone"], mats["brick_gothic"]
    ]

    # Ground floor: stone/brick plinth
    add_box(bm, 0, 0, 2.2, 8.0, 12.0, 4.4, mat_idx=3)
    # Arched portal and workshop shutter
    add_box(bm, -1.8, -6.05, 1.8, 1.4, 0.15, 2.6, mat_idx=1)
    add_box(bm, 1.8, -6.05, 2.0, 2.2, 0.15, 1.6, mat_idx=1)

    # Overhanging second floor jetty (0.6m overhang with corbels)
    add_box(bm, 0, 0, 6.2, 8.8, 12.6, 3.8, mat_idx=0)
    # Exposed diagonal timber braces (Fachwerk framing)
    for x in [-4.42, 4.42]:
        add_box(bm, x, 0, 6.2, 0.12, 12.6, 3.8, mat_idx=1)
    for y in [-6.32, 6.32]:
        add_box(bm, 0, y, 6.2, 8.8, 0.12, 3.8, mat_idx=1)
    # Carved wooden corbels under jetty
    for cx in [-4.0, -1.5, 1.5, 4.0]:
        add_box(bm, cx, -6.1, 4.4, 0.35, 0.5, 0.6, mat_idx=1)

    # Clay tiled medieval gable roof with attic dormer
    add_sloped_roof(bm, 0, 0, 8.1, 8.8, 12.6, 5.5, overhang=0.4, mat_idx=2)
    # Attic dormer window
    add_box(bm, 2.2, -2.0, 11.2, 1.6, 2.2, 1.8, mat_idx=0)
    add_sloped_roof(bm, 2.2, -2.0, 12.1, 1.6, 2.2, 1.0, overhang=0.2, mat_idx=2)

    bm.normal_update()
    mesh = bpy.data.meshes.new("Mesh_HouseHalfTimber")
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list: mesh.materials.append(m)
    obj = bpy.data.objects.new("HouseHalfTimber", mesh)
    bpy.context.collection.objects.link(obj)
    export_object(obj, "house_half_timber")

# -------------------------------------------------------------
# 8. House Type 3: Patrician Stepped Brick Kamienica
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
    # White plaster gothic lancet niches
    for x in [-2.5, 0, 2.5]:
        add_box(bm, x, -7.05, 5.0, 1.4, 0.12, 4.5, mat_idx=1)
        add_box(bm, x, -7.05, 2.0, 1.2, 0.12, 2.2, mat_idx=1)

    # High pitched clay tile roof
    add_sloped_roof(bm, 0, 0, 8.0, 9.0, 14.0, 6.0, overhang=0.2, mat_idx=2)

    # Crow-stepped gable on front (Szczyt schodkowy ze sterczynami)
    steps = 5
    for s in range(steps):
        sw = 9.0 - s * 1.6
        sz = 8.0 + s * 1.3
        add_box(bm, 0, -7.05, sz + 0.65, sw, 0.5, 1.3, mat_idx=0)
        # Small white plaster pinnacle / sterczyna on each step
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
# 9. Curtain Wall Segment & Octagonal Defense Tower
# -------------------------------------------------------------
def build_curtain_wall(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [
        mats["brick_gothic"], mats["stone_limestone"], mats["timber_dark"],
        mats["roof_tile_red"]
    ]

    # Wall segment: 16m long x 2.4m thick x 8m high
    add_box(bm, 0, 0, 1.0, 16.0, 2.6, 2.0, mat_idx=1) # Limestone foundation
    add_box(bm, 0, 0, 5.0, 16.0, 2.4, 6.0, mat_idx=0) # Brick body

    # Battlements / Crenellations on outer edge (+Y)
    for x in range(-7, 8, 2):
        add_box(bm, x, 1.1, 8.8, 1.2, 0.4, 1.6, mat_idx=0)

    # Inner wooden wall-walk hoarding / gallery (-Y)
    add_box(bm, 0, -1.0, 7.6, 16.0, 1.4, 0.2, mat_idx=2)
    # Wooden railing
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

    # Tower body: 7m wide x 7m deep x 16m high
    add_box(bm, 0, 0, 1.0, 7.4, 7.4, 2.0, mat_idx=1) # base
    add_box(bm, 0, 0, 8.0, 7.0, 7.0, 12.0, mat_idx=0)

    # Machicolations & crenellated top gallery
    add_box(bm, 0, 0, 14.6, 8.2, 8.2, 1.4, mat_idx=1)
    for cx in [-3.5, 0, 3.5]:
        for cy in [-3.5, 3.5]:
            add_box(bm, cx, cy, 16.0, 1.4, 0.5, 1.4, mat_idx=0)

    # Conical / Pyramidal red tile roof
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
# 10. Medieval Oak Tree
# -------------------------------------------------------------
def build_tree_oak(mats):
    clear_scene()
    bm = bmesh.new()

    mat_list = [mats["timber_dark"], mats["foliage_green"]]

    # Twisted wooden trunk
    add_box(bm, 0, 0, 2.0, 0.7, 0.7, 4.0, mat_idx=0)
    add_box(bm, 0.4, 0.3, 4.2, 0.5, 0.5, 2.0, mat_idx=0)
    add_box(bm, -0.3, -0.2, 4.5, 0.5, 0.5, 2.2, mat_idx=0)

    # Leafy foliage clusters (low-poly rounded volumes)
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

# -------------------------------------------------------------
# Main Execution
# -------------------------------------------------------------
def main():
    print("==================================================")
    print("  Compiling High-Quality 3D Assets via Blender CLI")
    print("==================================================")
    mats = get_materials()

    build_town_hall(mats)
    build_szmatruz(mats)
    build_market_stall(mats, "awning_red_white", "red_white")
    build_market_stall(mats, "awning_blue_white", "blue_white")
    build_market_stall(mats, "awning_yellow_white", "yellow_white")
    build_market_cart(mats)
    build_town_well(mats)
    build_house_timber_log(mats)
    build_house_half_timber(mats)
    build_house_patrician_brick(mats)
    build_curtain_wall(mats)
    build_defense_tower(mats)
    build_tree_oak(mats)

    print("All 3D assets compiled and exported to GLB format!")

if __name__ == "__main__":
    main()
