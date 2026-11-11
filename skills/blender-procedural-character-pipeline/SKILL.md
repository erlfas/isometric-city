---
name: blender-procedural-character-pipeline
description: Procedural 3D humanoid character modeling, 3-view turnaround reference generation, historical costume and held tool prop authoring, low-poly GLTF/GLB export, and deterministic individualization jitter for Three.js and WebGL RTS simulations.
---
# Headless Blender Procedural 3D Character Pipeline Guide

This skill specifies the complete, reproducible process for concepting, modeling, texturing, exporting, and integrating procedural 3D humanoid characters and historical craftspeople into WebGL and Three.js isometric simulations.

---

## 1. Aesthetic Directives & Humanoid Proportions

### The Strategy Game Readability Standard
In isometric city builders and RTS simulations (*Stronghold*, *Knights and Merchants*, *Patrician III*), characters are viewed from elevated camera angles at distances of $15\text{m} - 80\text{m}$.
- **Scale:** $1.75\text{m}$ overall height (Blender Z-up: $Z \in [0.0\text{m}, 1.75\text{m}]$).
- **Proportions:** $1:6.5$ head-to-body ratio (slightly exaggerated head and shoulders) to ensure facial features, headgear, and held tools remain immediately distinguishable from high vantage points.
- **Polygon Budget:** $140 - 220$ polygons ($280 - 450$ triangles) per character model. Keeps file sizes under $30\text{ KB}$ per `.glb` and allows hundreds of active citizens on screen at 60 FPS.

```
  Height (Z-Up)  Anatomical Feature          Key Equipment & Clothing
  1.75m +-------- Headwear Apex              Linen cap, chaperon roll, straw hat, or kettle helmet
  1.50m +-------- Head & Face (Radius 0.14m) Eyeballs, beard, nose profile, linen coif
  1.40m +-------- Neck & Collar              Gambeson collar, scapular cowl, or kirtle chemise
  0.85m +-------- Torso (Width 0.48m)        Woolen tunic, bib apron, waist belt with buckle
  0.75m +-------- Waist & Belt               Mallet, wedges, keys, coin purse, whetstone pouch
  0.16m +-------- Legs / Chausses            Woolen hose / loose trousers
  0.00m +-------- Feet & Footwear            Leather turnshoes, high water boots, or moccasins
```

---

## 2. Orthographic 3-View Turnaround Reference Standard

### Single-Canvas Prompt Formula
To eliminate AI hallucination and costume drift across camera angles, always generate **Front, Side Profile, and Rear views side-by-side on a single 16:9 canvas**:

```text
Orthographic 3-view character model sheet showing front view, side profile view, and rear view side-by-side,
14th-century medieval [CHARACTER ARCHETYPE / CRAFT],
wearing [PRIMARY HISTORICAL GARMENTS: tunic, cotte, kirtle, or habit],
[SPECIALIZED WORK GEAR: layered apron, harness straps, belt with pouch],
[DISTINCT HEADWEAR: linen coif, barett cap, chaperon with liripipe, straw hat, cowl, or kettle helmet],
holding [CHARACTERISTIC CRAFT TOOL / HELD PROP: bread peel, fleshing knife, block plane, axe, hammer, paddle, scythe, halberd],
neutral solid beige parchment background, crisp silhouette, studio lighting,
late 1990s PC strategy game sprite reference, no modern elements, no UI
```

### Staging Hierarchy
Save all character model sheets to `reference_photos/workers/worker_[id]_turnaround.jpg`.

---

## 3. Procedural Bmesh Humanoid Authoring (`bpy` + `bmesh`)

### Base Humanoid Recipe
```python
import math
import bmesh
from mathutils import Vector

def build_humanoid_base(bm, mats, 
                        tunic_mat, hose_mat, shoe_mat, skin_mat,
                        tunic_w=0.48, tunic_d=0.28, tunic_h=0.55,
                        has_skirt=True, skirt_len=0.35, skirt_flare=0.56,
                        head_scale=1.0):
    """
    Constructs the standard 1.75m low-poly humanoid armature:
    - Shoes: Z in [0.0, 0.16]
    - Legs (Chausses): Z in [0.16, 0.85]
    - Torso & Tunic: Z in [0.85, 1.40]
    - Neck: Z in [1.40, 1.46]
    - Head & Face: Z in [1.46, 1.70]
    - Posed arms in working / resting posture
    """
    # 1. Shoes
    add_box(bm, -0.12, -0.04, 0.08, 0.14, 0.26, 0.16, mat_idx=shoe_mat)
    add_box(bm, 0.12, -0.04, 0.08, 0.14, 0.26, 0.16, mat_idx=shoe_mat)

    # 2. Legs
    add_cylinder(bm, -0.12, 0.0, 0.48, r=0.085, h=0.64, segs=6, mat_idx=hose_mat)
    add_cylinder(bm, 0.12, 0.0, 0.48, r=0.085, h=0.64, segs=6, mat_idx=hose_mat)

    # 3. Torso
    torso_cz = 0.85 + tunic_h * 0.5
    add_tapered_box(bm, 0, 0, torso_cz, 
                    w_bot=tunic_w * 0.9, d_bot=tunic_d * 0.9, 
                    w_top=tunic_w, d_top=tunic_d, 
                    h=tunic_h, mat_idx=tunic_mat)

    # Lower Tunic Skirt
    if has_skirt:
        skirt_cz = 0.85 - skirt_len * 0.5
        add_tapered_box(bm, 0, 0, skirt_cz,
                        w_bot=skirt_flare, d_bot=tunic_d * 1.25,
                        w_top=tunic_w * 0.92, d_top=tunic_d * 0.92,
                        h=skirt_len, mat_idx=tunic_mat)

    # 4. Belt & Buckle
    add_box(bm, 0, 0, 0.85, tunic_w * 0.95, tunic_d * 0.95, 0.07, mat_idx=mats["leather_dark"])
    add_box(bm, 0, -tunic_d * 0.48, 0.85, 0.08, 0.03, 0.08, mat_idx=mats["iron_steel"])

    # 5. Neck & Head
    add_cylinder(bm, 0, 0, 1.42, r=0.065, h=0.08, segs=6, mat_idx=skin_mat)
    head_r = 0.14 * head_scale
    add_box(bm, 0, 0, 1.57, head_r * 1.9, head_r * 2.0, head_r * 2.1, mat_idx=skin_mat)
    add_box(bm, 0, -head_r * 1.05, 1.57, 0.04, 0.05, 0.07, mat_idx=skin_mat) # nose

    # 6. Arms (Offhand Left & Dominant Right)
    add_oriented_cylinder(bm, (-tunic_w * 0.5, 0, 1.35), (-tunic_w * 0.55 - 0.06, 0.02, 1.05), radius=0.075, segs=6, mat_idx=tunic_mat)
    add_oriented_cylinder(bm, (-tunic_w * 0.55 - 0.06, 0.02, 1.05), (-0.30, -0.15, 0.88), radius=0.065, segs=6, mat_idx=skin_mat)

    add_oriented_cylinder(bm, (tunic_w * 0.5, 0, 1.35), (tunic_w * 0.55 + 0.06, 0.02, 1.05), radius=0.075, segs=6, mat_idx=tunic_mat)
    add_oriented_cylinder(bm, (tunic_w * 0.55 + 0.06, 0.02, 1.05), (0.30, -0.15, 0.88), radius=0.065, segs=6, mat_idx=skin_mat)
```

### Layered Work Aprons & Straps
```python
def add_apron(bm, mat_apron, w=0.34, h=0.75, bib_w=0.26, bib_h=0.32):
    """Adds a realistic layered bib apron over the chest and legs with forward depth offsets."""
    add_box(bm, 0, -0.145, 1.20, bib_w, 0.03, bib_h, mat_idx=mat_apron)
    add_box(bm, 0, -0.155, 0.72, w, 0.03, h, mat_idx=mat_apron)
    add_box(bm, 0, 0, 1.36, bib_w * 0.9, 0.26, 0.03, mat_idx=mat_apron)
```

---

## 4. Headless Batch Compilation & GLB Export

```python
import os
import bpy

OUTPUT_DIR = "public/models/characters"

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
    print(f"Exported: {filepath} ({os.path.getsize(filepath):,} bytes)")
```

Execute headless via CLI:
```bash
/home/antigravity/blender/blender --background --python build_characters.py
```

---

## 5. Three.js Engine Integration & Anti-Cloning Engine

### Two-Tier Archetype Dispatch
```ts
private getCitizenArchetype(c: Citizen): string {
  const trade = (c.trade || '').toLowerCase();
  const wealth = c.wealthClass || '';

  if (trade.includes('baker')) return 'char_baker';
  if (trade.includes('tanner') || trade.includes('shoemaker')) return 'char_tanner';
  if (trade.includes('carpenter') || trade.includes('joiner')) return 'char_carpenter';
  if (trade.includes('blacksmith') || trade.includes('armorer')) return 'char_blacksmith';
  if (trade.includes('brewer') || trade.includes('cooper')) return 'char_brewer';
  if (trade.includes('potter')) return 'char_potter';
  if (trade.includes('weaver') || trade.includes('tailor')) return 'char_weaver';
  if (trade.includes('stone') || trade.includes('mason')) return 'char_stonemason';
  if (trade.includes('wood') || trade.includes('sawyer')) return 'char_woodcutter';
  if (trade.includes('friar') || trade.includes('monk')) return 'char_friar';
  if (trade.includes('guard') || trade.includes('halberd')) return 'char_guard';
  if (wealth === 'patrician' || trade.includes('merchant')) return 'char_merchant';
  if (c.gender === 'female') return 'char_townswoman';
  return 'char_farmer';
}
```

### Deterministic Micro-Variation (Anti-Cloning)
Avoid cloning by hashing each citizen's unique `id`:
```ts
let seed = 0;
for (let j = 0; j < c.id.length; j++) {
  seed = (seed * 31 + c.id.charCodeAt(j)) >>> 0;
}

// Proportional jitter: height and girth
const heightJitter = 1.0 + ((seed % 13) - 6) * 0.012; // 0.93x - 1.07x
const girthJitter = 1.0 + (((seed * 7) % 13) - 6) * 0.012; // 0.93x - 1.07x
clone.scale.set(girthJitter, heightJitter, girthJitter);
```

### Dynamic Locomotion & Workstation Tasks
```ts
if (c.isMoving) {
  const dx = (c.targetX ?? cx) - cx;
  const dz = (c.targetZ ?? cz) - cz;
  if (Math.abs(dx) > 0.01 || Math.abs(dz) > 0.01) {
    const targetAngle = Math.atan2(dx, dz);
    let diff = targetAngle - group.rotation.y;
    while (diff < -Math.PI) diff += Math.PI * 2;
    while (diff > Math.PI) diff -= Math.PI * 2;
    group.rotation.y += diff * Math.min(1.0, _dt * 12.0);
  }
  const walkCycle = (c.animFrame ?? 0) * Math.PI;
  group.position.y = Math.abs(Math.sin(walkCycle)) * 0.07;
  group.rotation.z = Math.sin(walkCycle) * 0.035;
} else {
  const seedOffset = (group.userData?.seed || 0) % 100;
  group.position.y = Math.sin(nowSec * 2.2 + seedOffset) * 0.015;
}
```
