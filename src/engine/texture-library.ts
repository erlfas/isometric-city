import * as THREE from 'three';

/**
 * Runtime texture binding for Blender-exported models.
 *
 * Models carry world-space UVs in metres (build_assets.py add_world_uvs). Each texture
 * family in public/textures/manifest.json states how many metres one repeat covers,
 * so texture.repeat = 1 / tile_m and a brick is the same size on every building.
 *
 * glTF materials are matched by name and replaced with shared textured materials.
 * Per-building variety comes from a small cache of tinted variants (VARIANTS per
 * material) instead of cloning a material for every one of the ~580 buildings.
 */

interface ManifestEntry {
  albedo: string;
  normal: string;
  tile_m: [number, number];
  roughness: number;
  source: string;
}

interface Binding {
  /** One family, or several to pick from per building (e.g. two brick variants). */
  families: string[];
  /** Multiplies the texture: lets one texture serve several materials (cream vs white plaster). */
  tint?: number;
  /** How far per-building variants may drift in brightness / warmth. */
  jitter?: number;
}

const BINDINGS: Record<string, Binding> = {
  BrickGothic: { families: ['brick_gothic_a', 'brick_gothic_b'], jitter: 0.08 },
  BrickDark: { families: ['brick_gothic_a', 'brick_gothic_b'], tint: 0xb49a92, jitter: 0.06 },
  BrickOven: { families: ['brick_gothic_b'], tint: 0xe6cfc6 },
  RoofTileRed: { families: ['roof_tile_red'], jitter: 0.1 },
  RoofShingle: { families: ['wood_shingle'], jitter: 0.08 },
  RoofThatch: { families: ['thatch'], jitter: 0.1 },
  TimberLog: { families: ['log_wall'], jitter: 0.08 },
  TimberLogWeathered: { families: ['log_wall'], tint: 0xc6bfb6, jitter: 0.06 },
  TimberDark: { families: ['timber_beam'], jitter: 0.06 },
  TimberPlank: { families: ['plank_board'], jitter: 0.08 },
  TimberWeathered: { families: ['plank_board'], tint: 0xbdb8b0, jitter: 0.06 },
  Limestone: { families: ['limestone_ashlar'], jitter: 0.04 },
  StoneFieldstone: { families: ['fieldstone'], jitter: 0.06 },
  PlasterWhite: { families: ['plaster_lime'], jitter: 0.04 },
  PlasterCream: { families: ['plaster_lime'], tint: 0xebddc0, jitter: 0.04 },
  CopperPatina: { families: ['copper_patina'] },
  FoliageGreen: { families: ['foliage'], jitter: 0.1 },
  AwningRedWhite: { families: ['awning_red'] },
  AwningBlueWhite: { families: ['awning_blue'] },
  AwningYellowWhite: { families: ['awning_yellow'] },
};

const VARIANTS = 8;

export class TextureLibrary {
  private manifest: Record<string, ManifestEntry> = {};
  private albedo = new Map<string, THREE.Texture>();
  private normal = new Map<string, THREE.Texture>();
  private baseMaterials = new Map<string, THREE.MeshStandardMaterial>();
  private variantCache = new Map<string, THREE.MeshStandardMaterial>();
  private maxAnisotropy = 1;
  public ready = false;

  private basePath: string;

  constructor(basePath = '/textures/') {
    this.basePath = basePath;
  }

  public async load(renderer: THREE.WebGLRenderer): Promise<void> {
    this.maxAnisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    const res = await fetch(`${this.basePath}manifest.json`);
    if (!res.ok) throw new Error(`texture manifest: HTTP ${res.status}`);
    this.manifest = await res.json();

    const loader = new THREE.TextureLoader();
    await Promise.all(
      Object.entries(this.manifest).map(async ([id, e]) => {
        const [a, n] = await Promise.all([
          loader.loadAsync(this.basePath + e.albedo),
          loader.loadAsync(this.basePath + e.normal),
        ]);
        this.albedo.set(id, this.configure(a, e, THREE.SRGBColorSpace));
        this.normal.set(id, this.configure(n, e, THREE.NoColorSpace));
      })
    );
    this.ready = true;
    console.log(`[TextureLibrary] Loaded ${this.albedo.size} texture families.`);
  }

  /** Raw tiling texture for custom shaders (ground splat). */
  public getAlbedo(id: string): THREE.Texture | undefined {
    return this.albedo.get(id);
  }

  public getTile(id: string): [number, number] | undefined {
    return this.manifest[id]?.tile_m;
  }

  private configure(t: THREE.Texture, e: ManifestEntry, cs: THREE.ColorSpace): THREE.Texture {
    t.colorSpace = cs;
    // glTF UV convention (origin top-left); our UVs are authored for it.
    t.flipY = false;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(1 / e.tile_m[0], 1 / e.tile_m[1]);
    t.anisotropy = this.maxAnisotropy;
    t.needsUpdate = true;
    return t;
  }

  public isTextured(mat: THREE.Material): boolean {
    return this.ready && !!BINDINGS[mat.name] && !!(mat as THREE.MeshStandardMaterial).map;
  }

  /** Swap a loaded model's flat glTF materials for shared textured ones (variant 0). */
  public applyToTemplate(root: THREE.Object3D): void {
    if (!this.ready) return;
    root.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;
      const swap = (m: THREE.Material) => this.base(m) ?? m;
      mesh.material = Array.isArray(mesh.material) ? mesh.material.map(swap) : swap(mesh.material);
    });
  }

  private base(src: THREE.Material, familyIndex = 0): THREE.MeshStandardMaterial | null {
    const b = BINDINGS[src.name];
    if (!b) return null;
    const fam = b.families[familyIndex % b.families.length];
    const key = `${src.name}|${fam}`;
    let mat = this.baseMaterials.get(key);
    if (!mat) {
      const e = this.manifest[fam];
      const map = this.albedo.get(fam);
      if (!e || !map) return null;
      const s = src as THREE.MeshStandardMaterial;
      mat = new THREE.MeshStandardMaterial({
        name: src.name,
        map,
        normalMap: this.normal.get(fam),
        color: new THREE.Color(b.tint ?? 0xffffff),
        roughness: e.roughness,
        metalness: s.metalness ?? 0,
      });
      // Our normal maps are OpenGL-style (+Y = image up), but the glTF export flips v
      // (v' = 1 - v), so texture "up" runs against +v here. Invert green to match.
      // Verified in-engine: with +1, bricks read as lit from below.
      mat.normalScale.set(1, -1);
      this.baseMaterials.set(key, mat);
    }
    return mat;
  }

  /**
   * Cached per-building variant of a textured material. `hash` is the parcel hash:
   * it picks the texture family (brick a/b) and one of VARIANTS tints.
   */
  public variant(mat: THREE.Material, hash: number): THREE.MeshStandardMaterial | null {
    const b = BINDINGS[mat.name];
    if (!b || !this.ready) return null;
    const h = Math.abs(hash | 0);
    const famIdx = (h >>> 5) % b.families.length;
    const v = h % VARIANTS;
    const key = `${mat.name}|${famIdx}|${v}`;
    let out = this.variantCache.get(key);
    if (!out) {
      const base = this.base(mat, famIdx);
      if (!base) return null;
      out = base.clone();
      const j = b.jitter ?? 0;
      if (j > 0) {
        // Deterministic spread across the variants: brightness and a slight warm/cool shift.
        const r1 = ((v * 37) % VARIANTS) / (VARIANTS - 1) * 2 - 1;
        const r2 = ((v * 53 + 3) % VARIANTS) / (VARIANTS - 1) * 2 - 1;
        const k = 1 - j + j * r1;                     // <= 1: tints only darken a full-range texture
        out.color.multiplyScalar(k);
        out.color.r *= 1 + r2 * j * 0.35;
        out.color.b *= 1 - r2 * j * 0.35;
      }
      this.variantCache.set(key, out);
    }
    return out;
  }
}
