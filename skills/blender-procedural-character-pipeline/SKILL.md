---
name: blender-procedural-character-pipeline
description: Add or change a citizen character (trade kit, costume, variants, colours, tools, work animation) in build_characters.py and the instanced crowd renderer. Use before touching build_characters.py, src/engine/citizen-crowd.ts or char_*.glb.
---
# Character kits

A character is a **kit**: one shared body plus per-trade pieces, exported as one GLB of many meshes. `src/engine/citizen-crowd.ts` instances every mesh, picks one look per citizen from its id, and swings the parts. Format and runtime contract: the header of `citizen-crowd.ts` and "Kit pipeline (v2)" in `build_characters.py`. Background: `KEY_FINDINGS.md` §18.

Legacy single-mesh characters (`CHARACTER_BUILDERS`) still render as one rigid `body` part. Convert a trade by moving it to `KIT_BUILDERS`; don't extend the legacy builders.

## Rules

- **Frame**: Blender Z up, the character faces -Y, so its **right hand is at -X**. Tools go in `arm_R` at x ≈ -0.24.
- **Parts**: `body head arm_L arm_R leg_L leg_R`; each swings about `BASE_PIVOTS`. Geometry that must move with a limb (tools, gloves, sleeves) goes in that limb's part.
- **Variants**: `kit.option(group, opt, w_male, w_female)` plus geometry in `kit.bm(part, "group:opt")`. Combine conditions with `+` (`"apron:bib+sex:f"`). An option with no geometry (`hat:bare`) just draws nothing. Shells that stack (hair < coif < hood) need increasing radii.
- **Colours**: dyeable surfaces use `kit.mat("slot:<name>")` plus `kit.slot(name, palette)`; palette rows are `[sRGB hex, weight, tiers]` with tiers `p a b r` = plebeian, artisan, burgher, patrician. Fixed materials (`FIXED_MATS`) are sRGB too; `create_mat` linearises.
- **Readability**: metallic ≤ 0.3 (no environment map, so metal renders black); every head cloth gets `add_fringe`. Why: `KEY_FINDINGS.md` §18.6.
- **Trade signature first**: everything a viewer uses to recognise the trade (apron, tool, boots) is base geometry; everything else varies.
- **Work loop**: set `kit.anim = {"work": "<name>"}` and add the pose to `CitizenCrowd.update`. Lean only the upper body.
- **Budget**: `check_models.py` enforces base and per-variant triangle limits.

## Loop

1. Look at the trade's turnaround in `reference_photos/workers/` (kit sheets: `reference_photos/workers/kit/`; prompts in `docs/IMAGE_GENERATION_PROMPTS_AND_GALLERY.md`, "Character Kit Reference Sheets").
2. Build only that kit: `$BLENDER --background --factory-startup --python build_characters.py -- char_<trade>`.
3. `$PY scripts/check_models.py` and `npm run check`.
4. With `npm run dev` running, screenshot idle, work and walk at close zoom on open ground:
   `node scripts/shoot.mjs out.png "cam=-15.5,-25.5,4.5,0&pause&hour=11&lineup=char_<trade>,8,work"`
   Done when, across 8 citizens, the trade reads at a glance, no two look alike, and nothing clips or floats in any of the three poses.
