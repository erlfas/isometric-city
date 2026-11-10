import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { CityPlan, Citizen } from '../types';

export class ThreeIsometricRenderer {
  public scene: THREE.Scene;
  public camera: THREE.OrthographicCamera;
  public renderer: THREE.WebGLRenderer;
  private canvas: HTMLCanvasElement;

  // Camera navigation & isometric projection
  public targetPos = new THREE.Vector3(0, 0, 0);
  public currentPos = new THREE.Vector3(0, 0, 0);
  public zoom: number = 65.0; // World units visible (spacious city view)
  public targetZoom: number = 65.0;
  public rotationQuadrant: number = 0; // 0=SW, 1=NW, 2=NE, 3=SE
  public currentRotationAngle: number = 0;
  public targetRotationAngle: number = 0;

  // Lighting
  private dirLight: THREE.DirectionalLight;
  private hemiLight: THREE.HemisphereLight;
  private ambientLight: THREE.AmbientLight;

  // Loaded GLTF model templates
  public models: Map<string, THREE.Group> = new Map();
  public isLoaded: boolean = false;

  private groundPlane: THREE.Mesh;
  private citizenMeshes: Map<string, THREE.Group> = new Map();

  // Speech bubbles data
  public activeBubbles: { id: string; text: string; x: number; y: number; z: number; timer: number }[] = [];
  public hoveredCitizen: Citizen | null = null;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x4a6572); // Medieval daylight sky

    // Orthographic Isometric Camera
    const aspect = canvas.clientWidth / canvas.clientHeight || 16 / 9;
    this.camera = new THREE.OrthographicCamera(
      -this.zoom * aspect * 0.5,
      this.zoom * aspect * 0.5,
      this.zoom * 0.5,
      -this.zoom * 0.5,
      -500,
      1000
    );

    // Renderer setup with shadows
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.25;

    // Atmospheric lighting
    this.hemiLight = new THREE.HemisphereLight(0xfff8ee, 0x5a5448, 0.75);
    this.scene.add(this.hemiLight);

    this.ambientLight = new THREE.AmbientLight(0xcfd8dc, 0.5);
    this.scene.add(this.ambientLight);

    // Directional sunlight casting crisp isometric diagonal shadows (matching reference images)
    this.dirLight = new THREE.DirectionalLight(0xfffaed, 1.5);
    this.dirLight.position.set(-80, 130, -70);
    this.dirLight.castShadow = true;
    this.dirLight.shadow.mapSize.width = 2048;
    this.dirLight.shadow.mapSize.height = 2048;
    this.dirLight.shadow.camera.near = 10;
    this.dirLight.shadow.camera.far = 400;
    const d = 140;
    this.dirLight.shadow.camera.left = -d;
    this.dirLight.shadow.camera.right = d;
    this.dirLight.shadow.camera.top = d;
    this.dirLight.shadow.camera.bottom = -d;
    this.dirLight.shadow.bias = -0.0003;
    this.scene.add(this.dirLight);
    this.scene.add(this.dirLight.target);

    // Create ground terrain with cobblestone / dirt textures
    this.groundPlane = this.createGroundTerrain();
    this.scene.add(this.groundPlane);

    this.updateCameraTransform();
  }

  private createGroundTerrain(): THREE.Mesh {
    // Generate cobblestone & earth procedural canvas texture
    const texCanvas = document.createElement('canvas');
    texCanvas.width = 1024;
    texCanvas.height = 1024;
    const ctx = texCanvas.getContext('2d')!;

    // Base earth / cobblestone color
    ctx.fillStyle = '#655e52';
    ctx.fillRect(0, 0, 1024, 1024);

    // Draw stone paving grid with noise
    ctx.strokeStyle = '#4a4338';
    ctx.lineWidth = 2;
    for (let x = 0; x < 1024; x += 16) {
      for (let y = 0; y < 1024; y += 12) {
        const stoneShade = 90 + Math.floor(Math.sin(x * 0.1) * 15 + Math.cos(y * 0.1) * 15);
        ctx.fillStyle = `rgb(${stoneShade + 15}, ${stoneShade + 10}, ${stoneShade})`;
        ctx.fillRect(x + 1, y + 1, 14, 10);
      }
    }

    const groundTex = new THREE.CanvasTexture(texCanvas);
    groundTex.wrapS = THREE.RepeatWrapping;
    groundTex.wrapT = THREE.RepeatWrapping;
    groundTex.repeat.set(40, 40);

    const geo = new THREE.PlaneGeometry(600, 500, 32, 32);
    const mat = new THREE.MeshStandardMaterial({
      map: groundTex,
      roughness: 0.9,
      metalness: 0.05
    });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.y = 0;
    mesh.receiveShadow = true;

    // Green countryside outer border
    const grassGeo = new THREE.RingGeometry(180, 350, 32);
    const grassMat = new THREE.MeshStandardMaterial({
      color: 0x486b36,
      roughness: 0.95
    });
    const grassMesh = new THREE.Mesh(grassGeo, grassMat);
    grassMesh.rotation.x = -Math.PI / 2;
    grassMesh.position.y = 0.05;
    grassMesh.receiveShadow = true;
    this.scene.add(grassMesh);

    return mesh;
  }

  public async loadAllModels(): Promise<void> {
    const loader = new GLTFLoader();
    const modelNames = [
      'town_hall',
      'szmatruz',
      'market_stall_red_white',
      'market_stall_blue_white',
      'market_stall_yellow_white',
      'market_cart',
      'town_well',
      'house_timber_log',
      'house_half_timber',
      'house_patrician_brick',
      'curtain_wall',
      'curtain_tower',
      'tree_oak'
    ];

    console.log('[ThreeRenderer] Loading 13 Blender-authored GLB assets...');

    for (const name of modelNames) {
      try {
        const gltf = await loader.loadAsync(`/models/${name}.glb`);
        gltf.scene.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
          }
        });
        this.models.set(name, gltf.scene);
      } catch (err) {
        console.warn(`[ThreeRenderer] Failed loading /models/${name}.glb:`, err);
      }
    }

    this.isLoaded = true;
    console.log(`[ThreeRenderer] Successfully loaded ${this.models.size} 3D assets!`);
  }

  public populateCityScene(plan: CityPlan): void {
    if (!this.isLoaded) return;

    // 1. Place Old Town Hall at Market Square center
    const townHallTemplate = this.models.get('town_hall');
    if (townHallTemplate) {
      const th = townHallTemplate.clone();
      th.position.set(0, 0, 0);
      th.rotation.y = 0;
      this.scene.add(th);
    }

    // 2. Place Szmatruz (Cloth Hall)
    const szmatruzTemplate = this.models.get('szmatruz');
    if (szmatruzTemplate) {
      const sz = szmatruzTemplate.clone();
      sz.position.set(22, 0, -18);
      sz.rotation.y = Math.PI / 2;
      this.scene.add(sz);
    }

    // 3. Place Municipal Well and Pillory in the square
    const wellTemplate = this.models.get('town_well');
    if (wellTemplate) {
      const well = wellTemplate.clone();
      well.position.set(-14, 0, 10);
      this.scene.add(well);
    }

    // 4. Place Vibrant Royal Fair Market Stalls and Carts across Rynek
    const stallTypes = ['market_stall_red_white', 'market_stall_blue_white', 'market_stall_yellow_white'];
    const stallCoords = [
      { x: -16, z: -14, rot: 0 },
      { x: -10, z: -14, rot: 0 },
      { x: -4, z: -14, rot: 0 },
      { x: 10, z: -14, rot: 0 },
      { x: 16, z: -14, rot: 0 },
      { x: -16, z: 14, rot: Math.PI },
      { x: -10, z: 14, rot: Math.PI },
      { x: -4, z: 14, rot: Math.PI },
      { x: 10, z: 14, rot: Math.PI },
      { x: 16, z: 14, rot: Math.PI },
      { x: -22, z: -6, rot: Math.PI / 2 },
      { x: -22, z: 2, rot: Math.PI / 2 },
      { x: -22, z: 8, rot: Math.PI / 2 },
      { x: 26, z: -6, rot: -Math.PI / 2 },
      { x: 26, z: 2, rot: -Math.PI / 2 }
    ];

    stallCoords.forEach((coord, idx) => {
      const type = stallTypes[idx % stallTypes.length];
      const tmpl = this.models.get(type);
      if (tmpl) {
        const stall = tmpl.clone();
        stall.position.set(coord.x, 0, coord.z);
        stall.rotation.y = coord.rot;
        this.scene.add(stall);
      }
    });

    // Market carts with spoked wheels
    const cartTemplate = this.models.get('market_cart');
    if (cartTemplate) {
      const cartPositions = [
        { x: -24, z: -18, rot: 0.4 },
        { x: 22, z: -26, rot: -0.6 },
        { x: -24, z: 16, rot: 1.2 },
        { x: 6, z: 18, rot: -0.8 },
        { x: -2, z: -20, rot: 1.8 }
      ];
      cartPositions.forEach(pos => {
        const cart = cartTemplate.clone();
        cart.position.set(pos.x, 0, pos.z);
        cart.rotation.y = pos.rot;
        this.scene.add(cart);
      });
    }

    // 5. Build Defensive Curtain Wall and Towers around Perimeter
    const wallTemplate = this.models.get('curtain_wall');
    const towerTemplate = this.models.get('curtain_tower');
    const perimeter = plan.defense.perimeterPoints;

    for (let i = 0; i < perimeter.length; i++) {
      const p1 = perimeter[i];
      const p2 = perimeter[(i + 1) % perimeter.length];

      // Add Tower
      if (towerTemplate) {
        const tower = towerTemplate.clone();
        tower.position.set(p1.x, 0, p1.z);
        this.scene.add(tower);
      }

      // Add Wall Segment
      if (wallTemplate && p1.id !== 'gate_grodzka') {
        const midX = (p1.x + p2.x) * 0.5;
        const midZ = (p1.z + p2.z) * 0.5;
        const dx = p2.x - p1.x;
        const dz = p2.z - p1.z;
        const segLen = Math.hypot(dx, dz);
        const angle = Math.atan2(dx, dz);

        const wall = wallTemplate.clone();
        wall.position.set(midX, 0, midZ);
        wall.rotation.y = angle + Math.PI / 2;
        wall.scale.set(segLen / 16.0, 1.0, 1.0);
        this.scene.add(wall);
      }
    }

    // 6. Populate 580 Parcels with Authentic Low-Poly Houses (Varied styles)
    const houseTemplates = [
      this.models.get('house_timber_log'),
      this.models.get('house_half_timber'),
      this.models.get('house_patrician_brick')
    ].filter(Boolean) as THREE.Group[];

    for (let i = 0; i < plan.parcels.length; i++) {
      const p = plan.parcels[i];
      // Alternate styles to prevent identical consecutive buildings along street fronts
      const tmplIdx = i % houseTemplates.length;
      const tmpl = houseTemplates[tmplIdx];

      if (tmpl) {
        const house = tmpl.clone();
        let posX = p.x;
        let posZ = p.z;

        // Provide 8m setback for market square frontage to keep plaza spacious
        if (p.district === 'market_square') {
          const distFromCenter = Math.hypot(p.x, p.z);
          if (distFromCenter > 1) {
            posX += (p.x / distFromCenter) * 8.0;
            posZ += (p.z / distFromCenter) * 8.0;
          }
        }

        house.position.set(posX, p.elevation * 0.3, posZ);
        house.rotation.y = (p.orientation * Math.PI) / 180;
        const scaleX = (p.width / 9.0) * 0.95;
        const scaleZ = (p.depth / 12.0) * 0.95;
        house.scale.set(scaleX, 1.0, scaleZ);
        house.userData = { parcelId: p.id };
        this.scene.add(house);
      }
    }

    // 7. Place Medieval Oak Trees along roads and outer green verge
    const treeTemplate = this.models.get('tree_oak');
    if (treeTemplate) {
      for (let t = 0; t < 75; t++) {
        const tree = treeTemplate.clone();
        // Place along outer perimeter
        const ang = Math.random() * Math.PI * 2;
        const dist = 160 + Math.random() * 80;
        tree.position.set(Math.cos(ang) * dist, 0, Math.sin(ang) * dist);
        const s = 0.8 + Math.random() * 0.6;
        tree.scale.set(s, s, s);
        tree.rotation.y = Math.random() * Math.PI * 2;
        this.scene.add(tree);
      }
    }

    console.log('[ThreeRenderer] Full medieval city populated successfully!');
  }

  public updateCitizens(citizens: Citizen[], _dt: number): void {
    // Maintain 3D citizen group objects
    for (let i = 0; i < citizens.length; i++) {
      const c = citizens[i];
      let group = this.citizenMeshes.get(c.id);

      if (!group) {
        // Create 3D citizen figure
        group = new THREE.Group();

        // Tunic color based on status
        let color = 0x8d6e63;
        if (c.trade.includes('Halberd') || c.trade.includes('Watch')) color = 0xc62828; // Guard red
        else if (c.trade.includes('Friar')) color = 0x4e342e; // Monk
        else if (c.wealthClass === 'patrician') color = 0x1565c0; // Patrician blue
        else if (c.guildRank === 'foreign_merchant') color = 0x2e7d32; // Merchant green

        // Body
        const bodyGeo = new THREE.CylinderGeometry(0.25, 0.35, 1.3, 8);
        const bodyMat = new THREE.MeshStandardMaterial({ color, roughness: 0.8 });
        const body = new THREE.Mesh(bodyGeo, bodyMat);
        body.position.y = 0.65;
        body.castShadow = true;
        group.add(body);

        // Head
        const headGeo = new THREE.SphereGeometry(0.2, 8, 8);
        const headMat = new THREE.MeshStandardMaterial({ color: 0xffcc80, roughness: 0.6 });
        const head = new THREE.Mesh(headGeo, headMat);
        head.position.y = 1.45;
        group.add(head);

        // Hat / Hood
        const hatGeo = new THREE.ConeGeometry(0.26, 0.28, 8);
        const hatMat = new THREE.MeshStandardMaterial({ color: 0x212121, roughness: 0.9 });
        const hat = new THREE.Mesh(hatGeo, hatMat);
        hat.position.y = 1.62;
        group.add(hat);

        // Halberd for guards
        if (c.trade.includes('Halberd')) {
          const halGeo = new THREE.CylinderGeometry(0.02, 0.02, 2.2, 6);
          const halMat = new THREE.MeshStandardMaterial({ color: 0x90a4ae, metalness: 0.8 });
          const hal = new THREE.Mesh(halGeo, halMat);
          hal.position.set(0.25, 1.1, 0);
          group.add(hal);
        }

        group.userData = { citizenId: c.id };
        this.scene.add(group);
        this.citizenMeshes.set(c.id, group);
      }

      // Update position
      const cx = c.currentX ?? 0;
      const cz = c.currentZ ?? 0;
      group.position.set(cx, 0, cz);

      // Walking bob
      if (c.isMoving) {
        group.position.y = Math.abs(Math.sin((c.animFrame ?? 0) * Math.PI)) * 0.12;
      }
    }
  }

  public updateCamera(dt: number): void {
    // Smooth camera center lerping
    this.currentPos.lerp(this.targetPos, Math.min(1.0, dt * 8.0));
    this.zoom += (this.targetZoom - this.zoom) * Math.min(1.0, dt * 10.0);

    // Smooth rotation angle lerping
    let diff = this.targetRotationAngle - this.currentRotationAngle;
    while (diff < -Math.PI) diff += Math.PI * 2;
    while (diff > Math.PI) diff -= Math.PI * 2;
    this.currentRotationAngle += diff * Math.min(1.0, dt * 8.0);

    this.updateCameraTransform();
  }

  private updateCameraTransform(): void {
    const aspect = this.canvas.clientWidth / this.canvas.clientHeight || 16 / 9;
    this.camera.left = -this.zoom * aspect * 0.5;
    this.camera.right = this.zoom * aspect * 0.5;
    this.camera.top = this.zoom * 0.5;
    this.camera.bottom = -this.zoom * 0.5;
    this.camera.updateProjectionMatrix();

    // Classic 35.264° true isometric / 30° dimetric projection
    const isoDist = 120.0;
    const yaw = this.currentRotationAngle + Math.PI / 4;
    const pitch = 0.615479; // ~35.264°

    const camX = this.currentPos.x + Math.sin(yaw) * Math.cos(pitch) * isoDist;
    const camY = this.currentPos.y + Math.sin(pitch) * isoDist;
    const camZ = this.currentPos.z + Math.cos(yaw) * Math.cos(pitch) * isoDist;

    this.camera.position.set(camX, camY, camZ);
    this.camera.lookAt(this.currentPos);

    // Update sunlight position relative to camera target
    this.dirLight.position.set(this.currentPos.x + 80, this.currentPos.y + 140, this.currentPos.z + 60);
    this.dirLight.target.position.copy(this.currentPos);
  }

  public setRotationQuadrant(q: number): void {
    this.rotationQuadrant = ((q % 4) + 4) % 4;
    this.targetRotationAngle = (this.rotationQuadrant * Math.PI) / 2;
  }

  public rotateClockwise(): void {
    this.setRotationQuadrant(this.rotationQuadrant + 1);
  }

  public rotateCounterClockwise(): void {
    this.setRotationQuadrant(this.rotationQuadrant - 1);
  }

  public panBy(dx: number, dy: number): void {
    const invZoom = this.zoom / this.canvas.clientHeight;
    const yaw = this.currentRotationAngle;
    const cosY = Math.cos(yaw);
    const sinY = Math.sin(yaw);

    // Unproject delta screen coordinates
    const wx = (dx * cosY + dy * sinY) * invZoom * 1.5;
    const wz = (-dx * sinY + dy * cosY) * invZoom * 1.5;

    this.targetPos.x += wx;
    this.targetPos.z += wz;
  }

  public zoomBy(factor: number): void {
    this.targetZoom = Math.max(8.0, Math.min(90.0, this.targetZoom * factor));
  }

  public jumpTo(x: number, z: number, zoomLevel?: number): void {
    this.targetPos.set(x, 0, z);
    if (zoomLevel) this.targetZoom = zoomLevel;
  }

  public updateDayNightLighting(hour: number): void {
    // Dynamic sun position and warm color grading
    if (hour >= 5 && hour < 8) {
      // Dawn
      this.dirLight.color.setHex(0xffaa66);
      this.dirLight.intensity = 0.9;
      this.ambientLight.color.setHex(0x5c4238);
      this.scene.background = new THREE.Color(0x735348);
    } else if (hour >= 8 && hour < 17) {
      // High Fair Noon: bright golden sun with crisp shadows
      this.dirLight.color.setHex(0xfffaed);
      this.dirLight.intensity = 1.45;
      this.ambientLight.color.setHex(0xdde3ea);
      this.scene.background = new THREE.Color(0x3a4f63);
    } else if (hour >= 17 && hour < 21) {
      // Dusk
      this.dirLight.color.setHex(0xff7744);
      this.dirLight.intensity = 0.85;
      this.ambientLight.color.setHex(0x382c44);
      this.scene.background = new THREE.Color(0x483244);
    } else {
      // Night Curfew: deep blue moonlight
      this.dirLight.color.setHex(0x5577aa);
      this.dirLight.intensity = 0.35;
      this.ambientLight.color.setHex(0x181e28);
      this.scene.background = new THREE.Color(0x0a1018);
    }
  }

  public triggerSpeechBubble(citizenId: string, text: string, x: number, z: number): void {
    this.activeBubbles.push({
      id: citizenId,
      text,
      x,
      y: 2.2,
      z,
      timer: 4.5 // seconds
    });
  }

  public updateSpeechBubbles(dt: number): void {
    for (let i = this.activeBubbles.length - 1; i >= 0; i--) {
      this.activeBubbles[i].timer -= dt;
      if (this.activeBubbles[i].timer <= 0) {
        this.activeBubbles.splice(i, 1);
      }
    }
  }

  /**
   * Project 3D world position to 2D canvas screen coordinate
   */
  public worldToScreen(wx: number, wy: number, wz: number): { x: number; y: number } {
    const v = new THREE.Vector3(wx, wy, wz);
    v.project(this.camera);
    const x = (v.x * 0.5 + 0.5) * this.canvas.clientWidth;
    const y = (-(v.y * 0.5) + 0.5) * this.canvas.clientHeight;
    return { x, y };
  }

  public render(): void {
    this.renderer.render(this.scene, this.camera);
  }

  public resize(width: number, height: number): void {
    this.renderer.setSize(width, height, false);
    this.updateCameraTransform();
  }
}
