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
  private mobilePlayBtn: HTMLElement | null = null;
  private mobileSheet: HTMLElement | null = null;
  public onFollowToggle?: (c: Citizen | null) => void;

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
    this.mobilePlayBtn = document.getElementById('btn-mobile-play');
    this.mobileSheet = document.getElementById('mobile-sheet');
    this.inspectorPanel = document.getElementById('inspector-panel')!;
    this.inspectorContent = document.getElementById('inspector-content')!;
    this.eventTickerEl = document.getElementById('event-ticker-text')!;
  }

  private setupEventListeners(): void {
    // Play / Pause (Desktop & Mobile buttons)
    const togglePlayHandler = () => {
      const isPaused = this.sim.togglePause();
      this.playPauseBtn.textContent = isPaused ? '▶ Resume' : '⏸ Pause';
      this.playPauseBtn.classList.toggle('active', !isPaused);
      if (this.mobilePlayBtn) {
        this.mobilePlayBtn.textContent = isPaused ? '▶' : '⏸';
        this.mobilePlayBtn.classList.toggle('active', !isPaused);
      }
    };
    this.playPauseBtn.addEventListener('click', togglePlayHandler);
    this.mobilePlayBtn?.addEventListener('click', togglePlayHandler);

    // Speed buttons (Both Desktop header & Mobile bottom sheet)
    document.querySelectorAll('[data-speed]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const el = e.currentTarget as HTMLElement;
        const spdVal = el.getAttribute('data-speed');
        document.querySelectorAll('[data-speed]').forEach((b) => {
          b.classList.toggle('active', b.getAttribute('data-speed') === spdVal);
        });
        const spd = parseFloat(spdVal || '5');
        this.sim.setSpeed(spd);
        this.closeMobileSheet();
      });
    });

    // Time Jump buttons
    document.querySelectorAll('[data-jump-hour]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const hour = parseFloat((e.currentTarget as HTMLElement).getAttribute('data-jump-hour') || '9');
        this.sim.setTime(hour);
        this.closeMobileSheet();
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
    const tollBellHandler = () => {
      this.sim.tollCivicBellManually();
      this.closeMobileSheet();
    };
    document.getElementById('btn-toll-bell')?.addEventListener('click', tollBellHandler);
    document.getElementById('btn-mobile-toll-bell')?.addEventListener('click', tollBellHandler);

    // Mobile sheet openers
    const sheetTitle = document.getElementById('sheet-title');
    const secSpeed = document.getElementById('sheet-section-speed');
    const secTime = document.getElementById('sheet-section-time');
    const secLayers = document.getElementById('sheet-section-layers');

    document.getElementById('btn-open-menu')?.addEventListener('click', () => {
      if (this.mobileSheet) {
        if (sheetTitle) sheetTitle.textContent = '⏱️ Time & Speed Controls';
        if (secSpeed) secSpeed.style.display = 'flex';
        if (secTime) secTime.style.display = 'flex';
        if (secLayers) secLayers.style.display = 'none';
        this.mobileSheet.classList.add('open');
      }
    });

    document.getElementById('btn-open-layers')?.addEventListener('click', () => {
      if (this.mobileSheet) {
        if (sheetTitle) sheetTitle.textContent = '🗺️ Visualization Overlays';
        if (secSpeed) secSpeed.style.display = 'none';
        if (secTime) secTime.style.display = 'none';
        if (secLayers) secLayers.style.display = 'flex';
        this.mobileSheet.classList.add('open');
      }
    });

    document.getElementById('btn-close-sheet')?.addEventListener('click', () => {
      this.closeMobileSheet();
    });
    document.getElementById('sheet-backdrop')?.addEventListener('click', () => {
      this.closeMobileSheet();
    });

    // Fullscreen toggle for smartphones
    document.getElementById('btn-fullscreen')?.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen?.().catch(() => {});
      } else {
        document.exitFullscreen?.().catch(() => {});
      }
    });
  }

  public closeMobileSheet(): void {
    this.mobileSheet?.classList.remove('open');
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

    // Today so far (M7: the day comes from needs and bells), newest last, then the needs.
    const mind = this.sim.mindOf(c);
    const hhmm = (h: number) => h < 0 ? '--:--'
      : `${String(Math.floor(h)).padStart(2, '0')}:${String(Math.floor((h % 1) * 60)).padStart(2, '0')}`;
    const diary = mind?.diary ?? [];
    const needBar = (label: string, v: number) => `
        <div class="schedule-item">
          <span class="sched-hour">${label}</span>
          <span class="sched-task"><span style="display:inline-block;width:${Math.round(v * 100)}%;max-width:100%;height:6px;border-radius:3px;background:${v > 0.7 ? '#c0503a' : v > 0.4 ? '#c8a040' : '#6a9a5a'}"></span></span>
        </div>`;
    const scheduleRows = diary.map((item, k) => `
        <div class="schedule-item ${k === diary.length - 1 ? 'active-schedule' : ''}">
          <span class="sched-hour">${hhmm(item.h)}</span>
          <span class="sched-state badge-${item.state.toLowerCase()}">${item.state}</span>
          <span class="sched-task">${item.task}</span>
        </div>`).join('') + (mind ? needBar('Hunger', mind.hunger) + needBar('Thirst', mind.thirst)
          + needBar('Tired', mind.fatigue) + needBar('Company', mind.social) + needBar('Piety', mind.piety) : '');

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
        this.onFollowToggle?.(null);
        this.inspectCitizen(c);
      } else {
        this.camera.follow(c.id, c.currentX ?? 0, c.currentZ ?? 0);
        this.onFollowToggle?.(c);
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
    this.onFollowToggle?.(null);

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
    this.onFollowToggle?.(null);
  }
}
