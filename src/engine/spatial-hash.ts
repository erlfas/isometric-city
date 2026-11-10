import type { Parcel, Citizen } from '../types';

export class SpatialHashGrid {
  private cellSize: number;
  private parcelBuckets: Map<number, Parcel[]> = new Map();
  private citizenBuckets: Map<number, Citizen[]> = new Map();

  // Scratch list for zero-allocation query results
  private queryResultParcels: Parcel[] = [];
  private queryResultCitizens: Citizen[] = [];
  private visitedKeys: Set<number> = new Set();

  constructor(cellSize: number = 24.0) {
    this.cellSize = cellSize;
  }

  private hashCoords(cx: number, cz: number): number {
    // 32-bit integer spatial hash
    return ((cx & 0xffff) << 16) | (cz & 0xffff);
  }

  public getCellCoord(x: number): number {
    return Math.floor(x / this.cellSize);
  }

  public indexParcels(parcels: Parcel[]): void {
    this.parcelBuckets.clear();
    for (let i = 0; i < parcels.length; i++) {
      const p = parcels[i];
      const minCx = this.getCellCoord(p.x - p.width * 0.5);
      const maxCx = this.getCellCoord(p.x + p.width * 0.5);
      const minCz = this.getCellCoord(p.z - p.depth * 0.5);
      const maxCz = this.getCellCoord(p.z + p.depth * 0.5);

      for (let cx = minCx; cx <= maxCx; cx++) {
        for (let cz = minCz; cz <= maxCz; cz++) {
          const key = this.hashCoords(cx, cz);
          let list = this.parcelBuckets.get(key);
          if (!list) {
            list = [];
            this.parcelBuckets.set(key, list);
          }
          list.push(p);
        }
      }
    }
  }

  public clearCitizens(): void {
    this.citizenBuckets.clear();
  }

  public insertCitizen(citizen: Citizen, x: number, z: number): void {
    const cx = this.getCellCoord(x);
    const cz = this.getCellCoord(z);
    const key = this.hashCoords(cx, cz);
    let list = this.citizenBuckets.get(key);
    if (!list) {
      list = [];
      this.citizenBuckets.set(key, list);
    }
    list.push(citizen);
  }

  public queryParcelsInBounds(minX: number, maxX: number, minZ: number, maxZ: number): Parcel[] {
    this.queryResultParcels.length = 0;
    this.visitedKeys.clear();

    const minCx = this.getCellCoord(minX);
    const maxCx = this.getCellCoord(maxX);
    const minCz = this.getCellCoord(minZ);
    const maxCz = this.getCellCoord(maxZ);

    for (let cx = minCx; cx <= maxCx; cx++) {
      for (let cz = minCz; cz <= maxCz; cz++) {
        const key = this.hashCoords(cx, cz);
        const list = this.parcelBuckets.get(key);
        if (list) {
          for (let i = 0; i < list.length; i++) {
            const p = list[i];
            const pKey = (p as any)._shId || ((p as any)._shId = p.id);
            if (!this.visitedKeys.has(pKey)) {
              this.visitedKeys.add(pKey);
              this.queryResultParcels.push(p);
            }
          }
        }
      }
    }
    return this.queryResultParcels;
  }

  public queryCitizensInBounds(minX: number, maxX: number, minZ: number, maxZ: number): Citizen[] {
    this.queryResultCitizens.length = 0;
    this.visitedKeys.clear();

    const minCx = this.getCellCoord(minX);
    const maxCx = this.getCellCoord(maxX);
    const minCz = this.getCellCoord(minZ);
    const maxCz = this.getCellCoord(maxZ);

    for (let cx = minCx; cx <= maxCx; cx++) {
      for (let cz = minCz; cz <= maxCz; cz++) {
        const key = this.hashCoords(cx, cz);
        const list = this.citizenBuckets.get(key);
        if (list) {
          for (let i = 0; i < list.length; i++) {
            const c = list[i];
            const cKey = (c as any)._shId || ((c as any)._shId = c.id);
            if (!this.visitedKeys.has(cKey)) {
              this.visitedKeys.add(cKey);
              this.queryResultCitizens.push(c);
            }
          }
        }
      }
    }
    return this.queryResultCitizens;
  }

  public findNearestCitizen(wx: number, wz: number, maxRadius: number = 5.0): Citizen | null {
    const list = this.queryCitizensInBounds(
      wx - maxRadius,
      wx + maxRadius,
      wz - maxRadius,
      wz + maxRadius
    );
    let bestDistSq = maxRadius * maxRadius;
    let bestCitizen: Citizen | null = null;

    for (let i = 0; i < list.length; i++) {
      const c = list[i];
      const cx = c.currentX ?? 0;
      const cz = c.currentZ ?? 0;
      const dx = cx - wx;
      const dz = cz - wz;
      const distSq = dx * dx + dz * dz;
      if (distSq < bestDistSq) {
        bestDistSq = distSq;
        bestCitizen = c;
      }
    }
    return bestCitizen;
  }

  public findParcelAt(wx: number, wz: number): Parcel | null {
    const cx = this.getCellCoord(wx);
    const cz = this.getCellCoord(wz);
    const key = this.hashCoords(cx, cz);
    const list = this.parcelBuckets.get(key);
    if (!list) return null;

    for (let i = 0; i < list.length; i++) {
      const p = list[i];
      // Check 2D bounding box
      const halfW = p.width * 0.5 + 0.5;
      const halfD = p.depth * 0.5 + 0.5;
      if (
        wx >= p.x - halfW &&
        wx <= p.x + halfW &&
        wz >= p.z - halfD &&
        wz <= p.z + halfD
      ) {
        return p;
      }
    }
    return null;
  }
}
