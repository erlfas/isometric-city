import * as THREE from 'three';

/**
 * Static scenery (buildings, walls, stalls, trees) drawn as one THREE.BatchedMesh per material.
 *
 * Each template mesh's geometry is stored once per batch; every placement adds an instance
 * with its own matrix and colour multiplier (texture-variant tint, HSL jitter), so all
 * placements share one material. A batch is one multi-draw call and culls per instance.
 * Templates have one mesh per material (build_assets.py merges by material), so instancing
 * per model would leave most batches at a single instance; batching across models is what
 * cuts draw calls.
 *
 * Placements are fixed once build() has run.
 */

/** Material to draw a template mesh with, and a colour multiplier for this placement. */
export type Tint = (mat: THREE.Material) => { material: THREE.Material; tint?: THREE.Color } | null;

export interface Placement { name: string; x: number; z: number; parcelId?: string }

interface Part { geometry: THREE.BufferGeometry; material: THREE.Material; local: THREE.Matrix4; cast: boolean; receive: boolean }
interface Batch {
  material: THREE.Material; cast: boolean; receive: boolean;
  geometries: THREE.BufferGeometry[];
  instances: { geometry: THREE.BufferGeometry; matrix: THREE.Matrix4; tint: THREE.Color }[];
}

const WHITE = new THREE.Color(1, 1, 1);

/** Geometries in one BatchedMesh must share attribute layout and indexing. */
function layout(g: THREE.BufferGeometry): string {
  const attrs = Object.keys(g.attributes).sort().map((k) => `${k}${g.attributes[k].itemSize}`);
  return `${attrs.join(',')}|${g.index ? 'i' : 'n'}`;
}

export class StaticBatches {
  readonly placements: Placement[] = [];
  private parts = new Map<THREE.Object3D, Part[]>();
  private batches = new Map<string, Batch>();
  private tmp = new THREE.Vector3();

  /** Add one placement of `template` (a loaded model root named after its model). */
  place(template: THREE.Object3D, world: THREE.Matrix4, tint?: Tint, parcelId?: string): void {
    this.tmp.setFromMatrixPosition(world);
    this.placements.push({ name: template.name, x: this.tmp.x, z: this.tmp.z, parcelId });
    for (const part of this.partsOf(template)) {
      const got = tint?.(part.material);
      const material = got?.material ?? part.material;
      const key = `${material.id}|${layout(part.geometry)}|${part.cast}|${part.receive}`;
      let b = this.batches.get(key);
      if (!b) this.batches.set(key, (b = { material, cast: part.cast, receive: part.receive, geometries: [], instances: [] }));
      if (!b.geometries.includes(part.geometry)) b.geometries.push(part.geometry);
      b.instances.push({
        geometry: part.geometry,
        matrix: new THREE.Matrix4().multiplyMatrices(world, part.local),
        tint: got?.tint ?? WHITE,
      });
    }
  }

  /** Create the batched meshes; call once after the last place(). Returns the batch count. */
  build(scene: THREE.Scene): number {
    for (const b of this.batches.values()) {
      let verts = 0, idx = 0;
      for (const g of b.geometries) {
        verts += g.attributes.position.count;
        idx += g.index?.count ?? 0;
      }
      const mesh = new THREE.BatchedMesh(b.instances.length, verts, idx, b.material);
      const ids = new Map(b.geometries.map((g) => [g, mesh.addGeometry(g)]));
      for (const inst of b.instances) {
        const i = mesh.addInstance(ids.get(inst.geometry)!);
        mesh.setMatrixAt(i, inst.matrix);
        mesh.setColorAt(i, inst.tint);
      }
      mesh.sortObjects = b.material.transparent; // per-frame sort only matters for blending
      mesh.castShadow = b.cast;
      mesh.receiveShadow = b.receive;
      mesh.matrixAutoUpdate = false;
      scene.add(mesh);
    }
    const n = this.batches.size;
    this.batches.clear();
    return n;
  }

  private partsOf(template: THREE.Object3D): Part[] {
    let parts = this.parts.get(template);
    if (parts) return parts;
    parts = [];
    template.updateMatrixWorld(true);
    const inv = new THREE.Matrix4().copy(template.matrixWorld).invert();
    template.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      if (Array.isArray(mesh.material)) throw new Error(`${template.name}: multi-material mesh ${mesh.name}`);
      parts!.push({
        geometry: mesh.geometry,
        material: mesh.material,
        local: new THREE.Matrix4().multiplyMatrices(inv, mesh.matrixWorld),
        cast: mesh.castShadow,
        receive: mesh.receiveShadow,
      });
    });
    this.parts.set(template, parts);
    return parts;
  }
}
