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

Exports all models as optimized GLTF/GLB models to public/models/characters/
"""

import os
import sys
import math

import bpy
import bmesh
from mathutils import Vector, Matrix, Color

OUTPUT_DIR = "public/models/characters"

def clear_scene():
    """Prunes scene objects and meshes while preserving materials in memory."""
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
    mats_dict = get_materials()
    # Sorted list of materials for index matching
    materials_list = list(mats_dict.values())
    mat_index_map = {name: i for i, name in enumerate(mats_dict.keys())}

    total_characters = len(CHARACTER_BUILDERS)
    for idx, (name, builder) in enumerate(CHARACTER_BUILDERS, start=1):
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

    print(f"\nSuccessfully compiled all {total_characters} character models into {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()
