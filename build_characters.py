#!/usr/bin/env python3
"""
Procedural 3D Medieval Character Pipeline: Lublin Anno Domini 1392
Synthesizes low-poly 3D character models based on 3-view turnaround references:
- 1. char_baker: Master Baker with flour apron, linen barett cap, bread peel shovel & sourdough loaf
- 2. char_tanner: Master Tanner with oiled raw hide apron, tied coif, two-handed curved fleshing knife
- 3. char_carpenter: Master Carpenter with canvas smock, tool belt, wooden block plane & broadaxe
- 4. char_blacksmith: Master Blacksmith with heavy leather apron, cross-peen hammer & tongs with hot iron
- 5. char_brewer: Master Brewer with red cotte, stained bib apron, chaperon, copper mash paddle & tankard
- 6. char_potter: Master Potter with clay spattered tunic, headband, pottery shaping rib & terracotta jug
- 7. char_weaver: Master Weaver with mi-parti cotte, liripipe hood, threaded shuttle & tailor shears
- 8. char_stonemason: Stone Mason with stone dust smock, split apron, gloves, mallet & chisel
- 9. char_woodcutter: Woodcutter with hooded cowl, felling wedges, heavy broad felling axe & boots
- 10. char_friar: Dominican Friar with white habit, dark brown scapular, rope cincture, wooden hoe & herb basket
- 11. char_guard: Town Guard with kettle hat helmet, gambeson, red heraldic tabard, halberd & sword
- 12. char_merchant: Patrician Merchant with royal blue houppelande, fur collar, chaperon & wax-sealed scroll
- 13. char_farmer: Peasant Farmer with straw hat, loose linen shirt, rope belt, curved harvest scythe
- 14. char_townswoman: Burgher Townswoman with green kirtle, white apron, wimple veil & market basket

Exports GLB models to public/models/ (the renderer loads char_*.glb from there).
Tanner and blacksmith are kits (see "Kit pipeline (v2)" below); the rest are legacy single meshes.

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

def get_materials():
    return {
        "skin": create_mat("CharSkin", (0.86, 0.68, 0.54), roughness=0.6),
        "skin_tan": create_mat("CharSkinTan", (0.76, 0.56, 0.42), roughness=0.6),
        "hair_brown": create_mat("CharHairBrown", (0.22, 0.14, 0.08), roughness=0.9),
        "hair_grey": create_mat("CharHairGrey", (0.55, 0.53, 0.50), roughness=0.9),
        "hair_blonde": create_mat("CharHairBlonde", (0.72, 0.60, 0.35), roughness=0.9),
        "linen_white": create_mat("CharLinenWhite", (0.86, 0.84, 0.78), roughness=0.8),
        "linen_flour": create_mat("CharLinenFlour", (0.92, 0.90, 0.86), roughness=0.8),
        "leather_dark": create_mat("CharLeatherDark", (0.16, 0.11, 0.07), roughness=0.7),
        "leather_oiled": create_mat("CharLeatherOiled", (0.12, 0.10, 0.08), roughness=0.55),
        "leather_tan": create_mat("CharLeatherTan", (0.38, 0.26, 0.16), roughness=0.7),
        "wool_brown": create_mat("CharWoolBrown", (0.32, 0.24, 0.16), roughness=0.85),
        "wool_grey": create_mat("CharWoolGrey", (0.42, 0.40, 0.38), roughness=0.85),
        "wool_ochre": create_mat("CharWoolOchre", (0.58, 0.45, 0.22), roughness=0.85),
        "wool_red": create_mat("CharWoolRed", (0.54, 0.15, 0.14), roughness=0.8),
        "wool_blue": create_mat("CharWoolBlue", (0.15, 0.28, 0.55), roughness=0.8),
        "wool_green": create_mat("CharWoolGreen", (0.18, 0.35, 0.18), roughness=0.8),
        "straw_yellow": create_mat("CharStrawYellow", (0.65, 0.52, 0.25), roughness=0.8),
        "iron_steel": create_mat("CharIronSteel", (0.55, 0.56, 0.58), roughness=0.35, metallic=0.8),
        "iron_dark": create_mat("CharIronDark", (0.18, 0.18, 0.20), roughness=0.45, metallic=0.6),
        "wood_ash": create_mat("CharWoodAsh", (0.48, 0.36, 0.24), roughness=0.75),
        "wood_dark": create_mat("CharWoodDark", (0.28, 0.18, 0.10), roughness=0.75),
        "copper": create_mat("CharCopper", (0.72, 0.38, 0.22), roughness=0.35, metallic=0.7),
        "gold_trim": create_mat("CharGoldTrim", (0.85, 0.68, 0.18), roughness=0.3, metallic=0.6),
        "fur_brown": create_mat("CharFurBrown", (0.25, 0.16, 0.11), roughness=0.9),
        "terracotta": create_mat("CharTerracotta", (0.68, 0.32, 0.18), roughness=0.75),
        "bread_crust": create_mat("CharBreadCrust", (0.72, 0.48, 0.22), roughness=0.8),
        "hot_iron": create_mat("CharHotIron", (0.95, 0.35, 0.05), roughness=0.2),
        "herb_green": create_mat("CharHerbGreen", (0.25, 0.45, 0.20), roughness=0.8),
        "wicker": create_mat("CharWicker", (0.55, 0.42, 0.25), roughness=0.85)
    }

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

def build_humanoid_base(bm, mat_map, 
                        tunic_mat, hose_mat, shoe_mat, skin_mat,
                        tunic_w=0.48, tunic_d=0.28, tunic_h=0.55,
                        has_skirt=True, skirt_len=0.35, skirt_flare=0.56,
                        head_scale=1.0):
    """
    Constructs the anatomical 1.75m base humanoid:
    - Boots / shoes: Z in [0.0, 0.16]
    - Legs / chausses: Z in [0.16, 0.85]
    - Torso & tunic: Z in [0.85, 1.40]
    - Neck: Z in [1.40, 1.46]
    - Head & face: Z in [1.46, 1.70]
    """
    # 1. Shoes
    add_box(bm, -0.12, -0.04, 0.08, 0.14, 0.26, 0.16, mat_idx=shoe_mat)
    add_box(bm, 0.12, -0.04, 0.08, 0.14, 0.26, 0.16, mat_idx=shoe_mat)

    # 2. Legs (Chausses)
    add_cylinder(bm, -0.12, 0.0, 0.48, r=0.085, h=0.64, segs=6, mat_idx=hose_mat)
    add_cylinder(bm, 0.12, 0.0, 0.48, r=0.085, h=0.64, segs=6, mat_idx=hose_mat)

    # 3. Torso (Tunic upper body)
    torso_cz = 0.85 + tunic_h * 0.5
    add_tapered_box(bm, 0, 0, torso_cz, 
                    w_bot=tunic_w * 0.9, d_bot=tunic_d * 0.9, 
                    w_top=tunic_w, d_top=tunic_d, 
                    h=tunic_h, mat_idx=tunic_mat)

    # Lower tunic skirt / hem
    if has_skirt:
        skirt_cz = 0.85 - skirt_len * 0.5
        add_tapered_box(bm, 0, 0, skirt_cz,
                        w_bot=skirt_flare, d_bot=tunic_d * 1.25,
                        w_top=tunic_w * 0.92, d_top=tunic_d * 0.92,
                        h=skirt_len, mat_idx=tunic_mat)

    # 4. Belt
    add_box(bm, 0, 0, 0.85, tunic_w * 0.95, tunic_d * 0.95, 0.07, mat_idx=mat_map["leather_dark"])
    # Belt buckle
    add_box(bm, 0, -tunic_d * 0.48, 0.85, 0.08, 0.03, 0.08, mat_idx=mat_map["iron_steel"])

    # 5. Neck & Head
    add_cylinder(bm, 0, 0, 1.42, r=0.065, h=0.08, segs=6, mat_idx=skin_mat)
    # Head (stylized polygonal sphere)
    head_r = 0.14 * head_scale
    add_box(bm, 0, 0, 1.57, head_r * 1.9, head_r * 2.0, head_r * 2.1, mat_idx=skin_mat)
    # Nose profile
    add_box(bm, 0, -head_r * 1.05, 1.57, 0.04, 0.05, 0.07, mat_idx=skin_mat)

    # 6. Arms (Posed holding or resting)
    # Left shoulder / arm
    add_oriented_cylinder(bm, (-tunic_w * 0.5, 0, 1.35), (-tunic_w * 0.55 - 0.06, 0.02, 1.05), radius=0.075, segs=6, mat_idx=tunic_mat)
    add_oriented_cylinder(bm, (-tunic_w * 0.55 - 0.06, 0.02, 1.05), (-0.30, -0.15, 0.88), radius=0.065, segs=6, mat_idx=skin_mat)

    # Right shoulder / arm (Dominant tool arm)
    add_oriented_cylinder(bm, (tunic_w * 0.5, 0, 1.35), (tunic_w * 0.55 + 0.06, 0.02, 1.05), radius=0.075, segs=6, mat_idx=tunic_mat)
    add_oriented_cylinder(bm, (tunic_w * 0.55 + 0.06, 0.02, 1.05), (0.30, -0.15, 0.88), radius=0.065, segs=6, mat_idx=skin_mat)

def add_apron(bm, mat_apron, w=0.34, h=0.75, bib_w=0.26, bib_h=0.32):
    """Adds a realistic layered bib apron over the chest and legs."""
    # Bib
    add_box(bm, 0, -0.145, 1.20, bib_w, 0.03, bib_h, mat_idx=mat_apron)
    # Skirt
    add_box(bm, 0, -0.155, 0.72, w, 0.03, h, mat_idx=mat_apron)
    # Apron neck strap
    add_box(bm, 0, 0, 1.36, bib_w * 0.9, 0.26, 0.03, mat_idx=mat_apron)

def add_coif_or_hood(bm, mat_idx, has_liripipe=False, liripipe_len=0.5):
    """Adds a historical linen coif or woolen hood over head."""
    # Head cowl
    add_box(bm, 0, 0.03, 1.60, 0.31, 0.28, 0.28, mat_idx=mat_idx)
    # Shoulder capelet
    add_tapered_box(bm, 0, 0, 1.38, w_bot=0.54, d_bot=0.36, w_top=0.30, d_top=0.28, h=0.18, mat_idx=mat_idx)
    if has_liripipe:
        # Hanging tail behind
        add_oriented_cylinder(bm, (0, 0.16, 1.62), (0.05, 0.18 + liripipe_len * 0.3, 1.62 - liripipe_len), radius=0.04, segs=6, mat_idx=mat_idx)

# -------------------------------------------------------------
# Archetype Specific Builders
# -------------------------------------------------------------

def build_char_baker(bm, mats):
    """Master Baker with flour-dusted apron, linen barett cap, bread peel & loaf."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["linen_flour"], 
                        hose_mat=mats["wool_brown"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin"])
    # White flour apron
    add_apron(bm, mats["linen_white"], w=0.36, h=0.70)
    # Baker canvas cap / barett
    add_cylinder(bm, 0, 0, 1.70, r=0.19, h=0.10, segs=8, mat_idx=mats["linen_white"])
    add_cylinder(bm, 0, 0, 1.74, r=0.23, h=0.08, segs=8, mat_idx=mats["linen_white"])

    # Held Prop: 1.8m wooden bread peel shovel in right hand
    # Long ash handle
    add_oriented_cylinder(bm, (0.30, -0.40, 0.0), (0.30, 0.20, 1.60), radius=0.022, segs=6, mat_idx=mats["wood_ash"])
    # Flat paddle blade
    add_box(bm, 0.30, -0.65, 0.10, 0.26, 0.40, 0.025, mat_idx=mats["wood_ash"])
    # Crusty round sourdough loaf resting on peel blade
    add_cylinder(bm, 0.30, -0.65, 0.14, r=0.10, h=0.065, segs=8, mat_idx=mats["bread_crust"])

def build_char_tanner(bm, mats):
    """Master Tanner with dark oiled rawhide apron, tied coif, 2-handed fleshing knife."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["wool_brown"], 
                        hose_mat=mats["wool_grey"], 
                        shoe_mat=mats["leather_oiled"], 
                        skin_mat=mats["skin_tan"])
    # Heavy waterproof dark oiled leather apron
    add_apron(bm, mats["leather_oiled"], w=0.38, h=0.82)
    # White linen coif tied under chin
    add_coif_or_hood(bm, mats["linen_white"])
    # High water-resistant work boots
    add_box(bm, -0.12, 0, 0.26, 0.17, 0.17, 0.26, mat_idx=mats["leather_oiled"])
    add_box(bm, 0.12, 0, 0.26, 0.17, 0.17, 0.26, mat_idx=mats["leather_oiled"])

    # Held Prop: Curved two-handled iron fleshing knife
    # Steel blade
    add_box(bm, 0.0, -0.26, 0.88, 0.46, 0.04, 0.07, mat_idx=mats["iron_steel"])
    # Wooden turned handles on both ends
    add_box(bm, -0.24, -0.26, 0.88, 0.06, 0.10, 0.05, mat_idx=mats["wood_dark"])
    add_box(bm, 0.24, -0.26, 0.88, 0.06, 0.10, 0.05, mat_idx=mats["wood_dark"])

def build_char_carpenter(bm, mats):
    """Master Carpenter with canvas smock, leather tool belt, block plane & broadaxe."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["wool_brown"], 
                        hose_mat=mats["wool_grey"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin"])
    # Canvas workshop apron
    add_apron(bm, mats["linen_white"], w=0.36, h=0.68)
    # Felt work cap
    add_cylinder(bm, 0, 0, 1.70, r=0.18, h=0.12, segs=8, mat_idx=mats["wool_grey"])

    # Heavy leather tool belt with hanging accessories
    # Carpenter wooden mallet hanging on left hip
    add_cylinder(bm, -0.25, 0.02, 0.72, r=0.045, h=0.14, segs=6, mat_idx=mats["wood_ash"])
    add_cylinder(bm, -0.25, 0.02, 0.76, r=0.015, h=0.22, segs=4, mat_idx=mats["wood_ash"])
    # Iron framing square on belt
    add_box(bm, 0.24, -0.12, 0.74, 0.02, 0.12, 0.16, mat_idx=mats["iron_steel"])

    # Left hand: Wooden block plane
    add_box(bm, -0.28, -0.22, 0.88, 0.11, 0.24, 0.09, mat_idx=mats["wood_dark"])
    add_box(bm, -0.28, -0.22, 0.94, 0.04, 0.08, 0.05, mat_idx=mats["iron_steel"]) # plane iron

    # Right hand: Broad carpenter felling axe
    add_oriented_cylinder(bm, (0.32, -0.15, 0.35), (0.32, -0.15, 1.15), radius=0.025, segs=6, mat_idx=mats["wood_ash"])
    add_box(bm, 0.32, -0.24, 1.08, 0.04, 0.18, 0.16, mat_idx=mats["iron_steel"]) # axe blade

def build_char_blacksmith(bm, mats):
    """Master Blacksmith with heavy leather apron, cross-peen hammer & tongs with hot iron."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["linen_white"], 
                        hose_mat=mats["wool_grey"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin_tan"],
                        tunic_w=0.52) # broader shoulders
    # Heavy cowhide blacksmith apron
    add_apron(bm, mats["leather_dark"], w=0.40, h=0.82)
    # Tied linen coif
    add_coif_or_hood(bm, mats["linen_white"])

    # Heavy heat-resistant smithing gauntlets
    add_box(bm, -0.32, -0.15, 0.92, 0.12, 0.14, 0.18, mat_idx=mats["leather_dark"])
    add_box(bm, 0.32, -0.15, 0.92, 0.12, 0.14, 0.18, mat_idx=mats["leather_dark"])

    # Right hand: Cross-peen forging hammer
    add_cylinder(bm, 0.32, -0.18, 0.85, r=0.02, h=0.42, segs=6, mat_idx=mats["wood_ash"])
    add_box(bm, 0.32, -0.18, 1.02, 0.08, 0.18, 0.08, mat_idx=mats["iron_steel"])

    # Left hand: Long forged blacksmith tongs holding orange-hot iron billet
    add_oriented_cylinder(bm, (-0.32, -0.15, 0.88), (-0.15, -0.45, 0.82), radius=0.015, segs=4, mat_idx=mats["iron_dark"])
    # Glowing billet
    add_box(bm, -0.15, -0.52, 0.82, 0.06, 0.16, 0.04, mat_idx=mats["hot_iron"])

def build_char_brewer(bm, mats):
    """Master Brewer with red cotte, leather apron, chaperon, copper paddle & tankard."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["wool_red"], 
                        hose_mat=mats["wool_grey"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin"])
    # Stained dark bib apron
    add_apron(bm, mats["leather_dark"], w=0.38, h=0.76)
    # Blue/burgundy velvet chaperon hat with folded roll and tail
    add_cylinder(bm, 0, 0, 1.68, r=0.19, h=0.10, segs=8, mat_idx=mats["wool_blue"])
    add_cylinder(bm, 0, 0, 1.74, r=0.22, h=0.08, segs=8, mat_idx=mats["wool_blue"])
    add_oriented_cylinder(bm, (0.16, 0.08, 1.72), (0.24, 0.12, 1.25), radius=0.04, segs=6, mat_idx=mats["wool_blue"])

    # Left hand: Wooden tavern beer tankard
    add_cylinder(bm, -0.28, -0.22, 0.88, r=0.07, h=0.15, segs=8, mat_idx=mats["wood_dark"])
    add_box(bm, -0.28, -0.14, 0.88, 0.03, 0.06, 0.10, mat_idx=mats["wood_dark"]) # handle

    # Right hand: 1.6m polished copper mash paddle
    add_oriented_cylinder(bm, (0.32, -0.15, 0.15), (0.32, -0.15, 1.65), radius=0.022, segs=6, mat_idx=mats["wood_ash"])
    add_box(bm, 0.32, -0.15, 0.30, 0.025, 0.18, 0.35, mat_idx=mats["copper"]) # paddle blade

def build_char_potter(bm, mats):
    """Master Potter with clay-spattered tunic, headband, shaping rib & terracotta jug."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["linen_white"], 
                        hose_mat=mats["wool_ochre"], 
                        shoe_mat=mats["leather_tan"], 
                        skin_mat=mats["skin_tan"])
    # Cloth headband
    add_cylinder(bm, 0, 0, 1.63, r=0.16, h=0.05, segs=8, mat_idx=mats["wool_grey"])
    # Clay-stained work apron
    add_apron(bm, mats["leather_tan"], w=0.34, h=0.68)

    # Right hand: Wooden pottery shaping rib
    add_box(bm, 0.28, -0.18, 0.88, 0.02, 0.12, 0.08, mat_idx=mats["wood_ash"])

    # Left hand: Freshly thrown terracotta clay amphora / pitcher
    add_cylinder(bm, -0.28, -0.24, 0.88, r=0.085, h=0.22, segs=8, mat_idx=mats["terracotta"])
    add_cone(bm, -0.28, -0.24, 1.02, r_bot=0.085, r_top=0.055, h=0.08, segs=8, mat_idx=mats["terracotta"])

def build_char_weaver(bm, mats):
    """Master Weaver with mi-parti cotte, liripipe hood, threaded shuttle & shears."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["wool_red"], 
                        hose_mat=mats["wool_grey"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin"])
    # Mi-parti left side blue overlay
    add_box(bm, -0.12, 0, 1.12, 0.24, 0.30, 0.55, mat_idx=mats["wool_blue"])
    add_box(bm, -0.14, 0, 0.70, 0.28, 0.35, 0.35, mat_idx=mats["wool_blue"])

    # Hood with long liripipe tail
    add_coif_or_hood(bm, mats["wool_red"], has_liripipe=True, liripipe_len=0.7)

    # Right hand: Threaded weaving shuttle
    add_box(bm, 0.28, -0.20, 0.88, 0.05, 0.22, 0.04, mat_idx=mats["wood_dark"])
    add_cylinder(bm, 0.28, -0.20, 0.88, r=0.02, h=0.10, segs=6, mat_idx=mats["linen_white"]) # wound yarn

    # Left hand: Large forged iron tailor shears
    add_box(bm, -0.28, -0.20, 0.86, 0.02, 0.18, 0.05, mat_idx=mats["iron_steel"])

def build_char_stonemason(bm, mats):
    """Stone Mason with stone dust smock, split apron, gloves, mallet & chisel."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["linen_white"], 
                        hose_mat=mats["wool_grey"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin"])
    # White linen coif
    add_coif_or_hood(bm, mats["linen_white"])
    # Split leather mason's apron
    add_apron(bm, mats["leather_tan"], w=0.38, h=0.78)

    # Left hand: Pointed steel stonecutter's chisel
    add_cylinder(bm, -0.28, -0.18, 0.88, r=0.018, h=0.22, segs=6, mat_idx=mats["iron_steel"])

    # Right hand: Round stonecutter's beechwood mallet
    add_cylinder(bm, 0.28, -0.18, 0.84, r=0.02, h=0.28, segs=6, mat_idx=mats["wood_ash"])
    add_cylinder(bm, 0.28, -0.18, 0.98, r=0.065, h=0.14, segs=8, mat_idx=mats["wood_ash"])

def build_char_woodcutter(bm, mats):
    """Woodcutter with dark hooded cowl, felling wedges, broad axe & boots."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["wool_grey"], 
                        hose_mat=mats["wool_brown"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin_tan"],
                        tunic_w=0.52)
    # Dark woolen hooded cowl covering shoulders
    add_coif_or_hood(bm, mats["wool_brown"])

    # Felling wedges hanging at belt
    add_box(bm, 0.22, -0.15, 0.76, 0.05, 0.04, 0.14, mat_idx=mats["wood_ash"])
    add_box(bm, 0.26, -0.14, 0.76, 0.05, 0.04, 0.14, mat_idx=mats["wood_ash"])

    # Two-handed heavy broad felling axe
    add_oriented_cylinder(bm, (0.28, -0.15, 0.10), (0.28, -0.15, 1.25), radius=0.026, segs=6, mat_idx=mats["wood_ash"])
    add_box(bm, 0.28, -0.26, 1.15, 0.04, 0.22, 0.20, mat_idx=mats["iron_steel"])

def build_char_friar(bm, mats):
    """Dominican Friar with white habit, dark brown scapular, rope cincture, hoe & herb basket."""
    # Full-length ankle robe
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["linen_white"], 
                        hose_mat=mats["linen_white"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin"],
                        skirt_len=0.75, skirt_flare=0.62)
    # Dark brown monastic scapular (front and back hanging cloth)
    add_box(bm, 0, -0.15, 0.95, 0.32, 0.03, 0.90, mat_idx=mats["wool_brown"])
    add_box(bm, 0, 0.15, 0.95, 0.32, 0.03, 0.90, mat_idx=mats["wool_brown"])
    # Scapular hood resting on back of neck
    add_box(bm, 0, 0.12, 1.45, 0.34, 0.18, 0.22, mat_idx=mats["wool_brown"])

    # Knotted white rope cincture cord
    add_box(bm, 0, 0, 0.85, 0.48, 0.30, 0.05, mat_idx=mats["linen_white"])
    # Hanging cord with rosary beads
    add_cylinder(bm, 0.18, -0.14, 0.65, r=0.015, h=0.35, segs=4, mat_idx=mats["linen_white"])

    # Tonsure hair ring
    add_cylinder(bm, 0, 0, 1.64, r=0.15, h=0.06, segs=8, mat_idx=mats["hair_brown"])

    # Left hand: Wicker herb basket with sage & lavender cuttings
    add_box(bm, -0.32, -0.18, 0.72, 0.22, 0.16, 0.14, mat_idx=mats["wicker"])
    add_box(bm, -0.32, -0.18, 0.80, 0.20, 0.14, 0.06, mat_idx=mats["herb_green"]) # herbs
    # Basket arch handle
    add_box(bm, -0.32, -0.18, 0.84, 0.02, 0.16, 0.14, mat_idx=mats["wicker"])

    # Right hand: Wooden garden hand-hoe
    add_oriented_cylinder(bm, (0.30, -0.15, 0.10), (0.30, -0.15, 1.35), radius=0.02, segs=6, mat_idx=mats["wood_ash"])
    add_box(bm, 0.30, -0.22, 1.32, 0.12, 0.12, 0.03, mat_idx=mats["iron_steel"])

def build_char_guard(bm, mats):
    """Town Guard with sallet/kettle helmet, gambeson, red city heraldic tabard, halberd & sword."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["linen_white"], 
                        hose_mat=mats["wool_grey"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin"])
    # Quilted padded gambeson collar & sleeves
    add_box(bm, 0, 0, 1.25, 0.52, 0.32, 0.30, mat_idx=mats["linen_white"])

    # Dark red heraldic city tabard
    add_box(bm, 0, -0.16, 0.95, 0.38, 0.03, 0.75, mat_idx=mats["wool_red"])
    add_box(bm, 0, 0.16, 0.95, 0.38, 0.03, 0.75, mat_idx=mats["wool_red"])
    # Gold castle gate emblem on tabard chest
    add_box(bm, 0, -0.18, 1.15, 0.16, 0.02, 0.16, mat_idx=mats["gold_trim"])

    # Chainmail coif
    add_box(bm, 0, 0.02, 1.56, 0.30, 0.28, 0.24, mat_idx=mats["iron_dark"])

    # Polished steel kettle hat / sallet helmet
    add_cylinder(bm, 0, 0, 1.68, r=0.18, h=0.12, segs=8, mat_idx=mats["iron_steel"])
    # Broad protective helmet brim
    add_cylinder(bm, 0, 0, 1.63, r=0.26, h=0.035, segs=8, mat_idx=mats["iron_steel"])

    # Steel plate pauldrons / shoulder armor
    add_box(bm, -0.26, 0, 1.34, 0.10, 0.14, 0.08, mat_idx=mats["iron_steel"])
    add_box(bm, 0.26, 0, 1.34, 0.10, 0.14, 0.08, mat_idx=mats["iron_steel"])

    # Short arming sword in scabbard at left hip
    add_oriented_cylinder(bm, (-0.22, 0.02, 0.85), (-0.32, 0.12, 0.35), radius=0.03, segs=4, mat_idx=mats["leather_dark"])
    add_box(bm, -0.20, 0.0, 0.88, 0.12, 0.03, 0.04, mat_idx=mats["iron_steel"]) # crossguard

    # Right hand: Tall 2.2m steel polearm halberd
    # Ash wood shaft
    add_cylinder(bm, 0.32, -0.20, 1.10, r=0.022, h=2.20, segs=6, mat_idx=mats["wood_ash"])
    # Steel halberd axe head, spear spike, and rear hook
    add_box(bm, 0.32, -0.28, 2.05, 0.03, 0.18, 0.22, mat_idx=mats["iron_steel"]) # crescent axe
    add_box(bm, 0.32, -0.12, 2.05, 0.03, 0.10, 0.08, mat_idx=mats["iron_steel"]) # rear hook
    add_cone(bm, 0.32, -0.20, 2.28, r_bot=0.035, r_top=0.002, h=0.25, segs=4, mat_idx=mats["iron_steel"]) # top spear spike

def build_char_merchant(bm, mats):
    """Patrician Merchant with royal blue houppelande, fur collar, chaperon & scroll."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["wool_blue"], 
                        hose_mat=mats["wool_red"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin"],
                        skirt_len=0.70, skirt_flare=0.64)
    # Long flowing houppelande gown sleeves
    add_box(bm, -0.32, 0, 1.05, 0.16, 0.28, 0.45, mat_idx=mats["wool_blue"])
    add_box(bm, 0.32, 0, 1.05, 0.16, 0.28, 0.45, mat_idx=mats["wool_blue"])

    # Luxurious beaver fur collar trim around neck
    add_box(bm, 0, 0, 1.36, 0.52, 0.34, 0.12, mat_idx=mats["fur_brown"])

    # Padded chaperon hat with burgundy cockade
    add_cylinder(bm, 0, 0, 1.68, r=0.20, h=0.10, segs=8, mat_idx=mats["wool_red"])
    add_cylinder(bm, 0, 0, 1.74, r=0.24, h=0.08, segs=8, mat_idx=mats["wool_red"])
    add_oriented_cylinder(bm, (0.16, 0.08, 1.72), (0.22, 0.12, 1.35), radius=0.035, segs=6, mat_idx=mats["wool_red"])

    # Gold embroidered belt with embossed coin pouch
    add_box(bm, 0, 0, 0.85, 0.46, 0.28, 0.07, mat_idx=mats["wool_red"])
    add_box(bm, -0.20, -0.14, 0.74, 0.12, 0.08, 0.14, mat_idx=mats["leather_tan"])

    # Right hand: Official parchment scroll with red wax seal
    add_cylinder(bm, 0.26, -0.22, 0.88, r=0.04, h=0.22, segs=8, mat_idx=mats["linen_white"])
    add_cylinder(bm, 0.26, -0.26, 0.88, r=0.02, h=0.03, segs=6, mat_idx=mats["wool_red"]) # wax seal

def build_char_farmer(bm, mats):
    """Peasant Farmer with straw hat, loose linen shirt, rope belt, curved scythe."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["linen_white"], 
                        hose_mat=mats["wool_brown"], 
                        shoe_mat=mats["leather_tan"], 
                        skin_mat=mats["skin_tan"])
    # Broad-brimmed woven straw hat
    add_cylinder(bm, 0, 0, 1.68, r=0.18, h=0.12, segs=8, mat_idx=mats["straw_yellow"])
    add_cylinder(bm, 0, 0, 1.63, r=0.34, h=0.03, segs=10, mat_idx=mats["straw_yellow"])

    # Whetstone horn pouch at belt
    add_cone(bm, -0.18, -0.14, 0.72, r_bot=0.035, r_top=0.015, h=0.18, segs=6, mat_idx=mats["wood_dark"])

    # Held Prop: 1.8m curved harvest scythe with bent wooden snath
    add_oriented_cylinder(bm, (0.32, -0.15, 0.05), (0.32, -0.15, 1.75), radius=0.022, segs=6, mat_idx=mats["wood_ash"])
    # Handgrips (snath nibs)
    add_cylinder(bm, 0.32, -0.22, 0.95, r=0.015, h=0.10, segs=4, mat_idx=mats["wood_ash"])
    # Curved steel scythe blade
    add_box(bm, 0.15, -0.15, 1.75, 0.38, 0.03, 0.08, mat_idx=mats["iron_steel"])

def build_char_townswoman(bm, mats):
    """Burgher Townswoman with green kirtle, white apron, wimple veil & market basket."""
    build_humanoid_base(bm, mats, 
                        tunic_mat=mats["wool_green"], 
                        hose_mat=mats["wool_brown"], 
                        shoe_mat=mats["leather_dark"], 
                        skin_mat=mats["skin"],
                        tunic_w=0.44, tunic_d=0.26,
                        skirt_len=0.72, skirt_flare=0.62)
    # Crisp white linen front apron
    add_apron(bm, mats["linen_white"], w=0.36, h=0.68)

    # White linen wimple and veil covering neck and hair
    add_box(bm, 0, 0, 1.58, 0.28, 0.28, 0.26, mat_idx=mats["linen_white"])
    # Wimple chin band
    add_cylinder(bm, 0, 0, 1.45, r=0.12, h=0.14, segs=8, mat_idx=mats["linen_white"])
    # Veil draped down back of shoulders
    add_box(bm, 0, 0.12, 1.35, 0.34, 0.04, 0.40, mat_idx=mats["linen_white"])

    # Key ring hanging from belt
    add_cylinder(bm, -0.18, -0.14, 0.74, r=0.035, h=0.02, segs=6, mat_idx=mats["iron_steel"])

    # Left hand: Woven wicker market basket loaded with bread loaf and carrots
    add_box(bm, -0.32, -0.18, 0.70, 0.24, 0.18, 0.16, mat_idx=mats["wicker"])
    add_cylinder(bm, -0.32, -0.18, 0.79, r=0.07, h=0.06, segs=8, mat_idx=mats["bread_crust"]) # bread
    add_cone(bm, -0.26, -0.18, 0.81, r_bot=0.03, r_top=0.005, h=0.12, segs=4, mat_idx=mats["terracotta"]) # carrot

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

    def mat(self, key):
        """'slot:tunic' -> white Slot_tunic material; 'iron_steel' -> fixed palette material."""
        if key not in self.mat_idx:
            if key.startswith("slot:"):
                m = create_mat("Slot_" + key[5:], (1.0, 1.0, 1.0), roughness=0.85)
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
        "iron_steel": create_mat("CharIronSteel", (0.55, 0.56, 0.58), roughness=0.35, metallic=0.8),
        "iron_dark": create_mat("CharIronDark", (0.18, 0.18, 0.20), roughness=0.45, metallic=0.6),
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
                  ((0, 0, 1.35), 0.2, 0.125), ((0, 0, 1.42), 0.165, 0.1),
                  ((0, 0, 1.47), 0.075, 0.065)], segs=10, mat_idx=tun)
    add_tube(bm, [((0, 0, 0.95), 0.172, 0.122), ((0, 0, 1.0), 0.172, 0.122)], segs=10, mat_idx=belt)
    # Torso, female: fitted bodice, kirtle to the ankle.
    bm = kit.bm("body", "sex:f")
    add_tube(bm, [((0, 0.0, 0.07), 0.25, 0.22), ((0, 0, 0.55), 0.205, 0.17),
                  ((0, 0, 0.98), 0.15, 0.105), ((0, -0.005, 1.16), 0.165, 0.125),
                  ((0, 0, 1.33), 0.175, 0.11), ((0, 0, 1.42), 0.125, 0.085),
                  ((0, 0, 1.46), 0.07, 0.06)], segs=10, mat_idx=tun)
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
        sh = (sx * 0.205, 0.0, 1.40)
        el = (sx * 0.232, 0.01, 1.11)
        wr = (sx * 0.238, -0.05, 0.86)
        add_ellipsoid(bm, (sx * 0.195, 0.0, 1.375), (0.06, 0.066, 0.052), segs=8, rings=5, mat_idx=tun)
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
            for sx in (-1, 1):
                add_tube(bm, [((sx * 0.085, -0.03, 1.53), 0.012, 0.012), ((sx * 0.04, -0.07, 1.47), 0.012, 0.012),
                              ((0, -0.08, 1.46), 0.012, 0.012)], segs=5, mat_idx=m)
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
        elif key == "hat:kerchief":  # women: linen kerchief knotted at the nape
            m = kit.mat("slot:linen")
            add_ellipsoid(bm, (cx, cy + 0.012, cz + 0.012), (rx * 1.14, ry * 1.13, rz * 1.08), segs=12, rings=8,
                          mat_idx=m, keep=lambda x, y, z: (z > 0.15 and y > -0.75) or (y > 0.1 and z > -0.5))
            add_tube(bm, [((0, 0.11, 1.58), 0.03, 0.03), ((0, 0.135, 1.52), 0.04, 0.02)], segs=6, mat_idx=m)
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


def build_kit_tanner(kit):
    """Tanner: high greased boots, oiled leather apron, curved fleshing knife."""
    kit.anim = {"work": "scrape"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="boots", sleeves=("full", "rolled"), sleeve_w=(1, 3))
    kit.slot("tunic", [["#5f6346", 3, "pab"], ["#6b5d45", 3, "pab"], ["#555a4a", 2, "pab"]] + UNDYED + DYED[:3])
    kit.slot("hose", HOSE)
    kit.slot("boots", OILED)
    kit.slot("apron", OILED)
    kit.slot("hood", [["#4d4536", 2, "pab"], ["#3c3a33", 2, "pab"], ["#5c4a36", 1, "pab"]])
    kit.slot("cap", [["#4a3d2e", 2, "pab"], ["#3b3a35", 1, "pab"]])
    kit_heads(kit, {"hat:coif": (4, 1), "hat:cap": (2, 0), "hat:hood": (1, 0), "hat:bare": (2, 0),
                    "hat:kerchief": (0, 3), "hat:veil": (0, 2),
                    "hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (1, 0),
                    "beard:none": (2, 1), "beard:short": (3, 0), "beard:full": (2, 0), "beard:moustache": (1, 0)})
    kit.option("apron", "bib", 3, 3)
    kit.option("apron", "waist", 1, 2)
    kit_bib_apron(kit, "apron:bib", "apron")
    kit_bib_apron(kit, "apron:waist", "apron", bottom=0.36, waist_only=True)

    # Fleshing knife in the right hand: grip, curved blade, far handle.
    bm = kit.bm("arm_R")
    wd, st = kit.mat("wood_dark"), kit.mat("iron_steel")
    add_tube(bm, [((-0.24, 0.0, 0.80), 0.016, 0.016), ((-0.24, -0.12, 0.79), 0.016, 0.016)], segs=6, mat_idx=wd)
    add_tube(bm, [((-0.24, -0.12, 0.79), 0.005, 0.03), ((-0.24, -0.20, 0.75), 0.005, 0.034),
                  ((-0.24, -0.26, 0.65), 0.005, 0.032), ((-0.24, -0.28, 0.53), 0.005, 0.026)],
             segs=4, mat_idx=st, smooth=False)
    add_tube(bm, [((-0.24, -0.28, 0.53), 0.016, 0.016), ((-0.24, -0.29, 0.42), 0.016, 0.016)], segs=6, mat_idx=wd)
    # Belt pouch (optional) on the left hip.
    kit.option("pouch", "yes", 2, 2)
    kit.option("pouch", "no", 1, 1)
    for sex, (x, y) in {"m": (0.17, -0.06), "f": (0.15, -0.05)}.items():
        bm = kit.bm("body", f"pouch:yes+sex:{sex}")
        add_ellipsoid(bm, (x, y, 0.88), (0.035, 0.05, 0.065), segs=8, rings=5, mat_idx=kit.mat("leather_tan"))


def build_kit_blacksmith(kit):
    """Blacksmith: linen shirt, long leather apron, cross-peen hammer, tongs."""
    kit.anim = {"work": "hammer"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="shoes", sleeves=("full", "rolled"), sleeve_w=(1, 4))
    kit.slot("tunic", LINEN + [["#a39a86", 3, "pab"], ["#7d7668", 2, "pab"]] + UNDYED[:2])  # sooty linen
    kit.slot("hose", HOSE)
    kit.slot("apron", LEATHER + [["#5a3e26", 2, "pabr"]])
    kit.slot("cap", [["#3a2a1c", 2, "pab"], ["#4b4a46", 1, "pab"]])
    kit.slot("hood", [["#3c3a33", 1, "pab"]])
    kit_heads(kit, {"hat:bare": (3, 0), "hat:coif": (2, 1), "hat:cap": (3, 0),
                    "hat:kerchief": (0, 3), "hat:veil": (0, 1),
                    "hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (2, 0),
                    "beard:none": (1, 1), "beard:short": (3, 0), "beard:full": (3, 0), "beard:moustache": (1, 0)})
    kit.option("apron", "bib", 1, 1)
    kit_bib_apron(kit, "apron:bib", "apron", bottom=0.26, top=1.33)

    # Leather gloves (optional): thick mitten + cuff over each hand.
    kit.option("gloves", "yes", 1, 1)
    kit.option("gloves", "no", 2, 2)
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        bm = kit.bm(side, "gloves:yes")
        lt = kit.mat("leather_tan")
        add_ellipsoid(bm, (sx * 0.24, -0.065, 0.80), (0.036, 0.048, 0.064), segs=8, rings=5, mat_idx=lt)
        add_tube(bm, [((sx * 0.239, -0.055, 0.90), 0.05, 0.052), ((sx * 0.24, -0.06, 0.83), 0.045, 0.047)],
                 segs=8, mat_idx=lt)

    # Cross-peen hammer in the right fist: handle forward-down, head across its end.
    bm = kit.bm("arm_R")
    wa, ir = kit.mat("wood_ash"), kit.mat("iron_dark")
    a, b = Vector((-0.24, 0.02, 0.81)), Vector((-0.24, -0.25, 0.68))
    add_tube(bm, [(tuple(a), 0.014, 0.014), (tuple(b), 0.016, 0.016)], segs=6, mat_idx=wa)
    d = (b - a).normalized()
    perp = Vector((0, d.z, -d.y))   # in the YZ plane, square to the handle
    add_tube(bm, [(tuple(b - perp * 0.06), 0.024, 0.024), (tuple(b + perp * 0.075), 0.022, 0.018)],
             segs=4, mat_idx=ir, smooth=False)
    # Tongs in the left hand (optional).
    kit.option("tongs", "yes", 2, 2)
    kit.option("tongs", "no", 1, 1)
    bm = kit.bm("arm_L", "tongs:yes")
    for dx in (-0.012, 0.012):
        add_tube(bm, [((0.24 + dx, -0.03, 0.83), 0.007, 0.007), ((0.24 + dx * 0.4, -0.16, 0.66), 0.007, 0.007),
                      ((0.24 + dx * 1.4, -0.22, 0.52), 0.008, 0.008)], segs=4, mat_idx=ir, smooth=False)


KIT_BUILDERS = [
    ("char_tanner", build_kit_tanner),
    ("char_blacksmith", build_kit_blacksmith),
]


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

CHARACTER_BUILDERS = [
    ("char_baker", build_char_baker),
    ("char_tanner", build_char_tanner),
    ("char_carpenter", build_char_carpenter),
    ("char_blacksmith", build_char_blacksmith),
    ("char_brewer", build_char_brewer),
    ("char_potter", build_char_potter),
    ("char_weaver", build_char_weaver),
    ("char_stonemason", build_char_stonemason),
    ("char_woodcutter", build_char_woodcutter),
    ("char_friar", build_char_friar),
    ("char_guard", build_char_guard),
    ("char_merchant", build_char_merchant),
    ("char_farmer", build_char_farmer),
    ("char_townswoman", build_char_townswoman)
]

def export_character(obj, name):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"{name}.glb")
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True
    )
    sz = os.path.getsize(filepath)
    polycount = len(obj.data.polygons)
    print(f"Exported: {filepath} ({sz:,} bytes | {polycount} polygons)")

def main():
    print("=== Lublin Anno Domini 1392: Procedural 3D Character Pipeline ===")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    wanted = {a.removesuffix(".glb") for a in argv}
    mats_dict = get_materials()
    get_fixed_mats()
    # Sorted list of materials for index matching
    materials_list = list(mats_dict.values())
    mat_index_map = {name: i for i, name in enumerate(mats_dict.keys())}

    kit_names = {n for n, _ in KIT_BUILDERS}
    for name, builder in KIT_BUILDERS:
        if wanted and name not in wanted:
            continue
        kit = Kit(name)
        builder(kit)
        export_kit(kit)

    for idx, (name, builder) in enumerate(CHARACTER_BUILDERS, start=1):
        if name in kit_names or (wanted and name not in wanted):
            continue
        clear_scene()
        bm = bmesh.new()
        builder(bm, mat_index_map)
        bm.normal_update()

        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()

        for mat in materials_list:
            mesh.materials.append(mat)

        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        export_character(obj, name)

    print(f"\nDone: character models written to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
