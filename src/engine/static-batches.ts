import * as THREE from 'three';

/**
 * Static scenery (buildings, walls, stalls, trees) drawn as one THREE.BatchedMesh per material.
 *
 * Each template mesh's geometry is stored once per batch; every placement adds an instance
 * with its own matrix and colour multiplier (texture-variant tint, HSL jitter), so all
 * placements share one material. A batch is one multi-draw call and culls per instance
 * (staticBatch: once per camera move, not per pass).
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
/** Layer of objects drawn only into the shadow map; enable it on the light's shadow camera. */
export const SHADOW_LAYER = 1;

/** The volume the batches are culled against; `version` changes when the camera does. */
interface Cull { camera: THREE.Camera | null; version: number }

/** three's own per-pass draw list builder (not in its typings). */
interface DrawList { _visibilityChanged: boolean; _updateDrawParameters(camera: THREE.Camera, geometry: THREE.BufferGeometry, material: THREE.Material): void }

/**
 * Make `mesh` a batch whose instances never move. three culls every instance and re-uploads the
 * draw list every time it draws the batch: for the city that was thousands of sphere tests
 * and a texture upload per batch per frame. Here the list is culled against `cull.camera`
 * (a volume around the view, see ThreeIsometricRenderer.fitShadow) and rebuilt only when
 * that volume or an instance's visibility changes.
 */
function staticBatch(mesh: THREE.BatchedMesh, cull: Cull): THREE.BatchedMesh {
  const list = mesh as unknown as DrawList;
  let seen = -1;
  const refresh = (passCamera: THREE.Camera, geometry: THREE.BufferGeometry, material: THREE.Material) => {
    if (seen === cull.version && !list._visibilityChanged) return;
    seen = cull.version;
    mesh.perObjectFrustumCulled = true; // for this call only: three skips the rebuild otherwise
    list._updateDrawParameters(cull.camera ?? passCamera, geometry, material);
    mesh.perObjectFrustumCulled = false;
  };
  mesh.perObjectFrustumCulled = false;
  mesh.sortObjects = false;
  mesh.onBeforeRender = (_r, _s, camera, geometry, material) => refresh(camera, geometry, material);
  mesh.onBeforeShadow = (_r, _s, _c, shadowCamera, geometry, depthMaterial) => refresh(shadowCamera, geometry, depthMaterial);
  return mesh;
}

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
  private cull: Cull = { camera: null, version: 0 };

  /** Cull the batches against this camera's frustum from now on; call again whenever its
   *  matrices change (until the first call each pass culls against its own camera). */
  setCullCamera(camera: THREE.Camera): void {
    this.cull.camera = camera;
    this.cull.version++;
  }

  /** Draw shadow casters for the placements in this camera's frustum (the sun's shadow box);
   *  call again whenever its matrices change. */
  setCasterCamera(camera: THREE.Camera): void {
    this.casterCam = camera;
    this.castersDirty = true;
  }

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

  /** Top (m) of the tallest placement the frustum touches; 0 if none. */
  topIn(frustum: THREE.Frustum): number {
    let top = 0;
    for (const b of this.bounds) if (b.max.y > top && frustum.intersectsBox(b)) top = b.max.y;
    return top;
  }

  /** Parts of the i-th placement with their world matrices and tints. */
  partsOfPlacement(i: number): readonly PlacedPart[] {
    return this.byPlacement[i] ?? [];
  }

  /** Show or hide the i-th placement in the batches (colour and shadow pass). */
  setPlacementVisible(i: number, visible: boolean): void {
    for (const p of this.byPlacement[i] ?? []) if (p.mesh) p.mesh.setVisibleAt(p.id!, visible);
    if (visible) this.hidden.delete(i); else this.hidden.add(i);
    this.castersDirty = true;
  }

  // Shadow casters. In the shadow pass a material is irrelevant, so each model is drawn as
  // ONE mesh (its casting parts merged, positions only), instanced over its placements:
  // ~25 instanced draws instead of the batches' one draw per part per building (ANGLE runs
  // a multi-draw as that many draws; it was half the frame up close). They sit on
  // SHADOW_LAYER, which only the sun's shadow camera sees; the batches cast nothing.
  private casters: { mesh: THREE.InstancedMesh; placements: number[] }[] = [];
  private hidden = new Set<number>();
  private castersDirty = true;
  private casterCam: THREE.Camera | null = null;
  private frustum = new THREE.Frustum();
  private viewProj = new THREE.Matrix4();

  /** Refill the shadow casters with the placements in the caster camera's box; call before rendering
   *  (does nothing unless the volume or a placement's visibility changed). */
  updateCasters(): void {
    if (!this.castersDirty) return;
    this.castersDirty = false;
    const cam = this.casterCam;
    if (cam) this.frustum.setFromProjectionMatrix(this.viewProj.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse));
    for (const c of this.casters) {
      let n = 0;
      for (const i of c.placements) {
        if (this.hidden.has(i) || (cam && !this.frustum.intersectsBox(this.bounds[i]))) continue;
        c.mesh.setMatrixAt(n++, this.placed[i].matrix);
      }
      c.mesh.count = n;
      c.mesh.visible = n > 0;
      c.mesh.instanceMatrix.clearUpdateRanges();
      c.mesh.instanceMatrix.addUpdateRange(0, n * 16);
      c.mesh.instanceMatrix.needsUpdate = true;
    }
  }

  private buildCasters(scene: THREE.Scene): void {
    const material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, name: 'ShadowCaster' });
    const byTemplate = new Map<THREE.Object3D, number[]>();
    this.placed.forEach((p, i) => {
      const list = byTemplate.get(p.template);
      if (list) list.push(i); else byTemplate.set(p.template, [i]);
    });
    const v = new THREE.Vector3();
    for (const [template, placements] of byTemplate) {
      const parts = this.partsOf(template).filter((p) => p.cast);
      let verts = 0, idx = 0;
      for (const p of parts) {
        verts += p.geometry.attributes.position.count;
        idx += p.geometry.index?.count ?? p.geometry.attributes.position.count;
      }
      if (!idx) continue;
      const pos = new Float32Array(verts * 3);
      const index = new Uint32Array(idx);
      let v0 = 0, i0 = 0;
      for (const p of parts) {
        const src = p.geometry.attributes.position;
        for (let k = 0; k < src.count; k++) {
          v.fromBufferAttribute(src, k).applyMatrix4(p.local).toArray(pos, (v0 + k) * 3);
        }
        const si = p.geometry.index;
        const n = si?.count ?? src.count;
        for (let k = 0; k < n; k++) index[i0 + k] = v0 + (si ? si.getX(k) : k);
        v0 += src.count;
        i0 += n;
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      geometry.setIndex(new THREE.BufferAttribute(index, 1));
      const mesh = new THREE.InstancedMesh(geometry, material, placements.length);
      mesh.name = `${template.name}:shadow`;
      mesh.layers.set(SHADOW_LAYER);
      mesh.castShadow = true;
      mesh.frustumCulled = false; // its instances are culled in updateCasters
      mesh.matrixAutoUpdate = false;
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      mesh.count = 0;
      scene.add(mesh);
      this.casters.push({ mesh, placements });
    }
    this.castersDirty = true;
  }

  /** Create the batched meshes; call once after the last place(). Returns the batch count. */
  build(scene: THREE.Scene): number {
    for (const b of this.batches.values()) {
      let verts = 0, idx = 0;
      for (const g of b.geometries) {
        verts += g.attributes.position.count;
        idx += g.index?.count ?? 0;
      }
      // Blended materials need three's per-frame back-to-front sort; the rest never change.
      const mesh = new THREE.BatchedMesh(b.instances.length, verts, idx, b.material);
      if (!b.material.transparent) staticBatch(mesh, this.cull);
      const ids = new Map(b.geometries.map((g) => [g, mesh.addGeometry(g)]));
      for (const inst of b.instances) {
        const i = mesh.addInstance(ids.get(inst.geometry)!);
        mesh.setMatrixAt(i, inst.matrix);
        mesh.setColorAt(i, inst.tint);
        inst.mesh = mesh;
        inst.id = i;
      }
      if (b.material.transparent) mesh.sortObjects = true;
      mesh.castShadow = false; // the casters below do that
      mesh.receiveShadow = b.receive;
      mesh.matrixAutoUpdate = false;
      scene.add(mesh);
    }
    this.buildCasters(scene);
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
