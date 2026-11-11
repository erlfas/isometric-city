"""
Texture build: turns picked hero sources + procedural recipes into runtime textures.

Run with Blender's bundled Python (has numpy):
  python -I scripts/textures/build_textures.py <src_bmp_dir> <out_bmp_dir> [--only hero|proc] [--family id]

Writes for each texture:  <id>_albedo.bmp, <id>_normal.bmp, <id>_preview.bmp
and <out>/manifest.json. scripts/textures/build_textures.ps1 converts the BMPs to
JPG in public/textures/ and copies the manifest.

Real-world scale: `tile_m` = metres covered by one texture repeat (width, height).
Geometry UVs are authored in metres, so the runtime sets repeat = 1 / tile_m.
"""
import json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from texlib import (read_bmp, write_bmp, hex_rgb, luminance, blur, delight, match_mean,
                    lift_shadows, height_from_albedo, normal_from_height,
                    resize_wrap, fix_vertical_seam, blend_vertical_seam)
import procedural

SIZE = 1024

# ------------------------------------------------------------ hero recipes ---
# measured: courses/rows counted with texlib.dominant_period on the 1024 px source.
HERO = {
    "brick_gothic_a": dict(src="brick_gothic_a", tile_m=(2.4, 2.4),   # 24 courses x 10 cm
                           target="#86473A", chroma=1.05, delight=0.5,
                           height="recess", recess_pct=88, normal=5.0, roughness=0.88),
    "brick_gothic_b": dict(src="brick_gothic_b", tile_m=(1.8, 1.8),   # 18 courses x 10 cm
                           target="#86473A", chroma=1.05, delight=0.5,
                           height="recess", recess_pct=88, normal=5.0, roughness=0.88),
    "roof_tile_red":  dict(src="roof_tile_red", tile_m=(4.75, 4.8),   # 19 ribs x 25 cm, 16 rows x 30 cm
                           target="#A04E35", chroma=0.95, delight=0.6, fix_v_seam=True,
                           height="lum", normal=8.0, roughness=0.75),
    "log_wall":       dict(src="log_wall", tile_m=(2.0, 2.0),         # 8 logs x 25 cm
                           target="#574535", chroma=1.0, delight=0.5, fix_v_seam=True,
                           height="recess", recess_pct=96, round_rows=True, normal=7.0, roughness=0.9),
    "wood_shingle":   dict(src="wood_shingle", tile_m=(2.1, 2.1),     # 14 rows x 15 cm
                           target="#6B6052", chroma=1.0, delight=0.7, fix_v_seam=True,
                           height="lum", normal=5.0, roughness=0.92),
    "thatch":         dict(src="thatch", tile_m=(2.0, 2.0),           # 8 courses x 25 cm
                           target="#97804F", chroma=0.95, delight=0.6, soften_ink=0.55, blend_v_seam=True,  # half-height shift = 4 courses
                           height="lum", normal=4.0, roughness=0.97),
    "fieldstone":     dict(src="fieldstone", tile_m=(3.0, 3.0),       # ~14 stones across
                           target="#938A7A", chroma=1.0, delight=0.5, fix_v_seam=True,
                           height="recess", recess_pct=85, normal=5.0, roughness=0.92),
}


def recess_height(img, pct):
    """Height for walls whose joints are LIGHTER than the units (lime mortar, clay chinking).
    The joint colour is estimated from the brightest pixels; pixels close to it are pressed in."""
    lum = luminance(img)
    sel = lum >= np.percentile(lum, pct)
    joint = img[sel].mean(0)
    dist = np.linalg.norm(img - joint, axis=-1)
    d0 = np.percentile(dist, 12)   # most joint-like
    d1 = np.percentile(dist, 40)
    unit = np.clip((dist - d0) / (d1 - d0 + 1e-6), 0, 1)
    unit = blur(unit, 1.2)
    detail = height_from_albedo(img, detail_sigma=0.8, broad_sigma_frac=0.02)
    h = unit * 0.8 + detail * 0.2
    return (h - h.min()) / (h.max() - h.min() + 1e-6), unit


def round_rows(unit, h, weight=0.6):
    """Logs: turn each course between chinking lines into a rounded (cylindrical) profile.
    The per-row fraction of 'wood' pixels marks where the chinking runs."""
    prof = unit.mean(1)
    prof = (prof - prof.min()) / (prof.max() - prof.min() + 1e-6)
    prof = blur(np.tile(prof[:, None], (1, 8)), 6.0)[:, 0]        # smooth, wraps vertically
    prof = np.sqrt(np.clip(prof, 0, 1))                            # flat-topped -> rounded log
    out = h * (1 - weight) + prof[:, None] * weight
    return (out - out.min()) / (out.max() - out.min() + 1e-6)


def preview(albedo, normal):
    """Lit check image: sun from upper-left, 50% ambient (style guide: shaded sides keep detail)."""
    n = normal * 2 - 1
    ldir = np.array([-0.45, 0.55, 0.70], np.float32)
    ldir /= np.linalg.norm(ldir)
    ndl = np.clip((n * ldir).sum(-1), 0, 1)
    return np.clip(albedo * (0.5 + 0.7 * ndl)[..., None], 0, 1)


def build_hero(fid, r, src_dir):
    """Returns albedo, normal and the effective tile size in metres (after any seam crop)."""
    img = read_bmp(os.path.join(src_dir, r["src"] + ".bmp"))     # full-resolution source
    tile_u, tile_v = r["tile_m"]
    if r.get("fix_v_seam"):
        img, kept = fix_vertical_seam(img, **r.get("seam_opts", {}))
        tile_v *= kept                                             # fewer courses per repeat
        print(f"  {fid}: vertical seam crop kept {kept:.3f} of the height")
    if r.get("blend_v_seam"):
        img = blend_vertical_seam(img)
    img = resize_wrap(img, SIZE, SIZE)
    if r.get("delight"):
        img = delight(img, strength=r["delight"])
    if r.get("soften_ink"):
        img = lift_shadows(img, floor=0.14, amount=r["soften_ink"])
    img = match_mean(img, hex_rgb(r["target"]), chroma=r.get("chroma", 1.0))
    if r["height"] == "recess":
        h, unit = recess_height(img, r["recess_pct"])
        if r.get("round_rows"):
            h = round_rows(unit, h)
    else:
        h = height_from_albedo(img, detail_sigma=0.8, broad_sigma_frac=0.03)
    return img, normal_from_height(h, r["normal"]), (round(tile_u, 3), round(tile_v, 3))


def save(fid, albedo, normal, out_dir):
    write_bmp(os.path.join(out_dir, f"{fid}_albedo.bmp"), albedo)
    write_bmp(os.path.join(out_dir, f"{fid}_normal.bmp"), normal)
    write_bmp(os.path.join(out_dir, f"{fid}_preview.bmp"), preview(albedo, normal))


def main():
    src_dir, out_dir = sys.argv[1], sys.argv[2]
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    fam = sys.argv[sys.argv.index("--family") + 1] if "--family" in sys.argv else None
    os.makedirs(out_dir, exist_ok=True)
    man_path = os.path.join(out_dir, "manifest.json")
    manifest = json.load(open(man_path)) if os.path.exists(man_path) else {}

    jobs = []
    if only in (None, "hero"):
        jobs += [("hero", fid, r) for fid, r in HERO.items()]
    if only in (None, "proc"):
        jobs += [("proc", fid, r) for fid, r in procedural.RECIPES.items()]
    for kind, fid, r in jobs:
        if fam and fid != fam:
            continue
        if kind == "hero":
            albedo, normal, tile_m = build_hero(fid, r, src_dir)
        else:
            albedo, normal = procedural.build(fid, r, SIZE)
            tile_m = r["tile_m"]
        save(fid, albedo, normal, out_dir)
        manifest[fid] = {
            "albedo": f"{fid}_albedo.jpg",
            "normal": f"{fid}_normal.jpg",
            "tile_m": list(tile_m),
            "roughness": r["roughness"],
            "source": "image-generated" if kind == "hero" else "procedural",
        }
        print(f"built {fid:20s} tile={tile_m}  mean=#{''.join(f'{int(v*255):02X}' for v in albedo.reshape(-1,3).mean(0))}")
    json.dump(dict(sorted(manifest.items())), open(man_path, "w"), indent=2)


if __name__ == "__main__":
    main()
