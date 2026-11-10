---
name: blender-procedural-asset-pipeline
description: Comprehensive procedural 3D modeling, headless CLI automation, bmesh geometry authoring, PBR material assignment, and GLTF/GLB export pipeline using Blender Python (bpy).
---
# Headless Blender Procedural 3D Asset Pipeline Guide

This guide provides drop-in idioms, architectural patterns, and troubleshooting techniques for procedural 3D modeling, headless CLI automation, and low-poly GLTF/GLB asset generation using Blender Python (`bpy` and `bmesh`).

---

## 1. Headless Execution & CLI Architecture

### Running Blender Headless in Cloud & CI Environments
Execute Blender without a display server or window manager using `--background`:

```bash
blender --background --python build_assets.py -- --out public/models --format glb
```

### Passing Custom CLI Arguments
Arguments placed after `--` are ignored by Blender and passed directly to Python:

```python
import sys
import argparse

def parse_cli_args():
    # Only parse arguments after '--'
    cli_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Headless Blender Asset Pipeline")
    parser.add_argument("--out", default="public/models", help="Output directory")
    parser.add_argument("--format", default="glb", choices=["glb", "gltf"], help="Export format")
    return parser.parse_args(cli_args)
```

### Portable Blender Installation in Non-Root Containers
When running in containers without `sudo`/`apt`:
1. Download official portable Linux tarball: `curl -L https://download.blender.org/release/Blender3.6/blender-3.6.18-linux-x64.tar.xz -o /tmp/blender.tar.xz`
2. Extract to user directory: `tar -xJf /tmp/blender.tar.xz -C $HOME && mv $HOME/blender-3.6.* $HOME/blender`
3. Symlink to PATH: `ln -sf $HOME/blender/blender $HOME/.local/bin/blender`

---

## 2. Memory & Material RNA Retention

### ❌ Critical Anti-Pattern: `read_factory_settings`
Calling `bpy.ops.wm.read_factory_settings(use_empty=True)` between asset builds wipes all cached `bpy.data.materials`. Reusing material references afterwards throws:
`ReferenceError: StructRNA of type Material has been removed`

### ✅ Robust Scene Pruning Idiom
Clear objects and meshes explicitly while keeping materials intact:

```python
import bpy

def clear_scene_objects():
    """Removes all objects and mesh data blocks without clearing materials."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)
```

---

## 3. PBR Materials & Shader Node Configuration

Create reusable Principled BSDF materials programmatically:

```python
def get_or_create_material(name, base_color_rgb, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            rgba = (*base_color_rgb[:3], 1.0) if len(base_color_rgb) == 3 else base_color_rgb
            bsdf.inputs["Base Color"].default_value = rgba
            bsdf.inputs["Roughness"].default_value = roughness
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = metallic
    return mat
```

---

## 4. Procedural Bmesh Geometry Generators

### Clean Bmesh Lifecycle
Always construct geometry in `bmesh`, compute outward normals, transfer to a mesh datablock, and free memory:

```python
import bmesh
from mathutils import Vector

def create_model_mesh(mesh_name, builder_func, materials):
    bm = bmesh.new()
    builder_func(bm)
    bm.normal_update()

    mesh = bpy.data.meshes.new(mesh_name)
    bm.to_mesh(mesh)
    bm.free()

    for mat in materials:
        mesh.materials.append(mat)

    obj = bpy.data.objects.new(mesh_name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj
```

### Outward Normal Winding Order (Counter-Clockwise in Z-Up)
Ensure outward-facing faces in Blender Z-up coordinate space:

```python
def add_oriented_box(bm, cx, cy, cz, w, d, h, mat_idx=0):
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
        bm.faces.new([v0, v3, v2, v1]), # -Z (bottom)
        bm.faces.new([v4, v5, v6, v7]), # +Z (top)
        bm.faces.new([v0, v1, v5, v4]), # -Y (front)
        bm.faces.new([v2, v3, v7, v6]), # +Y (back)
        bm.faces.new([v0, v4, v7, v3]), # -X (left)
        bm.faces.new([v1, v2, v6, v5]), # +X (right)
    ]
    for f in faces:
        f.material_index = mat_idx
    return faces
```

### High-Pitched Medieval Sloped Roof
```python
def add_sloped_roof(bm, cx, cy, z_base, w, d, h, overhang=0.3, mat_idx=0):
    w2, d2 = w * 0.5 + overhang, d * 0.5 + overhang
    v0 = bm.verts.new(Vector((cx - w2, cy - d2, z_base)))
    v1 = bm.verts.new(Vector((cx + w2, cy - d2, z_base)))
    v2 = bm.verts.new(Vector((cx + w2, cy + d2, z_base)))
    v3 = bm.verts.new(Vector((cx - w2, cy + d2, z_base)))
    r0 = bm.verts.new(Vector((cx, cy - d2, z_base + h)))
    r1 = bm.verts.new(Vector((cx, cy + d2, z_base + h)))

    faces = [
        bm.faces.new([v0, r0, r1, v3]), # left slope
        bm.faces.new([v1, v2, r1, r0]), # right slope
        bm.faces.new([v0, v1, r0]),     # front gable
        bm.faces.new([v2, v3, r1])      # back gable
    ]
    for f in faces:
        f.material_index = mat_idx
```

### Crow-Stepped Gables (*Szczyt Schodkowy*)
```python
def add_stepped_gable(bm, x_face, cy, z_base, depth, steps=5, step_h=1.2, mat_idx=0):
    for s in range(steps):
        sw = depth - s * (depth / steps * 0.8)
        sz = z_base + s * step_h
        add_oriented_box(bm, x_face, cy, sz + step_h * 0.5, 0.5, sw, step_h, mat_idx=mat_idx)
```

### Spoked Wheels & Rotational Polygonal Hubs
```python
import math

def add_spoked_wheel(bm, wx, wy, wz, radius=0.6, segments=8, mat_rim=0, mat_spoke=1):
    for i in range(segments):
        a1 = (i / segments) * math.pi * 2
        a2 = ((i + 1) / segments) * math.pi * 2
        y1, z1 = wy + math.cos(a1) * radius, wz + math.sin(a1) * radius
        y2, z2 = wy + math.cos(a2) * radius, wz + math.sin(a2) * radius
        seg_len = math.hypot(y2 - y1, z2 - z1)
        add_oriented_box(bm, wx, (y1 + y2) * 0.5, (z1 + z2) * 0.5, 0.08, seg_len, 0.08, mat_idx=mat_rim)
    # Center hub and cross spokes
    add_oriented_box(bm, wx, wy, wz, 0.16, 0.2, 0.2, mat_idx=mat_rim)
    add_oriented_box(bm, wx, wy, wz, 0.06, radius * 1.8, 0.06, mat_idx=mat_spoke)
    add_oriented_box(bm, wx, wy, wz, 0.06, 0.06, radius * 1.8, mat_idx=mat_spoke)
```

---

## 5. glTF / GLB Export Operator Configuration

Export single active objects cleanly with applied transforms and Draco compression:

```python
import os

def export_active_object_as_glb(obj, output_dir, filename_without_ext):
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{filename_without_ext}.glb")

    # Select only the target object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True, # Transforms Blender Z-up to glTF/WebGL Y-up
        export_materials='EXPORT',
        export_colors=True
    )
    print(f"[BlenderPipeline] Exported: {filepath} ({os.path.getsize(filepath):,} bytes)")
```

---

## 6. Automated Pipeline Verification Script

Run this validation script in CI/CD to verify that all assets were exported properly:

```python
import os
import glob

def verify_exported_assets(models_dir):
    glbs = glob.glob(os.path.join(models_dir, "*.glb"))
    assert len(glbs) > 0, "No GLB files found in output directory!"
    for path in glbs:
        size = os.path.getsize(path)
        assert size > 1024, f"Model {path} is suspiciously small ({size} bytes)!"
        print(f"Verified: {os.path.basename(path)} ({size:,} bytes)")
    print(f"All {len(glbs)} assets passed verification!")
```

---

## 7. Translating Multi-Angle Reference Images to Bmesh Coordinates

When constructing geometry from an architectural 3-view set (`front.jpg`, `side.jpg`, `back.jpg`) or character turnaround (`*_turnaround.jpg`):

### 1. Architectural Coordinate Extraction (Blender Z-Up)
- **Front View ($X \times Z$ Plane):**
  - Defines parcel width $W$ along $X \in [-W/2, W/2]$.
  - Defines story heights: Plinth $Z \in [0, H_0]$, First floor $Z \in [H_0, H_1]$, Jetty overhang $\Delta X = 0.25\text{m}$.
  - Positions street entrance doors and hung guild signs.
- **Side Profile View ($Y \times Z$ Plane):**
  - Defines building depth $D$ along $Y \in [-D/2, D/2]$.
  - Defines true roof gable pitch: $\theta = \arctan(H_{\text{roof}} / (D / 2))$. For Central European Brick Gothic, target $50^\circ - 60^\circ$.
  - Positions side flumes, mill waterwheels, lean-to roofs, and chimney stack projection along $Y$.
- **Rear View Yard Props ($X \times Y$ Footprints at $Z = 0$):**
  - Outdoor bake ovens: $Y_{\text{center}} = -D/2 - 1.2\text{m}$, radius $= 1.1\text{m}$.
  - Smelting furnaces & coal bunkers: Placed in rear corners with $X \in [W/4, W/2]$, $Y \in [-D/2 - 1.5, -D/2]$.
  - Tanning vats: Sunken negative Z coordinates or low rim boxes at $Z \in [0, 0.35\text{m}]$ behind the main cabin.

### 2. Character Model Turnaround Proportions
For 3-view worker turnaround sheets (`worker_*_turnaround.jpg`), map the 3 views to standardized proportional heights:
- **Total Height ($H_{\text{total}} \approx 1.75\text{m}$):**
  - Head & Headwear: $Z \in [1.50\text{m}, 1.75\text{m}]$ (Diameter $\approx 0.25\text{m}$)
  - Torso & Apron: $Z \in [0.85\text{m}, 1.50\text{m}]$ (Chest width $X \approx 0.45\text{m}$, depth $Y \approx 0.28\text{m}$)
  - Legs & Chausses: $Z \in [0.15\text{m}, 0.85\text{m}]$
  - Sturdy Work Boots: $Z \in [0.00\text{m}, 0.15\text{m}]$
- **Tool Attachment Offsets:**
  - Dominant hand (Right): $X = +0.35\text{m}$, $Y = +0.10\text{m}$, $Z = 0.85\text{m}$ (e.g. Forging hammer, bread peel, fleshing knife).
  - Offhand (Left): $X = -0.35\text{m}$, $Y = +0.10\text{m}$, $Z = 0.85\text{m}$ (e.g. Iron tongs, flour sack, skin clamp).
