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
 * Placements are fixed once build() has run, but each can be hidden (setPlacementVisible)
 * and its parts drawn separately instead (partsOfPlacement): the cutaway does that.
 */

/** Material to draw a template mesh with, and a colour multiplier for this placement. */
export type Tint = (mat: THREE.Material) => { material: THREE.Material; tint?: THREE.Color } | null;

export interface Placement { name: string; x: number; z: number; parcelId?: string }

interface Part { geometry: THREE.BufferGeometry; material: THREE.Material; local: THREE.Matrix4; cast: boolean; receive: boolean }
/** One part of one placement: its batch slot and what it is drawn with. */
export interface PlacedPart {
  geometry: THREE.BufferGeometry; material: THREE.Material; matrix: THREE.Matrix4; tint: THREE.Color;
  cast: boolean; receive: boolean;
  mesh?: THREE.BatchedMesh; id?: number;
}
interface Batch {
  material: THREE.Material; cast: boolean; receive: boolean;
  geometries: THREE.BufferGeometry[];
  instances: PlacedPart[];
}

const WHITE = new THREE.Color(1, 1, 1);

/** Geometries in one BatchedMesh must share attribute layout and indexing. */
function layout(g: THREE.BufferGeometry): string {
  const attrs = Object.keys(g.attributes).sort().map((k) => `${k}${g.attributes[k].itemSize}`);
  return `${attrs.join(',')}|${g.index ? 'i' : 'n'}`;
}

/** A placement with its template and world matrix (navigation grid, building anchors). */
export interface PlacedModel { template: THREE.Object3D; matrix: THREE.Matrix4; parcelId?: string }

export class StaticBatches {
  readonly placements: Placement[] = [];
  /** Same order as placements; kept apart so placements stay plain data (debug hooks print them). */
  readonly placed: PlacedModel[] = [];
  private parts = new Map<THREE.Object3D, Part[]>();
  private batches = new Map<string, Batch>();
  /** Per placement: its parts (batch slots after build). */
  private byPlacement: PlacedPart[][] = [];
  /** Per placement: world bounds of its parts. */
  readonly bounds: THREE.Box3[] = [];
  private tmp = new THREE.Vector3();
  private box = new THREE.Box3();

  /** Add one placement of `template` (a loaded model root named after its model). */
  place(template: THREE.Object3D, world: THREE.Matrix4, tint?: Tint, parcelId?: string): void {
    this.tmp.setFromMatrixPosition(world);
    this.placements.push({ name: template.name, x: this.tmp.x, z: this.tmp.z, parcelId });
    this.placed.push({ template, matrix: world.clone(), parcelId });
    const mine: PlacedPart[] = [];
    const bounds = new THREE.Box3();
    for (const part of this.partsOf(template)) {
      const got = tint?.(part.material);
      const material = got?.material ?? part.material;
      const key = `${material.id}|${layout(part.geometry)}|${part.cast}|${part.receive}`;
      let b = this.batches.get(key);
      if (!b) this.batches.set(key, (b = { material, cast: part.cast, receive: part.receive, geometries: [], instances: [] }));
      if (!b.geometries.includes(part.geometry)) b.geometries.push(part.geometry);
      const inst: PlacedPart = {
        geometry: part.geometry, material,
        matrix: new THREE.Matrix4().multiplyMatrices(world, part.local),
        tint: got?.tint ?? WHITE, cast: part.cast, receive: part.receive,
      };
      b.instances.push(inst);
      mine.push(inst);
      if (!part.geometry.boundingBox) part.geometry.computeBoundingBox();
      bounds.union(this.box.copy(part.geometry.boundingBox!).applyMatrix4(inst.matrix));
    }
    this.byPlacement.push(mine);
    this.bounds.push(bounds);
  }

  /** Parts of the i-th placement with their world matrices and tints. */
  partsOfPlacement(i: number): readonly PlacedPart[] {
    return this.byPlacement[i] ?? [];
  }

  /** Show or hide the i-th placement in the batches (colour and shadow pass). */
  setPlacementVisible(i: number, visible: boolean): void {
    for (const p of this.byPlacement[i] ?? []) if (p.mesh) p.mesh.setVisibleAt(p.id!, visible);
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
        inst.mesh = mesh;
        inst.id = i;
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
