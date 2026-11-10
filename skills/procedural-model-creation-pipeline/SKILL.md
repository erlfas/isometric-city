---
name: procedural-model-creation-pipeline
description: End-to-end process and best practices for creating, improving, and compiling procedural 3D models using headless Blender (bpy + bmesh), AI reference image generation, master markdown/JSON catalog authoring, and GLTF/GLB web runtime integration.
---
# Procedural 3D Model Creation Pipeline Guide

This skill specifies the complete, reproducible process for concepting, specifying, modeling, improving, and exporting procedural 3D architectural assets and craft workspaces for real-time web simulations and isometric city builders.

---

## 1. End-to-End Pipeline Architecture

The model creation pipeline flows through 6 distinct stages:

```
+----------------------------------------------------------------------------------------------------+
|                                    MODEL CREATION PIPELINE WORKFLOW                                |
+-----------------------+----------------------+--------------------+--------------------+-----------+
| 1. Concept Analysis   | 2. Master Catalog    | 3. Blender Python  | 4. Batch Export    | 5. Engine |
|    & Reference Staging|    Specification     |    bmesh Authoring |    to Single Folder|    Bind   |
| (reference_photos/)   | (Markdown + JSON)    | (bpy + bmesh)      | (public/models/)   | (Three.js)|
+-----------------------+----------------------+--------------------+--------------------+-----------+
```

---

## 2. Phase 1: Concept Analysis & Reference Photo Generation

### Deconstructing Concept Art
Before authoring procedural code, examine concept art to identify:
1. **Macro Architectural Structure**: Primary massing, story heights ($2.5\text{m} - 4.5\text{m}$ per floor), roof pitch ($45^\circ - 60^\circ$ for medieval Northern/Central Europe), foundation materials (limestone ashlar, fieldstone, timber pilings).
2. **Exterior Workspaces & Activity Stations**: In historical simulations, building interiors are rarely visible. Buildings must communicate their function through **outdoor equipment**:
   - *Baker*: Domed masonry oven, firewood cords, flour sacks, bread peel shovel, pretzel sign.
   - *Tanner*: Open drying lofts, sunken tanning vats, hide-stretching frames, fleshing beams.
   - *Brewer*: Malt ventilation louvers, cask-washing troughs, beer barrel pyramids, tavern tables.
   - *Blacksmith*: Projecting open forge canopy, hearth furnace with glowing embers, anvil on stump, quench trough.
   - *Potter*: Domed updraft kiln, potter's kick-wheel bench, drying shelves of amphorae/jugs.
   - *Weaver*: St. Andrew's cross braces, attic hoist, circular dye cauldrons, cloth drying rails.
   - *Watermill / Windmill*: Waterwheels, mill flumes, canvas sails, tail-poles.

### Generating Multi-Angle & 3-View Reference Images
To completely eliminate architectural ambiguity and production yard guesswork, author reference imagery using a disciplined **3-View Reference Methodology**:

#### 1. Architectural 3-View Elevation & Isometric Protocol
For every craft building or workshop, establish three distinct camera angles before authoring geometry:
- **Front Elevation / Primary Entrance:** Captures public street presence, stone portals, timber jetty overhangs, lintels, and craft guild signage.
- **Side Elevation / Profile:** Captures exact roof pitch ($45^\circ - 60^\circ$ for Central European Gothic), chimney stack projections, timber braces, and waterwheel or mill race alignments.
- **Rear Elevation / Production Yard:** Captures the functional industrial heart: sunken tanning vats, wood ricks, drying lofts, brick kilns, barrels, hoists, and storage outhouses.

Standard prompt formulas for each view:
```text
# 1. Front View / Street Elevation:
2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic,
front elevation view, street entrance of [BUILDING/WORKSHOP], timber-framed facade with guild sign,
Central European Brick Gothic, muted earthy colors, hard directional drop shadows, orthographic projection, no UI

# 2. Side Elevation / Flume & Gable Profile:
2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic,
side profile elevation view of [BUILDING/WORKSHOP], steep 50-degree gable roof, brick chimney stack,
Central European timber vernacular, muted earthy palette, orthographic projection, no UI

# 3. Rear Elevation / Outdoor Yard:
2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic,
rear yard view of [BUILDING/WORKSHOP], [OUTDOOR EQUIPMENT & WORKSPACES], timber fence,
stacked raw materials, muted earthy palette, hard directional drop shadows, orthographic projection, no UI
```

#### 2. Worker & Citizen 3-View Turnaround Sheets
For character models and animated craftspeople, **never generate 3 separate disconnected prompts** (which causes AI outfit and proportion drift). Instead, generate a **single unified 3-view turnaround character sheet**:

```text
Orthographic 3-view character model sheet showing front, profile side, and rear views side-by-side,
14th-century medieval [CRAFT WORKER / CITIZEN], historically accurate linen tunic, woolen chausses,
[SPECIALIZED APRON / WORK GEAR], holding [PRIMARY CRAFT TOOL], neutral solid parchment background,
crisp silhouette, studio lighting, late 1990s PC strategy game sprite reference, no UI
```

### Dedicated Reference Directory Hierarchy
Organize reference photos into clean, per-asset subdirectories in `reference_photos/` committed to the repository:
```bash
reference_photos/
├── baker_house/
│   ├── front.jpg
│   ├── side.jpg
│   └── back.jpg
├── blacksmith_workshop/
│   ├── front.jpg
│   ├── side.jpg
│   └── back.jpg
├── ...
└── workers/
    ├── worker_blacksmith_turnaround.jpg
    ├── worker_baker_turnaround.jpg
    └── ...
```

### Skill Storage vs. Project Repository Architecture
- **Skill Scope (`skills/procedural-model-creation-pipeline/`)**: Stores reusable procedural knowledge, automation scripts (`scripts/`), and golden benchmark templates (`assets/benchmark_workshop.glb`). It does not store all multi-megabyte project assets to prevent bloated skill packages.
- **Repository Scope**: The project repository stores the full asset collection:
  - `reference_photos/<model_id>/` for multi-view source imagery.
  - `public/models/*.glb` for all single-draw-call WebGL runtime assets.
  - `docs/` for master architectural catalogs and visual galleries.

---

## 3. Phase 2: Master Markdown & JSON Catalog Specification

Every 3D model must be documented in a master catalog (e.g. `BUILDINGS_AND_WORKERS_CATALOG.md` and companion JSON) before code authoring.

### Catalog Entry Template
```markdown
#### [Index]. [Building Name] (*[Historical Name]*)
- **ID:** `bldg_[archetype_id]`
- **Location:** [District placement context and coordinates]
- **Dimensions:** $[W]\text{m (W)} \times [D]\text{m (D)} \times [H]\text{m (Total H)}$.
- **Stories:** [Number of stories and specialized levels]
- **Architectural Motifs:** [Wall materials, framing style, roof type and pitch, guild signs]
- **Exterior Workspace / Station:**
  - **[Primary Machinery/Feature]:** [Dimensions, operational details, colors]
  - **[Secondary Workspace/Trough/Rack]:** [Dimensions, materials, props]
  - **Equipment & Props:** [Held tools, stacked raw materials, finished products]
- **Associated Workers:** `worker_[id]` ([Costume, held tools, looped animation cycle])
- **Blender Generator:** `build_[name]()` $\rightarrow$ `public/models/[name].glb`
- **Reference Image:** `reference_photos/[name].jpg`
```

---

## 4. Phase 3: Procedural Bmesh Geometry Authoring

### Memory Management & Material RNA Retention
**Critical Rule**: Never call `bpy.ops.wm.read_factory_settings(use_empty=True)` between asset builds in a batch script. Doing so destroys all cached material RNA pointers.

Use the explicit scene pruning idiom:
```python
import bpy

def clear_scene():
    """Removes all objects and mesh data blocks while retaining the materials dictionary."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)
```

### Reusable Global Material Palette
Define materials once with standard PBR inputs:
```python
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
```

### Essential Procedural Bmesh Primitives

#### 1. Outward-Facing Oriented Box (Counter-Clockwise in Z-Up)
```python
import bmesh
from mathutils import Vector

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
```

#### 2. Sloped Medieval Gable Roof
```python
def add_sloped_roof(bm, cx, cy, z_base, w, d, h, overhang=0.3, mat_idx=0):
    w2, d2 = w * 0.5 + overhang, d * 0.5 + overhang
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
```

#### 3. Low-Poly Polygonal Cylinder (Barrels, Towers, Vats)
```python
import math

def add_cylinder(bm, cx, cy, cz, radius, height, segs=12, mat_idx=0):
    h2 = height * 0.5
    bot_verts, top_verts = [], []
    for i in range(segs):
        ang = (i / segs) * math.pi * 2
        x = cx + math.cos(ang) * radius
        y = cy + math.sin(ang) * radius
        bot_verts.append(bm.verts.new(Vector((x, y, cz - h2))))
        top_verts.append(bm.verts.new(Vector((x, y, cz + h2))))

    for i in range(segs):
        nxt = (i + 1) % segs
        f = bm.faces.new([bot_verts[i], bot_verts[nxt], top_verts[nxt], top_verts[i]])
        f.material_index = mat_idx

    bm.faces.new(top_verts).material_index = mat_idx
    bm.faces.new(list(reversed(bot_verts))).material_index = mat_idx
```

---

## 5. Phase 4: Non-Destructive Model Improvement Protocol

When improving existing baseline models (e.g. `house_patrician_brick`, `house_half_timber`, `house_timber_log`, `town_hall`):

1. **Maintain Ground Origin**: Ensure origin remains at $(0, 0, 0)$ at ground level.
2. **Respect Footprint Bounds**: Auxiliary additions (dormers, chimneys, lean-tos) must fit the assigned parcel lot dimensions ($W \times D$).
3. **Additive Architectural Detail**:
   - *Gables*: Add multi-tier crow-stepped gables with pinnacles (*sterczyny*).
   - *Jetties*: Add cantilevered second-floor overhangs with carved wooden corbels.
   - *Street Interaction*: Add fold-down shop shutters, display sills, cellar bulkhead doors, and rain barrels.
   - *Vernacular Details*: Protruding saddle-notched corner logs (*wieńce*) and thatch roof cross-timbers (*kozły*).

---

## 6. Phase 5: Batch Compilation to Single Destination Folder

All models must export to a single unified destination directory (e.g. `public/models/*.glb`):

```python
import os

OUTPUT_DIR = "public/models"

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
```

### Execution Command
```bash
/home/antigravity/blender/blender --background --python build_assets.py
```

### Verification Script
```python
import glob, os

def verify_models(directory):
    glbs = glob.glob(os.path.join(directory, "*.glb"))
    assert len(glbs) >= 20, f"Expected >= 20 models, found {len(glbs)}"
    for g in glbs:
        sz = os.path.getsize(g)
        assert sz > 4096, f"Suspiciously small asset {g}: {sz} bytes"
    print(f"All {len(glbs)} models successfully verified!")
```

---

## 7. Phase 6: Runtime Engine Dynamic Dispatch (Three.js)

### Asynchronous Pre-loading & Shadow Setup
```ts
const loader = new GLTFLoader();
for (const name of modelNames) {
  const gltf = await loader.loadAsync(`/models/${name}.glb`);
  gltf.scene.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });
  this.models.set(name, gltf.scene);
}
```

### Two-Tier Dynamic Parcel Dispatch
Avoid visual cloning by querying craft ID first, then specialized building type, and falling back to district typology:

```ts
const craftId = parcel.craft?.id || '';
const bType = parcel.buildingType || '';

let tmpl: THREE.Group | undefined;
if (parcel.isShed) {
  tmpl = this.models.get('shed_timber');
} else if (craftId === 'baker' || bType.includes('baker')) {
  tmpl = this.models.get('house_baker');
} else if (craftId === 'tanner' || bType.includes('tanner')) {
  tmpl = this.models.get('house_tanner');
} else if (craftId === 'brewer' || bType.includes('brewer')) {
  tmpl = this.models.get('house_brewer');
} else if (craftId === 'blacksmith' || craftId === 'armorer') {
  tmpl = this.models.get('blacksmith_workshop');
} else if (craftId === 'potter') {
  tmpl = this.models.get('house_potter');
} else if (craftId === 'weaver' || craftId === 'tailor') {
  tmpl = this.models.get('house_weaver');
} else if (bType.includes('patrician')) {
  tmpl = this.models.get('house_patrician_brick');
} else if (bType.includes('log') || bType.includes('thatched')) {
  tmpl = this.models.get('house_timber_log');
} else {
  tmpl = this.models.get('house_half_timber');
}
```
