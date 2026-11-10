import type { CityPlan, Citizen, Parcel, BellHourInfo, FairEvent, StreetNode } from '../types';
import { SpatialHashGrid } from './spatial-hash';
import { IsometricCamera } from './camera';

export class SimulationEngine {
  public plan: CityPlan;
  public spatialGrid: SpatialHashGrid;

  // Time & Clock state
  public simTimeHours: number = 9.0; // Starts at 9:00 AM (Terce - Royal Fair Opening)
  public simSpeed: number = 5.0;     // 5x default
  public isPaused: boolean = false;
  public currentBellKey: string = 'terce';
  public currentBellInfo: BellHourInfo;

  // Parcels and Street Graph Lookup
  public parcelMap: Map<string, Parcel> = new Map();
  public streetNodeMap: Map<string, StreetNode> = new Map();
  public citizens: Citizen[] = [];

  // Active Selected Entity
  public selectedCitizen: Citizen | null = null;
  public selectedParcel: Parcel | null = null;

  // Events & Notifications
  public activeEvents: FairEvent[] = [];
  public onBellToll: ((bellName: string, hour: number) => void) | null = null;
  public onEventTriggered: ((event: FairEvent) => void) | null = null;

  private lastTriggeredBellHour: number = 9;
  private lastTriggeredEvents: Set<string> = new Set();

  constructor(plan: CityPlan, spatialGrid: SpatialHashGrid) {
    this.plan = plan;
    this.spatialGrid = spatialGrid;
    this.currentBellInfo = plan.bellHours['terce'];

    // Index parcels
    for (let i = 0; i < plan.parcels.length; i++) {
      const p = plan.parcels[i];
      this.parcelMap.set(p.id, p);
    }

    // Index street nodes
    for (let i = 0; i < plan.streetNetwork.nodes.length; i++) {
      const node = plan.streetNetwork.nodes[i];
      this.streetNodeMap.set(node.id, node);
    }

    // Initialize 1,500 Citizens with world positions
    this.citizens = plan.citizens;
    for (let i = 0; i < this.citizens.length; i++) {
      const c = this.citizens[i];
      const homeP = this.parcelMap.get(c.homeParcelId);
      const workP = this.parcelMap.get(c.workParcelId);

      // Start at home or work depending on initial time (9:00 AM -> working / fair)
      const startP = workP || homeP || plan.parcels[0];
      c.currentX = startP.x + (Math.random() - 0.5) * 4.0;
      c.currentZ = startP.z + (Math.random() - 0.5) * 4.0;
      c.targetX = c.currentX;
      c.targetZ = c.currentZ;
      c.animFrame = Math.random() * 10;
      c.isMoving = false;
      c.state = 'WORKING';
      c.currentTask = `Trading / working as ${c.trade}`;
    }

    // Index initial static parcels into spatial grid
    this.spatialGrid.indexParcels(plan.parcels);
  }

  public setSpeed(speed: number): void {
    this.simSpeed = speed;
    if (speed > 0) this.isPaused = false;
  }

  public togglePause(): boolean {
    this.isPaused = !this.isPaused;
    return this.isPaused;
  }

  public setTime(hour: number): void {
    this.simTimeHours = hour % 24.0;
    this.evaluateSchedules(true);
    this.checkBellHour();
  }

  public update(dt: number): void {
    if (this.isPaused) return;

    // Advance clock: at 1x speed, 1 real second = 1 simulation minute (0.01666 hours)
    const hoursPerSec = (1.0 / 60.0) * (this.simSpeed / 5.0);
    this.simTimeHours = (this.simTimeHours + dt * hoursPerSec) % 24.0;

    // Check civic bells & systemic events
    this.checkBellHour();
    this.checkSystemicEvents();

    // Clear and rebuild citizen spatial hash buckets
    this.spatialGrid.clearCitizens();

    // Update 1,500 citizens
    const currentHourInt = Math.floor(this.simTimeHours);
    const walkSpeed = 3.5 * Math.min(2.0, Math.max(1.0, this.simSpeed * 0.4)); // m/s adjusted for responsiveness

    for (let i = 0; i < this.citizens.length; i++) {
      const c = this.citizens[i];
      const cx = c.currentX ?? 0;
      const cz = c.currentZ ?? 0;

      // Update schedule task if hour changed
      this.updateCitizenTask(c, currentHourInt);

      // Move toward target
      const tx = c.targetX ?? cx;
      const tz = c.targetZ ?? cz;
      const dx = tx - cx;
      const dz = tz - cz;
      const dist = Math.hypot(dx, dz);

      if (dist > 0.8) {
        c.isMoving = true;
        const step = Math.min(dist, walkSpeed * dt);
        c.currentX = cx + (dx / dist) * step;
        c.currentZ = cz + (dz / dist) * step;
        c.animFrame = ((c.animFrame ?? 0) + dt * 8.0) % 8;
      } else {
        c.isMoving = false;
        // Jitter destination occasionally in workplace or market
        if (Math.random() < 0.008) {
          this.pickNewTargetForCitizen(c);
        }
      }

      // Re-index into spatial grid
      this.spatialGrid.insertCitizen(c, c.currentX!, c.currentZ!);
    }
  }

  private updateCitizenTask(c: Citizen, currentHour: number): void {
    // Find active schedule item for this hour
    let activeItem = c.schedule[0];
    for (let i = 0; i < c.schedule.length; i++) {
      if (currentHour >= c.schedule[i].hour) {
        activeItem = c.schedule[i];
      }
    }

    if (c.state !== activeItem.state) {
      c.state = activeItem.state;
      c.currentTask = activeItem.task;
      this.routeCitizenToLocation(c, activeItem.location);
    }
  }

  private routeCitizenToLocation(c: Citizen, locationId: string): void {
    let destX = 0;
    let destZ = 0;

    if (locationId === 'market_square') {
      // Rynek center jitter
      destX = (Math.random() - 0.5) * 55.0;
      destZ = (Math.random() - 0.5) * 40.0;
    } else if (locationId === 'curtain_wall') {
      // Wall ramparts
      const p = this.plan.defense.perimeterPoints[Math.floor(Math.random() * this.plan.defense.perimeterPoints.length)];
      destX = p.x;
      destZ = p.z;
    } else if (this.parcelMap.has(locationId)) {
      const p = this.parcelMap.get(locationId)!;
      destX = p.x + (Math.random() - 0.5) * 3.0;
      destZ = p.z + (Math.random() - 0.5) * 3.0;
    } else {
      // Street waypoint
      const node = this.streetNodeMap.get(locationId);
      if (node) {
        destX = node.x;
        destZ = node.z;
      } else {
        destX = (Math.random() - 0.5) * 20.0;
        destZ = (Math.random() - 0.5) * 20.0;
      }
    }

    c.targetX = destX;
    c.targetZ = destZ;
  }

  private pickNewTargetForCitizen(c: Citizen): void {
    if (c.state === 'WORKING' || c.state === 'SHOPPING_FAIR' || c.state === 'SOCIALIZING') {
      // Wander inside current district or market stall
      const wanderRadius = c.state === 'SHOPPING_FAIR' ? 18.0 : 6.0;
      c.targetX = (c.currentX ?? 0) + (Math.random() - 0.5) * wanderRadius;
      c.targetZ = (c.currentZ ?? 0) + (Math.random() - 0.5) * wanderRadius;
    }
  }

  private evaluateSchedules(_force: boolean = false): void {
    const curHour = Math.floor(this.simTimeHours);
    for (let i = 0; i < this.citizens.length; i++) {
      this.updateCitizenTask(this.citizens[i], curHour);
    }
  }

  private checkBellHour(): void {
    const hour = Math.floor(this.simTimeHours);
    if (hour !== this.lastTriggeredBellHour) {
      this.lastTriggeredBellHour = hour;

      // Find closest bell key
      for (const [key, info] of Object.entries(this.plan.bellHours)) {
        if (info.hour === hour) {
          this.currentBellKey = key;
          this.currentBellInfo = info;
          if (this.onBellToll) {
            this.onBellToll(info.name, info.hour);
          }
          break;
        }
      }
    }
  }

  private checkSystemicEvents(): void {
    const hour = Math.floor(this.simTimeHours);
    for (let i = 0; i < this.plan.fairEvents.length; i++) {
      const ev = this.plan.fairEvents[i];
      if (ev.triggerHour === hour && !this.lastTriggeredEvents.has(ev.id)) {
        this.lastTriggeredEvents.add(ev.id);
        this.activeEvents.unshift(ev);
        if (this.activeEvents.length > 5) this.activeEvents.pop();
        if (this.onEventTriggered) {
          this.onEventTriggered(ev);
        }
      } else if (ev.triggerHour !== hour && this.lastTriggeredEvents.has(ev.id)) {
        // Reset for next day cycle
        this.lastTriggeredEvents.delete(ev.id);
      }
    }
  }

  public tollCivicBellManually(): void {
    if (this.onBellToll) {
      this.onBellToll(this.currentBellInfo.name, Math.floor(this.simTimeHours));
    }
  }

  /**
   * Render dynamic 2.5D visual overlays:
   * - Citizen isometric avatars (Patricians, Artisans, Guards, Monks, Merchants)
   * - Selected rings, nameplates
   * - Foot traffic & heatmaps
   */
  public renderOverlay(ctx: CanvasRenderingContext2D, camera: IsometricCamera): void {
    const bounds = camera.getVisibleWorldBounds();
    const visibleCitizens = this.spatialGrid.queryCitizensInBounds(
      bounds.minX, bounds.maxX, bounds.minZ, bounds.maxZ
    );

    // Sort visible citizens by depth (rx + rz) for correct isometric painter's order
    const cosA = Math.cos(camera.currentRotationAngle);
    const sinA = Math.sin(camera.currentRotationAngle);

    visibleCitizens.sort((a, b) => {
      const ax = (a.currentX ?? 0) - camera.x;
      const az = (a.currentZ ?? 0) - camera.z;
      const bx = (b.currentX ?? 0) - camera.x;
      const bz = (b.currentZ ?? 0) - camera.z;

      const depthA = (ax * cosA - az * sinA) + (ax * sinA + az * cosA);
      const depthB = (bx * cosA - bz * sinA) + (bx * sinA + bz * cosA);
      return depthA - depthB;
    });

    const isZoomedIn = camera.zoom > 1.1;

    for (let i = 0; i < visibleCitizens.length; i++) {
      const c = visibleCitizens[i];
      const wx = c.currentX ?? 0;
      const wz = c.currentZ ?? 0;
      const screenPos = camera.worldToScreen(wx, 1.2, wz);
      const sx = screenPos.x;
      const sy = screenPos.y;

      const isSelected = this.selectedCitizen?.id === c.id;

      // Draw drop shadow
      ctx.fillStyle = 'rgba(20, 15, 10, 0.35)';
      ctx.beginPath();
      ctx.ellipse(sx, sy + 3 * camera.zoom, 5 * camera.zoom, 2.5 * camera.zoom, 0, 0, Math.PI * 2);
      ctx.fill();

      // Palette based on wealth/profession
      let tunicColor = '#8c7659'; // Artisan/Burgher brown
      let hatColor = '#3e2723';
      let heightPx = 14 * camera.zoom;

      if (c.trade.includes('Halberd') || c.trade.includes('Watch')) {
        tunicColor = '#b71c1c'; // Guard red tabard
        hatColor = '#90a4ae';   // Iron kettle helm
      } else if (c.trade.includes('Friar') || c.trade.includes('Vicar')) {
        tunicColor = '#4e342e'; // Dominican habit
        hatColor = '#d7ccc8';   // Tonsure
      } else if (c.wealthClass === 'patrician') {
        tunicColor = '#1565c0'; // Ultramarine patrician robe
        hatColor = '#ffd54f';   // Gilded cap
      } else if (c.guildRank === 'foreign_merchant') {
        tunicColor = '#2e7d32'; // Emerald cloth trader
        hatColor = '#ff8f00';   // Turban/feathered bonnet
      } else if (c.wealthClass === 'plebeian') {
        tunicColor = '#6d4c41';
        hatColor = '#a1887f';
      }

      // Draw stylized 2.5D citizen avatar
      const bob = c.isMoving ? Math.sin((c.animFrame ?? 0) * Math.PI) * 1.5 * camera.zoom : 0;

      // Body / Tunic
      ctx.fillStyle = tunicColor;
      ctx.beginPath();
      ctx.rect(sx - 3 * camera.zoom, sy - heightPx + bob, 6 * camera.zoom, heightPx);
      ctx.fill();

      // Head
      ctx.fillStyle = '#ffcc80'; // Skin tone
      ctx.beginPath();
      ctx.arc(sx, sy - heightPx - 3 * camera.zoom + bob, 3 * camera.zoom, 0, Math.PI * 2);
      ctx.fill();

      // Hat / Helm
      ctx.fillStyle = hatColor;
      ctx.beginPath();
      ctx.arc(sx, sy - heightPx - 4.5 * camera.zoom + bob, 3.2 * camera.zoom, Math.PI, Math.PI * 2);
      ctx.fill();

      // Halberd for guards
      if (c.trade.includes('Halberd')) {
        ctx.strokeStyle = '#cfd8dc';
        ctx.lineWidth = 1.5 * camera.zoom;
        ctx.beginPath();
        ctx.moveTo(sx + 4 * camera.zoom, sy);
        ctx.lineTo(sx + 4 * camera.zoom, sy - heightPx - 8 * camera.zoom);
        ctx.stroke();
      }

      // Selection ring
      if (isSelected) {
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.ellipse(sx, sy + 3 * camera.zoom, 10 * camera.zoom, 5 * camera.zoom, 0, 0, Math.PI * 2);
        ctx.stroke();

        // Citizen name badge
        ctx.fillStyle = 'rgba(15, 12, 10, 0.88)';
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 1;
        const tagText = `${c.name} (${c.trade})`;
        ctx.font = 'bold 12px serif';
        const tw = ctx.measureText(tagText).width;
        ctx.fillRect(sx - tw * 0.5 - 6, sy - heightPx - 26 * camera.zoom, tw + 12, 18);
        ctx.strokeRect(sx - tw * 0.5 - 6, sy - heightPx - 26 * camera.zoom, tw + 12, 18);
        ctx.fillStyle = '#fff8e7';
        ctx.fillText(tagText, sx - tw * 0.5, sy - heightPx - 13 * camera.zoom);
      } else if (isZoomedIn && camera.zoom > 1.8) {
        // Subtle name tag when closely zoomed in
        ctx.fillStyle = '#ffffff';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(c.name.split(' ')[0], sx, sy - heightPx - 8 * camera.zoom);
      }
    }

    // Selected parcel outline
    if (this.selectedParcel) {
      const p = this.selectedParcel;
      const screenPos = camera.worldToScreen(p.x, p.elevation + 0.1, p.z);
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 3;
      ctx.beginPath();
      // Draw parcel footprint diamond
      const hw = (p.width * 0.5) * camera.zoom;
      const hd = (p.depth * 0.5) * camera.zoom * 0.5;
      ctx.moveTo(screenPos.x, screenPos.y - hd);
      ctx.lineTo(screenPos.x + hw, screenPos.y);
      ctx.lineTo(screenPos.x, screenPos.y + hd);
      ctx.lineTo(screenPos.x - hw, screenPos.y);
      ctx.closePath();
      ctx.stroke();
    }
  }
}
