"""Static checks on the exported GLB models and the texture bindings.

Stdlib only (runs on CI's python3 and on Blender's bundled python). Exit 1 on any failure.

  python scripts/check_models.py            # all checks
  python scripts/check_models.py -v         # also print per-model roof stats

Checks:
  1. Roofs face up: for each roof material, the area of upward-facing triangles must exceed
     the downward-facing area. Inward-wound roofs get back-face culled (KEY_FINDINGS §16).
  2. Textured materials have UVs: every primitive whose material is in BINDINGS has TEXCOORD_0.
  3. No node transforms: build_assets.py bakes transforms; this check assumes it.
  4. Bindings resolve: every BINDINGS key is a create_mat() name in build_assets.py, every
     family it names is in the manifest, and every manifest family is used (BINDINGS or a
     getAlbedo('...') call).
  5. Manifest files exist.
  6. Character kits: every mesh has a valid part, its variant names kit.groups options, every
     Slot_* material has a palette, triangle budgets hold, metallic <= KIT_MAX_METALLIC,
     variants per part and colour slots fit the crowd renderer's limits.
"""
import glob
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "public", "models")
TEXTURES = os.path.join(ROOT, "public", "textures")
TEXLIB = os.path.join(ROOT, "src", "engine", "texture-library.ts")
SRC = os.path.join(ROOT, "src")

ROOF_MATERIALS = {"RoofTileRed", "RoofShingle", "RoofThatch"}
COMP = {5126: ("f", 4), 5125: ("I", 4), 5123: ("H", 2), 5121: ("B", 1)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

errors = []
verbose = "-v" in sys.argv


def fail(msg):
    errors.append(msg)


def load_glb(path):
    data = open(path, "rb").read()
    if data[:4] != b"glTF":
        raise ValueError("not a GLB")
    jlen = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + jlen])
    bin_chunk = data[20 + jlen + 8:]
    return gltf, bin_chunk


def accessor(gltf, binary, idx):
    a = gltf["accessors"][idx]
    bv = gltf["bufferViews"][a["bufferView"]]
    fmt, size = COMP[a["componentType"]]
    n = NCOMP[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", size * n)
    count = a["count"]
    if stride == size * n:
        flat = struct.unpack_from(f"<{count * n}{fmt}", binary, start)
    else:
        flat = []
        for k in range(count):
            flat.extend(struct.unpack_from(f"<{n}{fmt}", binary, start + k * stride))
    return flat if n == 1 else [flat[i:i + n] for i in range(0, len(flat), n)]


def roof_areas(pos, idx):
    """(up_area, down_area) of a triangle list, glTF Y-up. A triangle that has an exact
    reverse-wound twin (deliberately two-sided geometry) counts as neither."""
    def key(t):
        return frozenset(tuple(round(c, 4) for c in pos[idx[t + k]]) for k in range(3))
    seen = {}
    for t in range(0, len(idx), 3):
        seen.setdefault(key(t), []).append(t)
    twins = set()
    for tris in seen.values():
        if len(tris) > 1:
            twins.update(tris)

    up = down = 0.0
    for t in range(0, len(idx), 3):
        if t in twins:
            continue
        ax, ay, az = pos[idx[t]]
        bx, by, bz = pos[idx[t + 1]]
        cx, cy, cz = pos[idx[t + 2]]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        area = 0.5 * (nx * nx + ny * ny + nz * nz) ** 0.5
        if area < 1e-9:
            continue
        cos = ny / (2 * area)
        if cos > 0.05:
            up += area
        elif cos < -0.05:
            down += area
    return up, down


KIT_PARTS = {"body", "head", "arm_L", "arm_R", "leg_L", "leg_R"}
KIT_BASE_TRIS = 1300      # always-drawn meshes of one kit
KIT_VARIANT_TRIS = 450    # any single variant mesh
KIT_MAX_METALLIC = 0.3    # no environment map: more metallic renders near black (KEY_FINDINGS §18.6)
KIT_MAX_VARIANTS = 48     # distinct variants per part: the crowd's per-instance mask (citizen-crowd.ts)
KIT_MAX_SLOTS = 31        # colour slots per kit: columns of the crowd's slot texture


def check_kit(name, gltf):
    """Character kits (build_characters.py export_kit): metadata matches the meshes."""
    scenes = gltf.get("scenes", [])
    raw = scenes[0].get("extras", {}).get("kit") if scenes else None
    if raw is None:
        return
    kit = json.loads(raw)
    groups, slots = kit.get("groups", {}), kit.get("slots", {})
    if set(kit.get("pivots", {})) != KIT_PARTS:
        fail(f"{name}: kit pivots {sorted(kit.get('pivots', {}))} != {sorted(KIT_PARTS)}")
    mats = gltf.get("materials", [])
    for m in mats:
        metal = m.get("pbrMetallicRoughness", {}).get("metallicFactor", 1.0)  # glTF default is 1
        if metal > KIT_MAX_METALLIC + 1e-3:  # exported as float32
            fail(f"{name}: material {m.get('name')} metallic {metal:.2f} > {KIT_MAX_METALLIC} (renders black)")
    if len(slots) > KIT_MAX_SLOTS:
        fail(f"{name}: {len(slots)} colour slots (max {KIT_MAX_SLOTS})")
    base = 0
    variants = {}
    for node in gltf.get("nodes", []):
        if "mesh" not in node:
            continue
        ex = node.get("extras", {})
        part, variant = ex.get("part"), ex.get("variant", "")
        if part not in KIT_PARTS:
            fail(f"{name}: node '{node.get('name')}' has no valid extras.part ({part})")
        for cond in filter(None, variant.split("+")):
            g, _, o = cond.partition(":")
            if o not in groups.get(g, {}):
                fail(f"{name}: node '{node.get('name')}' variant {cond} is not an option in kit.groups")
        tris = 0
        for prim in gltf["meshes"][node["mesh"]]["primitives"]:
            mname = mats[prim["material"]].get("name", "") if "material" in prim else ""
            if mname.startswith("Slot_") and mname[5:] not in slots:
                fail(f"{name}: material {mname} has no palette in kit.slots")
            acc = prim.get("indices", prim["attributes"]["POSITION"])
            tris += gltf["accessors"][acc]["count"] // 3
        if variant:
            variants.setdefault(part, set()).add(variant)
            if tris > KIT_VARIANT_TRIS:
                fail(f"{name}: variant mesh '{node.get('name')}' has {tris} tris (budget {KIT_VARIANT_TRIS})")
        else:
            base += tris
    for part, vs in variants.items():
        if len(vs) > KIT_MAX_VARIANTS:
            fail(f"{name}: part {part} has {len(vs)} variants (max {KIT_MAX_VARIANTS})")
    if base > KIT_BASE_TRIS:
        fail(f"{name}: kit base meshes have {base} tris (budget {KIT_BASE_TRIS})")
    for g, opts in groups.items():
        for o, w in opts.items():
            if len(w) != 2:
                fail(f"{name}: kit.groups.{g}.{o} weights must be [male, female]")


def parse_bindings():
    src = open(TEXLIB, encoding="utf-8").read()
    block = re.search(r"const BINDINGS[^{]*\{(.*?)\n\};", src, re.S)
    if not block:
        fail(f"{TEXLIB}: could not find the BINDINGS table")
        return {}
    out = {}
    for m in re.finditer(r"^\s*(\w+):\s*\{\s*families:\s*\[([^\]]*)\]", block.group(1), re.M):
        out[m.group(1)] = re.findall(r"'([^']+)'", m.group(2))
    return out


def main():
    bindings = parse_bindings()
    seen_materials = set()
    paths = sorted(glob.glob(os.path.join(MODELS, "*.glb")))
    if not paths:
        fail(f"no GLBs in {MODELS}")

    for path in paths:
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            gltf, binary = load_glb(path)
        except Exception as e:  # noqa: BLE001 - report and continue
            fail(f"{name}: unreadable GLB ({e})")
            continue

        for node in gltf.get("nodes", []):
            if any(k in node for k in ("matrix", "rotation", "scale", "translation")):
                fail(f"{name}: node '{node.get('name')}' has a transform; bake it in build_assets.py")

        mats = gltf.get("materials", [])
        seen_materials.update(m.get("name", "") for m in mats)
        check_kit(name, gltf)
        roof = {}
        for mesh in gltf.get("meshes", []):
            for prim in mesh["primitives"]:
                if "material" not in prim:
                    continue
                mname = mats[prim["material"]].get("name", "")
                if mname in bindings and "TEXCOORD_0" not in prim["attributes"]:
                    fail(f"{name}: textured material {mname} has no TEXCOORD_0 (add_world_uvs not run?)")
                if mname in ROOF_MATERIALS and prim.get("mode", 4) == 4:
                    pos = accessor(gltf, binary, prim["attributes"]["POSITION"])
                    idx = accessor(gltf, binary, prim["indices"]) if "indices" in prim else list(range(len(pos)))
                    u, d = roof_areas(pos, idx)
                    pu, pd = roof.get(mname, (0.0, 0.0))
                    roof[mname] = (pu + u, pd + d)
        for mname, (u, d) in roof.items():
            if verbose:
                print(f"  {name:28s} {mname:12s} up {u:8.1f} m2  down {d:8.1f} m2")
            if d > u:
                fail(f"{name}: {mname} faces mostly down (up {u:.1f} m2, down {d:.1f} m2) - roof wound inward")

    manifest_path = os.path.join(TEXTURES, "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8")) if os.path.exists(manifest_path) else {}
    if not manifest:
        fail(f"{manifest_path}: missing or empty")
    for fam, entry in manifest.items():
        for key in ("albedo", "normal"):
            if not os.path.exists(os.path.join(TEXTURES, entry.get(key, ""))):
                fail(f"manifest {fam}.{key}: file {entry.get(key)} missing")

    palette = set(re.findall(r'create_mat\(\s*"(\w+)"', open(os.path.join(ROOT, "build_assets.py"), encoding="utf-8").read()))
    used = set()
    for mat, fams in bindings.items():
        if mat not in palette:
            fail(f"BINDINGS.{mat}: build_assets.py defines no material with this name (create_mat)")
        elif mat not in seen_materials:
            print(f"  note: BINDINGS.{mat} is defined but no exported model uses it yet")
        for fam in fams:
            used.add(fam)
            if fam not in manifest:
                fail(f"BINDINGS.{mat}: family '{fam}' is not in manifest.json")
    for ts in glob.glob(os.path.join(SRC, "**", "*.ts"), recursive=True):
        used.update(re.findall(r"getAlbedo\(\s*'([^']+)'", open(ts, encoding="utf-8").read()))
    for fam in sorted(set(manifest) - used):
        fail(f"manifest family '{fam}' is never used (not in BINDINGS, no getAlbedo('{fam}'))")

    if errors:
        print(f"check_models: {len(errors)} problem(s)")
        for e in errors:
            print("  FAIL", e)
        return 1
    print(f"check_models: OK ({len(paths)} GLBs, {len(bindings)} bindings, {len(manifest)} texture families)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
