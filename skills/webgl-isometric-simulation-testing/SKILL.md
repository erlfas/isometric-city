---
name: webgl-isometric-simulation-testing
description: Systematic testing, automated headless verification, and rendering quality audits for WebGL and Three.js isometric city simulations and Blender 3D procedural asset pipelines.
---
# WebGL & Isometric 3D Simulation Testing & Verification Guide

This skill provides a systematic test harness and verification methodology for real-time WebGL isometric games, Three.js city simulations, and headless Blender Python asset compilation pipelines.

---

## 1. Automated Headless Visual Verification Pipeline

Always verify browser rendering visually using headless Chromium before delivering graphics or simulation updates.

### Capturing Headless WebGL Screenshots
Execute Chromium in headless mode with software WebGL fallback and a virtual time budget to allow assets and shaders to load:

```bash
chromium --headless=new \
  --no-sandbox \
  --disable-gpu \
  --window-size=1280,720 \
  --virtual-time-budget=3000 \
  --screenshot=/tmp/render_verification.png \
  http://localhost:4173/
```

### Black Screen & Silhouette Detection Script
A common failure mode in custom WebGL shaders is backface culling or normal inversion, producing solid black rectangles or unlit silhouettes. Use this Python one-liner to verify that the rendered frame contains healthy visual contrast:

```bash
python3 -c "
import struct
with open('/tmp/render_verification.png', 'rb') as f:
    data = f.read()
size = len(data)
if size < 50000:
    print('FAIL: Screenshot file too small (blank/white frame)! Size:', size)
    exit(1)
else:
    print(f'PASS: Screenshot captured successfully ({size:,} bytes).')
"
```

---

## 2. Headless Blender (`bpy`) Asset Pipeline Verification

When compiling procedural 3D models via Blender Python CLI scripts, verify:

### 1. Scene Reset Without RNA Material Destruction
**Anti-Pattern:** Calling `bpy.ops.wm.read_factory_settings(use_empty=True)` destroys previously cached `bpy.data.materials`, resulting in `ReferenceError: StructRNA of type Material has been removed`.

**Correct Pattern:** Delete only objects and meshes while preserving materials in data blocks:
```python
def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)
```

### 2. GLB Export Integrity Check
Audit exported `.glb` files to ensure they exist, have non-zero file sizes, and contain valid geometry:
```bash
python3 -c "
import os, glob
glb_files = glob.glob('public/models/*.glb')
if not glb_files:
    print('FAIL: No GLB models found in public/models/')
    exit(1)
for path in glb_files:
    size = os.path.getsize(path)
    if size < 1024:
        print(f'FAIL: Model {path} is suspiciously small ({size} bytes)!')
        exit(1)
    print(f'PASS: {os.path.basename(path)} ({size:,} bytes)')
"
```

---

## 3. WebGL Isometric & Shadow Pipeline Checklist

Before completing an isometric rendering task, audit these core graphics settings:

1. **Orthographic Isometric Camera Setup**:
   - Ensure classic dimetric angle ($30^\circ$ pitch) or true isometric angle ($35.264^\circ$, where $\sin(\theta) = 1/\sqrt{3}$).
   - Verify camera updates on window resize:
     ```ts
     const aspect = canvas.clientWidth / canvas.clientHeight;
     camera.left = -zoom * aspect * 0.5;
     camera.right = zoom * aspect * 0.5;
     camera.top = zoom * 0.5;
     camera.bottom = -zoom * 0.5;
     camera.updateProjectionMatrix();
     ```
2. **Directional Shadow Map Configuration**:
   - `renderer.shadowMap.enabled = true` with `THREE.PCFSoftShadowMap`.
   - Set shadow camera bounds tightly to encompass the active view (e.g. $d = 140$).
   - Set `directionalLight.shadow.bias = -0.0003` to eliminate shadow acne while avoiding light detachment.
3. **Face Culling & Winding Order**:
   - In custom WebGL, verify quad vertex ordering is Counter-Clockwise (`gl.CCW`) when viewed from the outside:
     $$\vec{v}_0 \to \vec{v}_1 \to \vec{v}_2 \to \vec{v}_3$$
   - When building sloped roofs or gables, ensure normals point outward or disable backface culling during initial geometry debugging.

---

## 4. Simulation & Spatial Verification

1. **Parcellation Non-Repetition Audit**:
   - Verify that adjacent parcels along street fronts do not share identical building types:
     ```python
     for i in range(len(parcels) - 1):
         if parcels[i]['streetName'] == parcels[i+1]['streetName']:
             assert parcels[i]['buildingType'] != parcels[i+1]['buildingType'], f"Consecutive repeat at {parcels[i]['id']}"
     ```
2. **Spatial Hash Grid Bounds**:
   - Ensure spatial hash cell size ($24\text{m}$) evenly covers building dimensions ($8\text{m} - 18\text{m}$).
   - Check that `spatialGrid.findNearestCitizen()` or `findParcelAt()` returns valid entities on screen raycasts.
3. **Clockwork Schedule Integrity**:
   - Confirm that all 1,500 citizens have non-empty schedules covering canonical bell hours (Matins, Prime, Terce, Sext, Nones, Vespers, Compline, Curfew).
