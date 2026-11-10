import type { Citizen, Parcel } from '../types';
import { SimulationEngine } from '../engine/simulation';
import { IsometricCamera } from '../engine/camera';

export class UIController {
  private sim: SimulationEngine;
  private camera: IsometricCamera;

  // DOM elements
  private clockEl!: HTMLElement;
  private bellNameEl!: HTMLElement;
  private playPauseBtn!: HTMLElement;
  private inspectorPanel!: HTMLElement;
  private inspectorContent!: HTMLElement;
  private eventTickerEl!: HTMLElement;

  constructor(sim: SimulationEngine, camera: IsometricCamera) {
    this.sim = sim;
    this.camera = camera;
    this.bindDOMElements();
    this.setupEventListeners();
  }

  private bindDOMElements(): void {
    this.clockEl = document.getElementById('hud-time')!;
    this.bellNameEl = document.getElementById('hud-bell-name')!;
    this.playPauseBtn = document.getElementById('btn-play-pause')!;
    this.inspectorPanel = document.getElementById('inspector-panel')!;
    this.inspectorContent = document.getElementById('inspector-content')!;
    this.eventTickerEl = document.getElementById('event-ticker-text')!;
  }

  private setupEventListeners(): void {
    // Play / Pause
    this.playPauseBtn.addEventListener('click', () => {
      const isPaused = this.sim.togglePause();
      this.playPauseBtn.textContent = isPaused ? '▶ Resume' : '⏸ Pause';
      this.playPauseBtn.classList.toggle('active', !isPaused);
    });

    // Speed buttons
    document.querySelectorAll('[data-speed]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('[data-speed]').forEach(b => b.classList.remove('active'));
        const el = e.currentTarget as HTMLElement;
        el.classList.add('active');
        const spd = parseFloat(el.getAttribute('data-speed') || '5');
        this.sim.setSpeed(spd);
      });
    });

    // Time Jump buttons
    document.querySelectorAll('[data-jump-hour]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const hour = parseFloat((e.currentTarget as HTMLElement).getAttribute('data-jump-hour') || '9');
        this.sim.setTime(hour);
      });
    });

    // Camera Rotation
    document.getElementById('btn-rotate-cw')?.addEventListener('click', () => {
      this.camera.rotateClockwise();
      this.updateCompass();
    });
    document.getElementById('btn-rotate-ccw')?.addEventListener('click', () => {
      this.camera.rotateCounterClockwise();
      this.updateCompass();
    });

    // Camera Zoom
    document.getElementById('btn-zoom-in')?.addEventListener('click', () => {
      this.camera.zoomBy(1.25);
    });
    document.getElementById('btn-zoom-out')?.addEventListener('click', () => {
      this.camera.zoomBy(0.8);
    });

    // Landmark Quick Jumps
    document.querySelectorAll('[data-landmark]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const landmark = (e.currentTarget as HTMLElement).getAttribute('data-landmark');
        if (landmark === 'rynek') {
          this.camera.smoothJumpTo(0, 0, 1.4);
        } else if (landmark === 'krakow_gate') {
          this.camera.smoothJumpTo(-160, -80, 1.5);
        } else if (landmark === 'grodzka_gate') {
          this.camera.smoothJumpTo(190, 20, 1.5);
        } else if (landmark === 'castle') {
          this.camera.smoothJumpTo(275, 85, 1.3);
        } else if (landmark === 'workshop') {
          this.camera.smoothJumpTo(-235, -120, 1.6);
        }
      });
    });

    // Close Inspector
    document.getElementById('btn-close-inspector')?.addEventListener('click', () => {
      this.closeInspector();
    });

    // Toll Bell Manually
    document.getElementById('btn-toll-bell')?.addEventListener('click', () => {
      this.sim.tollCivicBellManually();
    });
  }

  private updateCompass(): void {
    const directions = ['SW (Kraków Rd)', 'NW (Czechówka Valley)', 'NE (Castle Hill)', 'SE (Bystrzyca)'];
    const el = document.getElementById('compass-heading');
    if (el) {
      el.textContent = directions[this.camera.rotationQuadrant];
    }
  }

  public updateHUD(): void {
    // Format hour and minute
    const hours = Math.floor(this.sim.simTimeHours);
    const mins = Math.floor((this.sim.simTimeHours % 1) * 60);
    const hh = String(hours).padStart(2, '0');
    const mm = String(mins).padStart(2, '0');

    this.clockEl.textContent = `${hh}:${mm}`;
    this.bellNameEl.textContent = this.sim.currentBellInfo.name;

    // Follow camera if an entity is tracked
    if (this.camera.followingEntityId && this.sim.selectedCitizen) {
      const c = this.sim.selectedCitizen;
      this.camera.targetX = c.currentX ?? this.camera.targetX;
      this.camera.targetZ = c.currentZ ?? this.camera.targetZ;
    }
  }

  public showEventNotification(text: string): void {
    if (this.eventTickerEl) {
      this.eventTickerEl.textContent = text;
      this.eventTickerEl.parentElement?.classList.add('flash');
      setTimeout(() => {
        this.eventTickerEl.parentElement?.classList.remove('flash');
      }, 3000);
    }
  }

  public inspectCitizen(c: Citizen): void {
    this.sim.selectedCitizen = c;
    this.sim.selectedParcel = null;

    const isFollowing = this.camera.followingEntityId === c.id;

    const homeP = this.sim.parcelMap.get(c.homeParcelId);
    const workP = this.sim.parcelMap.get(c.workParcelId);

    const scheduleRows = c.schedule.map((item) => {
      const isActive = Math.floor(this.sim.simTimeHours) >= item.hour &&
        (!c.schedule.find(next => next.hour > item.hour && Math.floor(this.sim.simTimeHours) >= next.hour));
      return `
        <div class="schedule-item ${isActive ? 'active-schedule' : ''}">
          <span class="sched-hour">${String(item.hour).padStart(2, '0')}:00</span>
          <span class="sched-state badge-${item.state.toLowerCase()}">${item.state}</span>
          <span class="sched-task">${item.task}</span>
        </div>
      `;
    }).join('');

    this.inspectorContent.innerHTML = `
      <div class="inspector-header">
        <div class="avatar-box class-${c.wealthClass}">
          <span>${c.gender === 'male' ? '🧔' : '👩'}</span>
        </div>
        <div class="header-info">
          <h3>${c.name}</h3>
          <div class="sub-badge badge-${c.wealthClass}">${c.wealthClass.toUpperCase()} • ${c.guildRank.replace('_', ' ').toUpperCase()}</div>
          <div class="trade-title">⚒️ ${c.trade}</div>
        </div>
      </div>

      <div class="action-bar">
        <button id="btn-follow-citizen" class="action-btn ${isFollowing ? 'active' : ''}">
          ${isFollowing ? '👁 Following (Tracking Camera)' : '🔍 Track Citizen'}
        </button>
      </div>

      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Current Action</div>
          <div class="stat-val highlight">${c.currentTask || 'Working'}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Purse (Wealth)</div>
          <div class="stat-val">💰 ${c.walletGroschen} Kraków Grosze</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Carrying</div>
          <div class="stat-val">📦 ${c.carriedItem}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Residence</div>
          <div class="stat-val link-parcel" data-parcel-id="${c.homeParcelId}">
            🏠 ${homeP?.streetName || c.homeParcelId} (Bed #${c.bedNumber})
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Workplace / Stall</div>
          <div class="stat-val link-parcel" data-parcel-id="${c.workParcelId}">
            🏢 ${workP?.name || workP?.streetName || c.workParcelId}
          </div>
        </div>
      </div>

      <h4 class="section-title">⏰ Daily Clockwork Schedule (Civic Bells)</h4>
      <div class="schedule-list">
        ${scheduleRows}
      </div>
    `;

    // Follow toggle event
    document.getElementById('btn-follow-citizen')?.addEventListener('click', () => {
      if (this.camera.followingEntityId === c.id) {
        this.camera.stopFollowing();
        this.inspectCitizen(c);
      } else {
        this.camera.follow(c.id, c.currentX ?? 0, c.currentZ ?? 0);
        this.inspectCitizen(c);
      }
    });

    // Link to parcels
    this.inspectorContent.querySelectorAll('.link-parcel').forEach((el) => {
      el.addEventListener('click', (e) => {
        const pid = (e.currentTarget as HTMLElement).getAttribute('data-parcel-id');
        if (pid && this.sim.parcelMap.has(pid)) {
          this.inspectParcel(this.sim.parcelMap.get(pid)!);
        }
      });
    });

    this.inspectorPanel.classList.add('open');
  }

  public inspectParcel(p: Parcel): void {
    this.sim.selectedParcel = p;
    this.sim.selectedCitizen = null;
    this.camera.stopFollowing();

    const aging = p.aging;
    const sagMm = Math.round(aging.ridgeSag * 1000);

    const residentTags = p.residents.map(cid => {
      const cit = this.sim.citizens.find(c => c.id === cid);
      return `<button class="citizen-pill" data-cit-id="${cid}">👤 ${cit?.name || cid}</button>`;
    }).join('') || '<em>No permanent residents</em>';

    const workerTags = p.workplaceFor.map(cid => {
      const cit = this.sim.citizens.find(c => c.id === cid);
      return `<button class="citizen-pill" data-cit-id="${cid}">⚒️ ${cit?.name || cid} (${cit?.trade || 'Artisan'})</button>`;
    }).join('') || '<em>No active workshop workers</em>';

    this.inspectorContent.innerHTML = `
      <div class="inspector-header">
        <div class="avatar-box building-box">
          <span>🏛️</span>
        </div>
        <div class="header-info">
          <h3>${p.name || `Parcel ${p.id.toUpperCase()}`}</h3>
          <div class="sub-badge badge-${p.district.replace(/_/g, '-')}">${p.district.replace(/_/g, ' ').toUpperCase()}</div>
          <div class="trade-title">${p.craft ? `Guild: ${p.craft.name}` : (p.isShed ? 'Utility Shed' : 'Residential Dwelling')}</div>
        </div>
      </div>

      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Street Frontage</div>
          <div class="stat-val">📍 ${p.streetName}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Architectural Archetype</div>
          <div class="stat-val highlight">${p.buildingType.replace(/_/g, ' ')}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Dimensions & Elevation</div>
          <div class="stat-val">${p.width}m × ${p.depth}m • +${p.elevation}m Loess Hill</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Hung Trade Sign</div>
          <div class="stat-val">🪧 ${p.craft ? p.craft.sign : 'None'}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Structural Age</div>
          <div class="stat-val">${aging.ageYears} years (${aging.maintenanceState.toUpperCase()})</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Ridge Sag & Wall Lean</div>
          <div class="stat-val warning">Sag: ${sagMm} mm • Tilt: ${aging.wallLeanAngle}°</div>
        </div>
      </div>

      <h4 class="section-title">👥 Household Residents (${p.residents.length})</h4>
      <div class="pill-list">${residentTags}</div>

      <h4 class="section-title">⚒️ Workshop Master & Journeymen (${p.workplaceFor.length})</h4>
      <div class="pill-list">${workerTags}</div>

      <h4 class="section-title">📦 Yard Clutter & Construction</h4>
      <div class="clutter-tags">
        ${p.scaffolding ? '<span class="tag-scaffold">🚧 Active Timber Scaffolding</span>' : ''}
        ${p.clutter.map(c => `<span class="tag-clutter">${c.replace(/_/g, ' ')}</span>`).join('')}
      </div>
    `;

    // Click on citizen pills
    this.inspectorContent.querySelectorAll('.citizen-pill').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const cid = (e.currentTarget as HTMLElement).getAttribute('data-cit-id');
        const cit = this.sim.citizens.find(c => c.id === cid);
        if (cit) this.inspectCitizen(cit);
      });
    });

    this.inspectorPanel.classList.add('open');
  }

  public closeInspector(): void {
    this.inspectorPanel.classList.remove('open');
    this.sim.selectedCitizen = null;
    this.sim.selectedParcel = null;
    this.camera.stopFollowing();
  }
}
