import type { Parcel, CivicLandmark, PerimeterElement, CastleElement } from '../types';

export interface Vertex3D {
  x: number;
  y: number;
  z: number;
  nx: number;
  ny: number;
  nz: number;
  r: number;
  g: number;
  b: number;
  a: number;
}

export interface MeshBufferData {
  positions: Float32Array; // 3 floats per vert
  normals: Float32Array;   // 3 floats per vert
  colors: Float32Array;    // 4 floats per vert (RGBA)
  indices: Uint32Array;
}

export class GeometryBuilder {
  public vertices: number[] = []; // x, y, z, nx, ny, nz, r, g, b, a
  public indices: number[] = [];
  private vertCount: number = 0;

  public clear(): void {
    this.vertices.length = 0;
    this.indices.length = 0;
    this.vertCount = 0;
  }

  public addVertex(
    x: number, y: number, z: number,
    nx: number, ny: number, nz: number,
    r: number, g: number, b: number, a: number = 1.0
  ): number {
    this.vertices.push(x, y, z, nx, ny, nz, r, g, b, a);
    return this.vertCount++;
  }

  public addQuad(
    v0: [number, number, number],
    v1: [number, number, number],
    v2: [number, number, number],
    v3: [number, number, number],
    normal: [number, number, number],
    color: [number, number, number, number]
  ): void {
    const idx0 = this.addVertex(v0[0], v0[1], v0[2], normal[0], normal[1], normal[2], color[0], color[1], color[2], color[3]);
    const idx1 = this.addVertex(v1[0], v1[1], v1[2], normal[0], normal[1], normal[2], color[0], color[1], color[2], color[3]);
    const idx2 = this.addVertex(v2[0], v2[1], v2[2], normal[0], normal[1], normal[2], color[0], color[1], color[2], color[3]);
    const idx3 = this.addVertex(v3[0], v3[1], v3[2], normal[0], normal[1], normal[2], color[0], color[1], color[2], color[3]);

    this.indices.push(idx0, idx1, idx2, idx0, idx2, idx3);
  }

  public addTriangle(
    v0: [number, number, number],
    v1: [number, number, number],
    v2: [number, number, number],
    normal: [number, number, number],
    color: [number, number, number, number]
  ): void {
    const idx0 = this.addVertex(v0[0], v0[1], v0[2], normal[0], normal[1], normal[2], color[0], color[1], color[2], color[3]);
    const idx1 = this.addVertex(v1[0], v1[1], v1[2], normal[0], normal[1], normal[2], color[0], color[1], color[2], color[3]);
    const idx2 = this.addVertex(v2[0], v2[1], v2[2], normal[0], normal[1], normal[2], color[0], color[1], color[2], color[3]);

    this.indices.push(idx0, idx1, idx2);
  }

  public addBox(
    cx: number, cy: number, cz: number,
    w: number, h: number, d: number,
    color: [number, number, number, number]
  ): void {
    const w2 = w * 0.5;
    const h2 = h * 0.5;
    const d2 = d * 0.5;

    // Top face (+Y)
    this.addQuad(
      [cx - w2, cy + h2, cz - d2],
      [cx - w2, cy + h2, cz + d2],
      [cx + w2, cy + h2, cz + d2],
      [cx + w2, cy + h2, cz - d2],
      [0, 1, 0],
      [color[0] * 1.1, color[1] * 1.1, color[2] * 1.1, color[3]]
    );

    // Bottom face (-Y)
    this.addQuad(
      [cx - w2, cy - h2, cz + d2],
      [cx - w2, cy - h2, cz - d2],
      [cx + w2, cy - h2, cz - d2],
      [cx + w2, cy - h2, cz + d2],
      [0, -1, 0],
      [color[0] * 0.5, color[1] * 0.5, color[2] * 0.5, color[3]]
    );

    // Front (+Z)
    this.addQuad(
      [cx - w2, cy - h2, cz + d2],
      [cx + w2, cy - h2, cz + d2],
      [cx + w2, cy + h2, cz + d2],
      [cx - w2, cy + h2, cz + d2],
      [0, 0, 1],
      [color[0] * 0.9, color[1] * 0.9, color[2] * 0.9, color[3]]
    );

    // Back (-Z)
    this.addQuad(
      [cx + w2, cy - h2, cz - d2],
      [cx - w2, cy - h2, cz - d2],
      [cx - w2, cy + h2, cz - d2],
      [cx + w2, cy + h2, cz - d2],
      [0, 0, -1],
      [color[0] * 0.7, color[1] * 0.7, color[2] * 0.7, color[3]]
    );

    // Left (-X)
    this.addQuad(
      [cx - w2, cy - h2, cz - d2],
      [cx - w2, cy - h2, cz + d2],
      [cx - w2, cy + h2, cz + d2],
      [cx - w2, cy + h2, cz - d2],
      [-1, 0, 0],
      [color[0] * 0.8, color[1] * 0.8, color[2] * 0.8, color[3]]
    );

    // Right (+X)
    this.addQuad(
      [cx + w2, cy - h2, cz + d2],
      [cx + w2, cy - h2, cz - d2],
      [cx + w2, cy + h2, cz - d2],
      [cx + w2, cy + h2, cz + d2],
      [1, 0, 0],
      [color[0] * 0.95, color[1] * 0.95, color[2] * 0.95, color[3]]
    );
  }

  public toMeshBuffer(): MeshBufferData {
    const stride = 10;
    const vCount = this.vertCount;
    const positions = new Float32Array(vCount * 3);
    const normals = new Float32Array(vCount * 3);
    const colors = new Float32Array(vCount * 4);

    for (let i = 0; i < vCount; i++) {
      const offset = i * stride;
      positions[i * 3 + 0] = this.vertices[offset + 0];
      positions[i * 3 + 1] = this.vertices[offset + 1];
      positions[i * 3 + 2] = this.vertices[offset + 2];

      normals[i * 3 + 0] = this.vertices[offset + 3];
      normals[i * 3 + 1] = this.vertices[offset + 4];
      normals[i * 3 + 2] = this.vertices[offset + 5];

      colors[i * 4 + 0] = this.vertices[offset + 6];
      colors[i * 4 + 1] = this.vertices[offset + 7];
      colors[i * 4 + 2] = this.vertices[offset + 8];
      colors[i * 4 + 3] = this.vertices[offset + 9];
    }

    return {
      positions,
      normals,
      colors,
      indices: new Uint32Array(this.indices)
    };
  }
}

export class ProceduralCityBuilder {
  private geo: GeometryBuilder = new GeometryBuilder();

  // Color palettes
  private readonly PALETTE = {
    loessGround: [0.55, 0.48, 0.36, 1.0] as [number, number, number, number],
    cobblestone: [0.45, 0.43, 0.40, 1.0] as [number, number, number, number],
    limestone: [0.76, 0.72, 0.64, 1.0] as [number, number, number, number],
    gothicBrick: [0.58, 0.23, 0.16, 1.0] as [number, number, number, number],
    plasterWhite: [0.82, 0.80, 0.74, 1.0] as [number, number, number, number],
    plasterLoam: [0.68, 0.60, 0.48, 1.0] as [number, number, number, number],
    timberFrame: [0.26, 0.18, 0.12, 1.0] as [number, number, number, number],
    timberWeathered: [0.38, 0.35, 0.32, 1.0] as [number, number, number, number],
    roofCeramicTile: [0.64, 0.25, 0.15, 1.0] as [number, number, number, number],
    roofShingle: [0.32, 0.28, 0.24, 1.0] as [number, number, number, number],
    roofThatch: [0.54, 0.46, 0.30, 1.0] as [number, number, number, number],
    copperRoof: [0.25, 0.48, 0.42, 1.0] as [number, number, number, number],
    wroughtIron: [0.15, 0.15, 0.18, 1.0] as [number, number, number, number],
    gildedGold: [0.88, 0.74, 0.18, 1.0] as [number, number, number, number],
    woodScaffold: [0.48, 0.38, 0.24, 1.0] as [number, number, number, number],
    waterRavine: [0.20, 0.32, 0.36, 1.0] as [number, number, number, number]
  };

  /**
   * Builds the entire city static geometry batch:
   * - Loess plateau & Czechówka/Bystrzyca river valleys
   * - Defensive curtain wall with 14 towers and 2 gates
   * - Castle Hill bailey (Donjon, Royal Chapel, Palace Hall)
   * - Civic Core (Town Hall, Szmatruz Cloth Hall, Parish Fara)
   * - 580 Parcels (25 House types, 3 Shed types, Hung Trade Signs, Yard Clutter, Scaffolding)
   */
  public buildFullCityMesh(
    parcels: Parcel[],
    civicLandmarks: CivicLandmark[],
    perimeterTowers: PerimeterElement[],
    castleElements: CastleElement[]
  ): MeshBufferData {
    this.geo.clear();

    console.log(`[ProceduralCityBuilder] Generating full city geometry for ${parcels.length} parcels...`);

    // 1. Terrain Base (Loess Promontory Plateau & Surrounding Ravines)
    this.buildTerrainBase();

    // 2. Defensive Curtain Wall & Towers
    this.buildPerimeterDefenses(perimeterTowers);

    // 3. Castle Hill Complex
    this.buildCastleHill(castleElements);

    // 4. Civic Landmarks (Town Hall, Szmatruz, Fara Church, Dominican Cloister)
    this.buildCivicLandmarks(civicLandmarks);

    // 5. 580 Parcels: Buildings, Sheds, Hung Signs, Clutter, Scaffolding
    for (let i = 0; i < parcels.length; i++) {
      this.buildParcelBuilding(parcels[i]);
    }

    console.log(`[ProceduralCityBuilder] City mesh built: ${this.geo.vertices.length / 10} vertices, ${this.geo.indices.length / 3} triangles.`);
    return this.geo.toMeshBuffer();
  }

  private buildTerrainBase(): void {
    // Generate organic stepped loess plateau
    const pW = 600;
    const pD = 440;
    // Base valley
    this.geo.addBox(0, -2.5, 0, pW, 2.0, pD, this.PALETTE.loessGround);

    // Czechówka River moat/ravine cutting between Old Town and Castle Hill
    // at X approx 200 to 230
    this.geo.addBox(215, -1.8, 50, 24, 1.4, 320, this.PALETTE.waterRavine);

    // Old Town Main Plateau (+2.5m elevation loess spur)
    this.geo.addBox(0, 0.0, -10, 380, 2.0, 240, [0.58, 0.50, 0.38, 1.0]);

    // Castle Hill Motte (+6.5m elevation mound at X=280, Z=80)
    this.geo.addBox(280, 2.5, 85, 110, 5.0, 110, [0.52, 0.44, 0.34, 1.0]);

    // Cobblestone Market Square (Rynek) paving: 80m x 60m center
    this.geo.addBox(0, 1.05, 0, 84, 0.1, 64, this.PALETTE.cobblestone);

    // Bramowa & Grodzka street paving
    this.geo.addBox(-90, 1.04, -50, 130, 0.1, 14, this.PALETTE.cobblestone);
    this.geo.addBox(110, 1.04, 18, 140, 0.1, 14, this.PALETTE.cobblestone);
  }

  private buildPerimeterDefenses(towers: PerimeterElement[]): void {
    // Wall height 8m, thickness 2.4m
    const wallHeight = 7.5;
    const wallThick = 2.2;

    for (let i = 0; i < towers.length; i++) {
      const t1 = towers[i];
      const t2 = towers[(i + 1) % towers.length];

      // Draw tower
      if (t1.type === 'gate') {
        // Gate structure (Brama Krakowska / Brama Grodzka)
        // Multi-tier gothic brick gateway with arched portal and high roof
        const isKrakow = t1.id.includes('krakow');
        const gw = isKrakow ? 14 : 12;
        const gd = 12;
        const gh = t1.height;
        // Main tower base
        this.geo.addBox(t1.x, gh * 0.5, t1.z, gw, gh, gd, this.PALETTE.gothicBrick);
        // Arched portal opening (dark cutout)
        this.geo.addBox(t1.x, 3.0, t1.z, 5.0, 6.0, gd + 0.8, [0.12, 0.10, 0.10, 1.0]);
        // Octagonal superstructure
        this.geo.addBox(t1.x, gh + 4.0, t1.z, gw * 0.7, 8.0, gd * 0.7, this.PALETTE.gothicBrick);
        // Steep pyramidal roof with copper spire
        this.geo.addBox(t1.x, gh + 9.5, t1.z, gw * 0.75, 4.0, gd * 0.75, this.PALETTE.copperRoof);

        // Barbican / Foregate for Kraków Gate
        if (isKrakow) {
          this.geo.addBox(t1.x - 14, 4.0, t1.z - 8, 12, 8.0, 10, this.PALETTE.gothicBrick);
          // Wooden drawbridge over moat
          this.geo.addBox(t1.x - 24, 1.5, t1.z - 8, 10, 0.6, 6.0, this.PALETTE.timberWeathered);
        }
      } else {
        // Regular defensive tower (half-round or square baszta)
        const tw = 8.0;
        const th = t1.height;
        this.geo.addBox(t1.x, th * 0.5, t1.z, tw, th, tw, this.PALETTE.gothicBrick);
        // Machicolations and crenellations on top
        this.geo.addBox(t1.x, th + 0.6, t1.z, tw + 0.8, 1.2, tw + 0.8, this.PALETTE.limestone);
        // Conical roof
        this.geo.addBox(t1.x, th + 2.5, t1.z, tw * 0.9, 3.0, tw * 0.9, this.PALETTE.roofCeramicTile);
      }

      // Connecting curtain wall segment between t1 and t2
      // Skip gap at Grodzka Gate (bridge leads to castle instead)
      if (t1.id === 'gate_grodzka') continue;

      const midX = (t1.x + t2.x) * 0.5;
      const midZ = (t1.z + t2.z) * 0.5;
      const dx = t2.x - t1.x;
      const dz = t2.z - t1.z;
      const segLen = Math.hypot(dx, dz);
      if (segLen > 0.1) {
        // Build wall box aligned along segment
        this.geo.addBox(midX, wallHeight * 0.5, midZ, Math.max(segLen - 5.0, 2.0), wallHeight, wallThick, this.PALETTE.gothicBrick);
        // Wooden wall-walk hoarding / gallery on inner face
        this.geo.addBox(midX, wallHeight - 0.4, midZ, segLen - 4.0, 0.8, wallThick + 0.8, this.PALETTE.timberFrame);
      }
    }
  }

  private buildCastleHill(_elements: CastleElement[]): void {
    // Castle Moat Wooden Bridge
    this.geo.addBox(220, 3.8, 38, 52, 0.8, 6.5, this.PALETTE.timberWeathered);
    // Bridge oak pilings
    for (let px = 200; px <= 240; px += 10) {
      this.geo.addBox(px, 1.5, 38, 1.4, 4.0, 6.5, this.PALETTE.timberFrame);
    }

    // Castle Outer Curtain Wall
    this.geo.addBox(280, 7.5, 35, 90, 7.0, 2.2, this.PALETTE.limestone);
    this.geo.addBox(330, 7.5, 85, 2.2, 7.0, 95, this.PALETTE.limestone);
    this.geo.addBox(280, 7.5, 135, 90, 7.0, 2.2, this.PALETTE.limestone);
    this.geo.addBox(230, 7.5, 85, 2.2, 7.0, 95, this.PALETTE.limestone);

    // Donjon (Romanesque Keep): Round limestone cylinder, 30m high
    const donjonX = 275;
    const donjonZ = 75;
    const donjonH = 30.0;
    const donjonR = 8.0;
    // Approximated by stacked octagon boxes for low-poly efficiency
    this.geo.addBox(donjonX, donjonH * 0.5 + 5.0, donjonZ, donjonR * 2, donjonH, donjonR * 2, this.PALETTE.limestone);
    // Battlements & observation gallery
    this.geo.addBox(donjonX, donjonH + 5.6, donjonZ, donjonR * 2 + 1.2, 1.8, donjonR * 2 + 1.2, this.PALETTE.limestone);
    // Royal Jagiełło Banner flagpole on Donjon
    this.geo.addBox(donjonX, donjonH + 9.0, donjonZ, 0.4, 6.0, 0.4, this.PALETTE.wroughtIron);
    this.geo.addBox(donjonX + 2.0, donjonH + 10.5, donjonZ, 3.5, 2.2, 0.1, [0.85, 0.15, 0.15, 1.0]); // Red Polish standard

    // Royal Holy Trinity Chapel (Kaplica Trójcy Świętej)
    const chapX = 260;
    const chapZ = 115;
    this.geo.addBox(chapX, 15.0, chapZ, 14, 20.0, 24, this.PALETTE.gothicBrick);
    // Gothic buttresses (pillars along chapel walls)
    for (let bz = chapZ - 10; bz <= chapZ + 10; bz += 6.5) {
      this.geo.addBox(chapX - 7.5, 14.0, bz, 1.8, 16.0, 1.6, this.PALETTE.limestone);
      this.geo.addBox(chapX + 7.5, 14.0, bz, 1.8, 16.0, 1.6, this.PALETTE.limestone);
    }
    // High steep chapel roof
    this.geo.addBox(chapX, 27.0, chapZ, 13.5, 6.0, 24, this.PALETTE.roofCeramicTile);
    // Slender gothic turret
    this.geo.addBox(chapX, 32.0, chapZ - 10, 2.4, 8.0, 2.4, this.PALETTE.copperRoof);

    // Royal Palace Hall (Dwór Królewski)
    const palX = 295;
    const palZ = 110;
    this.geo.addBox(palX, 14.0, palZ, 16, 18.0, 28, this.PALETTE.gothicBrick);
    this.geo.addBox(palX, 24.5, palZ, 16.5, 5.0, 28.5, this.PALETTE.roofCeramicTile);
  }

  private buildCivicLandmarks(_landmarks: CivicLandmark[]): void {
    // 1. Old Town Hall (Ratusz Miejski) in Rynek center
    // Dimensions 24m wide x 18m deep x 14m hall height + 32m clock tower
    const thX = 0;
    const thZ = 0;
    // Ground floor council arcades (podcienia)
    this.geo.addBox(thX, 2.0, thZ, 24.0, 4.0, 18.0, this.PALETTE.limestone);
    // Upper gothic brick chambers
    this.geo.addBox(thX, 8.5, thZ, 23.5, 9.0, 17.5, this.PALETTE.gothicBrick);
    // Battlemented attic with corner turrets
    this.geo.addBox(thX, 13.5, thZ, 24.5, 1.8, 18.5, this.PALETTE.gothicBrick);
    // 4 Corner Turrets
    for (const sx of [-11.5, 11.5]) {
      for (const sz of [-8.5, 8.5]) {
        this.geo.addBox(thX + sx, 15.0, thZ + sz, 2.2, 5.0, 2.2, this.PALETTE.limestone);
        this.geo.addBox(thX + sx, 18.0, thZ + sz, 2.4, 2.5, 2.4, this.PALETTE.copperRoof);
      }
    }
    // High central clock tower
    const towerH = 32.0;
    this.geo.addBox(thX, towerH * 0.5, thZ, 6.0, towerH, 6.0, this.PALETTE.gothicBrick);
    // Tower clock faces (all 4 sides)
    this.geo.addBox(thX, 24.0, thZ + 3.1, 2.8, 2.8, 0.2, this.PALETTE.gildedGold);
    this.geo.addBox(thX, 24.0, thZ - 3.1, 2.8, 2.8, 0.2, this.PALETTE.gildedGold);
    this.geo.addBox(thX + 3.1, 24.0, thZ, 0.2, 2.8, 2.8, this.PALETTE.gildedGold);
    this.geo.addBox(thX - 3.1, 24.0, thZ, 0.2, 2.8, 2.8, this.PALETTE.gildedGold);
    // Tower gallery & belfry
    this.geo.addBox(thX, 28.5, thZ, 7.2, 2.2, 7.2, this.PALETTE.limestone);
    // Octagonal copper spire
    this.geo.addBox(thX, 35.0, thZ, 5.5, 11.0, 5.5, this.PALETTE.copperRoof);

    // 2. Szmatruz (Cloth Hall) adjacent to Town Hall
    // 28m x 14m with 22 brick pillars and 16 vendor stalls
    const szX = 22.0;
    const szZ = -20.0;
    this.geo.addBox(szX, 4.5, szZ, 28.0, 9.0, 14.0, this.PALETTE.gothicBrick);
    // Steep roof
    this.geo.addBox(szX, 10.5, szZ, 28.5, 4.5, 14.5, this.PALETTE.roofCeramicTile);
    // Vendor stalls along aisle (awning rooflets in colorful fair stripes)
    for (let bx = -11; bx <= 11; bx += 3.5) {
      this.geo.addBox(szX + bx, 1.8, szZ + 7.6, 2.8, 2.2, 1.8, [0.78, 0.65, 0.25, 1.0]); // Ochre cloth stall
      this.geo.addBox(szX + bx, 1.8, szZ - 7.6, 2.8, 2.2, 1.8, [0.25, 0.45, 0.65, 1.0]); // Indigo cloth stall
    }

    // 3. St. Michael Archangel Collegiate Church (Fara)
    const faraX = 130.0;
    const faraZ = 20.0;
    // Massive nave and choir
    this.geo.addBox(faraX, 14.0, faraZ, 22.0, 24.0, 36.0, this.PALETTE.gothicBrick);
    this.geo.addBox(faraX, 28.0, faraZ, 22.5, 7.0, 36.5, this.PALETTE.roofCeramicTile);
    // Soaring 60m collegiate bell tower
    this.geo.addBox(faraX - 14.0, 26.0, faraZ, 10.0, 52.0, 10.0, this.PALETTE.gothicBrick);
    this.geo.addBox(faraX - 14.0, 56.0, faraZ, 9.0, 16.0, 9.0, this.PALETTE.copperRoof);

    // 4. Dominican Monastery & Basilica
    const domX = -60.0;
    const domZ = -90.0;
    this.geo.addBox(domX, 12.0, domZ, 26.0, 22.0, 40.0, this.PALETTE.gothicBrick);
    this.geo.addBox(domX, 24.5, domZ, 26.5, 6.0, 40.5, this.PALETTE.roofCeramicTile);
    // Cloister courtyard quadrangle
    this.geo.addBox(domX - 25.0, 5.0, domZ, 22.0, 8.0, 22.0, this.PALETTE.plasterWhite);
    this.geo.addBox(domX - 25.0, 1.0, domZ, 14.0, 0.2, 14.0, [0.35, 0.52, 0.28, 1.0]); // Cloister herb garden

    // 5. Town Pillory & Market Well
    this.geo.addBox(-15.0, 3.5, 12.0, 1.2, 5.0, 1.2, this.PALETTE.limestone);
    this.geo.addBox(-12.0, 1.2, -10.0, 3.5, 1.8, 3.5, this.PALETTE.limestone); // Stone well rim
    this.geo.addBox(-12.0, 3.2, -10.0, 3.8, 1.2, 3.8, this.PALETTE.roofShingle);   // Well rooflet
  }

  private buildParcelBuilding(p: Parcel): void {
    const px = p.x;
    const pz = p.z;
    const elev = p.elevation;
    const w = p.width;
    const d = p.depth;
    const aging = p.aging;
    const bType = p.buildingType;

    // Structural Aging influence
    // Lean angle: horizontal displacement at roof peak
    const leanRad = (aging.wallLeanAngle * Math.PI) / 180;
    const leanOffset = Math.sin(leanRad) * 4.0;
    const moss = aging.mossFoundation;

    if (p.isShed) {
      // 3 Shed Types
      const shH = 3.6;
      const shColor = bType.includes('open')
        ? this.PALETTE.timberWeathered
        : (bType.includes('wattle') ? this.PALETTE.plasterLoam : this.PALETTE.timberFrame);

      this.geo.addBox(px, elev + shH * 0.5, pz, w, shH, d, shColor);
      // Shed roof (lean-to sloped roof)
      this.geo.addBox(px, elev + shH + 0.4, pz, w + 0.6, 0.5, d + 0.6, this.PALETTE.roofShingle);
    } else {
      // 25 House Types
      const isPatrician = bType.includes('patrician');
      const isMerchant = bType.includes('merchant');
      const isThatched = bType.includes('thatched') || bType.includes('thatch');
      const isShingle = bType.includes('shingle') || bType.includes('timber') || bType.includes('cottage');
      const isStepped = bType.includes('stepped');

      // 1. Loess/Limestone Foundation with moss staining
      const foundH = 1.2;
      const foundColor: [number, number, number, number] = [
        this.PALETTE.limestone[0] * (1.0 - moss * 0.2),
        this.PALETTE.limestone[1] * (1.0 - moss * 0.05),
        this.PALETTE.limestone[2] * (1.0 - moss * 0.3),
        1.0
      ];
      this.geo.addBox(px, elev + foundH * 0.5, pz, w, foundH, d, foundColor);

      // 2. Ground Floor (Gothic brick or plaster/loam)
      const floor1H = 3.8;
      const floor1Color = (isPatrician || bType.includes('brick') || bType.includes('baker'))
        ? this.PALETTE.gothicBrick
        : (isMerchant ? this.PALETTE.plasterWhite : this.PALETTE.plasterLoam);

      this.geo.addBox(px, elev + foundH + floor1H * 0.5, pz, w - 0.2, floor1H, d - 0.2, floor1Color);

      // 3. Second Floor (Fachwerk Jetty with wood frame or patrician masonry)
      const floor2H = 3.4;
      const jettyOverhang = (isMerchant || bType.includes('fachwerk') || bType.includes('half_timber')) ? 0.5 : 0.0;
      const floor2W = w + jettyOverhang;
      const floor2D = d + jettyOverhang;
      const floor2Color = (isMerchant || bType.includes('half_timber') || bType.includes('workshop'))
        ? this.PALETTE.timberFrame
        : floor1Color;

      this.geo.addBox(
        px + leanOffset * 0.5,
        elev + foundH + floor1H + floor2H * 0.5,
        pz,
        floor2W, floor2H, floor2D,
        floor2Color
      );

      // 4. Medieval Roof & Gables
      const roofH = isPatrician ? 6.0 : (isThatched ? 5.5 : 4.5);
      const totalH = foundH + floor1H + floor2H;
      const roofPeakY = elev + totalH + roofH * 0.5 - aging.ridgeSag; // Sagging ridge!

      const roofColor = isThatched
        ? this.PALETTE.roofThatch
        : (isShingle ? this.PALETTE.roofShingle : this.PALETTE.roofCeramicTile);

      // Roof main prism
      this.geo.addBox(
        px + leanOffset,
        roofPeakY,
        pz,
        floor2W + 0.6, roofH, floor2D + 0.6,
        roofColor
      );

      // Stepped Gable feature for Patrician Kamienice
      if (isStepped) {
        this.geo.addBox(
          px + leanOffset,
          elev + totalH + roofH + 0.8,
          pz - floor2D * 0.48,
          floor2W * 0.7, 1.8, 0.6,
          this.PALETTE.gothicBrick
        );
        this.geo.addBox(
          px + leanOffset,
          elev + totalH + roofH + 2.2,
          pz - floor2D * 0.48,
          floor2W * 0.4, 1.4, 0.6,
          this.PALETTE.gothicBrick
        );
      }

      // Chimney for Bakeries, Blacksmiths, and large residences
      if (bType.includes('baker') || bType.includes('blacksmith') || isPatrician) {
        const chimX = px + w * 0.28;
        const chimZ = pz - d * 0.25;
        this.geo.addBox(chimX, elev + totalH + roofH + 1.2, chimZ, 1.2, 3.5, 1.2, this.PALETTE.gothicBrick);
      }

      // Hung Trade Sign (18 crafts)
      if (p.craft) {
        const signArmY = elev + foundH + floor1H * 0.8;
        const signZ = pz + d * 0.5 + 0.8;
        // Wrought iron bracket
        this.geo.addBox(px, signArmY, signZ, 0.2, 0.2, 1.4, this.PALETTE.wroughtIron);
        // Suspended emblematic sign board
        const signColor = (p.craft.id === 'goldsmith' || p.craft.id === 'armorer')
          ? this.PALETTE.gildedGold
          : [0.75, 0.25, 0.20, 1.0] as [number, number, number, number];
        this.geo.addBox(px, signArmY - 0.45, signZ + 0.4, 0.1, 0.6, 0.6, signColor);
      }

      // Active Building Site Scaffolding
      if (p.scaffolding) {
        // Timber scaffold poles and work planks
        const scafZ = pz + d * 0.5 + 1.2;
        this.geo.addBox(px - w * 0.4, elev + totalH * 0.5, scafZ, 0.3, totalH, 0.3, this.PALETTE.woodScaffold);
        this.geo.addBox(px + w * 0.4, elev + totalH * 0.5, scafZ, 0.3, totalH, 0.3, this.PALETTE.woodScaffold);
        this.geo.addBox(px, elev + totalH * 0.6, scafZ, w + 1.0, 0.25, 1.4, this.PALETTE.woodScaffold);
      }

      // Yard Clutter (Barrels, Firewood, Ladders, Hoops)
      if (p.clutter && p.clutter.length > 0) {
        for (let c = 0; c < p.clutter.length; c++) {
          const item = p.clutter[c];
          const cx = px + (c % 2 === 0 ? 1 : -1) * (w * 0.5 + 1.2 + c * 0.4);
          const cz = pz + (c > 1 ? 1 : -1) * (d * 0.3);

          if (item.includes('barrel') || item.includes('cask')) {
            this.geo.addBox(cx, elev + 0.5, cz, 0.9, 1.1, 0.9, this.PALETTE.timberWeathered);
          } else if (item.includes('firewood')) {
            this.geo.addBox(cx, elev + 0.45, cz, 1.8, 0.9, 0.8, this.PALETTE.timberFrame);
          } else if (item.includes('ladder')) {
            this.geo.addBox(cx, elev + 1.2, cz, 0.6, 2.4, 0.15, this.PALETTE.woodScaffold);
          } else {
            this.geo.addBox(cx, elev + 0.35, cz, 0.8, 0.5, 0.8, this.PALETTE.timberWeathered);
          }
        }
      }
    }
  }
}
