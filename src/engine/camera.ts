import type { CameraQuadrant } from '../types';

export class IsometricCamera {
  public x: number = 0;       // Center world X
  public z: number = 0;       // Center world Z
  public targetX: number = 0;
  public targetZ: number = 0;

  public zoom: number = 1.0;
  public targetZoom: number = 1.0;

  public rotationQuadrant: CameraQuadrant = 0; // 0=SW, 1=NW, 2=NE, 3=SE
  public targetRotationAngle: number = 0;      // radians
  public currentRotationAngle: number = 0;     // smoothed radians

  public viewportWidth: number = 1280;
  public viewportHeight: number = 720;

  public followingEntityId: string | null = null;

  // Isometric projection constants: 2:1 dimetric ratio
  // cos(30°) and sin(30°) or 2:1 angle
  private readonly ISO_X_RATIO = 1.0;
  private readonly ISO_Y_RATIO = 0.5;

  constructor(width: number, height: number) {
    this.viewportWidth = width;
    this.viewportHeight = height;
    // Default focus on Market Square (Rynek)
    this.x = 0;
    this.z = 0;
    this.targetX = 0;
    this.targetZ = 0;
  }

  public resize(width: number, height: number): void {
    this.viewportWidth = width;
    this.viewportHeight = height;
  }

  public setRotationQuadrant(quadrant: CameraQuadrant): void {
    this.rotationQuadrant = quadrant;
    this.targetRotationAngle = (quadrant * Math.PI) / 2;
  }

  public rotateClockwise(): void {
    const nextQ = ((this.rotationQuadrant + 1) % 4) as CameraQuadrant;
    this.setRotationQuadrant(nextQ);
  }

  public rotateCounterClockwise(): void {
    const prevQ = ((this.rotationQuadrant + 3) % 4) as CameraQuadrant;
    this.setRotationQuadrant(prevQ);
  }

  public panBy(dx: number, dy: number): void {
    // Un-project screen delta to world delta based on current rotation
    this.followingEntityId = null; // Break follow lock
    const invZoom = 1.0 / this.zoom;
    const cosA = Math.cos(-this.currentRotationAngle);
    const sinA = Math.sin(-this.currentRotationAngle);

    // Invert dimetric projection:
    // dx_screen = (rx - rz) * zoom
    // dy_screen = (rx + rz) * 0.5 * zoom
    const rx = (dx / this.ISO_X_RATIO + dy / this.ISO_Y_RATIO) * 0.5 * invZoom;
    const rz = (-dx / this.ISO_X_RATIO + dy / this.ISO_Y_RATIO) * 0.5 * invZoom;

    // Rotate back to world space
    const wx = rx * cosA - rz * sinA;
    const wz = rx * sinA + rz * cosA;

    this.targetX += wx;
    this.targetZ += wz;
  }

  public zoomBy(factor: number, cursorX?: number, cursorY?: number): void {
    const oldZoom = this.targetZoom;
    const newZoom = Math.max(0.35, Math.min(3.2, oldZoom * factor));
    this.targetZoom = newZoom;

    if (cursorX !== undefined && cursorY !== undefined) {
      // Zoom centered at cursor
    }
  }

  public jumpTo(x: number, z: number, zoomLevel?: number): void {
    this.targetX = x;
    this.targetZ = z;
    this.x = x;
    this.z = z;
    if (zoomLevel !== undefined) {
      this.targetZoom = zoomLevel;
      this.zoom = zoomLevel;
    }
  }

  public smoothJumpTo(x: number, z: number, zoomLevel?: number): void {
    this.targetX = x;
    this.targetZ = z;
    if (zoomLevel !== undefined) {
      this.targetZoom = zoomLevel;
    }
  }

  public follow(entityId: string, x: number, z: number): void {
    this.followingEntityId = entityId;
    this.targetX = x;
    this.targetZ = z;
  }

  public stopFollowing(): void {
    this.followingEntityId = null;
  }

  public update(dt: number): void {
    const lerpRate = Math.min(1.0, dt * 10.0);
    this.x += (this.targetX - this.x) * lerpRate;
    this.z += (this.targetZ - this.z) * lerpRate;
    this.zoom += (this.targetZoom - this.zoom) * lerpRate;

    // Smooth angle interpolation
    let angleDiff = this.targetRotationAngle - this.currentRotationAngle;
    while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
    while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
    this.currentRotationAngle += angleDiff * Math.min(1.0, dt * 8.0);
  }

  /**
   * Transforms 3D world coordinates (wx, wy, wz) into 2D canvas screen coordinates (sx, sy).
   */
  public worldToScreen(wx: number, wy: number, wz: number): { x: number; y: number } {
    // 1. Center relative to camera
    const dx = wx - this.x;
    const dz = wz - this.z;

    // 2. Rotate around Y axis
    const cosA = Math.cos(this.currentRotationAngle);
    const sinA = Math.sin(this.currentRotationAngle);
    const rx = dx * cosA - dz * sinA;
    const rz = dx * sinA + dz * cosA;

    // 3. Project to dimetric (2:1 isometric)
    const isoX = (rx - rz) * this.ISO_X_RATIO;
    const isoY = (rx + rz) * this.ISO_Y_RATIO - wy;

    // 4. Scale and center on canvas
    const sx = this.viewportWidth * 0.5 + isoX * this.zoom;
    const sy = this.viewportHeight * 0.5 + isoY * this.zoom;

    return { x: sx, y: sy };
  }

  /**
   * Raycast ground plane unprojection: screen coordinate (sx, sy) -> world ground (wx, wz) at elevation Y=0.
   */
  public screenToWorld(sx: number, sy: number, groundY: number = 0): { x: number; z: number } {
    const isoX = (sx - this.viewportWidth * 0.5) / this.zoom;
    const isoY = (sy - this.viewportHeight * 0.5) / this.zoom + groundY;

    // Invert dimetric projection
    const rx = (isoX / this.ISO_X_RATIO + isoY / this.ISO_Y_RATIO) * 0.5;
    const rz = (-isoX / this.ISO_X_RATIO + isoY / this.ISO_Y_RATIO) * 0.5;

    // Invert rotation
    const cosA = Math.cos(-this.currentRotationAngle);
    const sinA = Math.sin(-this.currentRotationAngle);
    const wx = rx * cosA - rz * sinA + this.x;
    const wz = rx * sinA + rz * cosA + this.z;

    return { x: wx, z: wz };
  }

  /**
   * Get world-space axis-aligned bounding box of currently visible ground region
   * Used for spatial hash culling.
   */
  public getVisibleWorldBounds(): { minX: number; maxX: number; minZ: number; maxZ: number } {
    const p1 = this.screenToWorld(-100, -100);
    const p2 = this.screenToWorld(this.viewportWidth + 100, -100);
    const p3 = this.screenToWorld(this.viewportWidth + 100, this.viewportHeight + 100);
    const p4 = this.screenToWorld(-100, this.viewportHeight + 100);

    const minX = Math.min(p1.x, p2.x, p3.x, p4.x);
    const maxX = Math.max(p1.x, p2.x, p3.x, p4.x);
    const minZ = Math.min(p1.z, p2.z, p3.z, p4.z);
    const maxZ = Math.max(p1.z, p2.z, p3.z, p4.z);

    return { minX, maxX, minZ, maxZ };
  }
}
