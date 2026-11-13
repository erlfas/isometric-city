export type DistrictId =
  | 'market_square'
  | 'bramowa_quarter'
  | 'grodzka_quarter'
  | 'dominican_quarter'
  | 'fara_quarter'
  | 'north_wall'
  | 'south_wall'
  | 'castle_hill'
  | 'krakow_suburb';

export type WealthClass = 'patrician' | 'burgher' | 'artisan' | 'plebeian' | 'visitor';

export type MaintenanceState = 'pristine' | 'sound' | 'weathered' | 'dilapidated';

export interface StructuralAging {
  ageYears: number;
  ridgeSag: number;       // meters of parabolic center dip (0.02 - 0.35m)
  wallLeanAngle: number;  // degrees of lateral tilt (-3.0 to +3.0)
  woodGraying: number;    // factor (0.0 - 1.0)
  mossFoundation: number; // factor (0.0 - 1.0)
  maintenanceState: MaintenanceState;
}

export interface CraftInfo {
  id: string;
  name: string;
  sign: string;
  guild: string;
  wealth?: WealthClass;
}

export interface Parcel {
  id: string;
  district: DistrictId;
  streetName: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  orientation: number;   // degrees
  elevation: number;     // meters above baseline
  buildingType: string;
  isShed?: boolean;
  isPlayerProperty?: boolean;
  name?: string;
  craft?: CraftInfo | null;
  aging: StructuralAging;
  clutter: string[];
  scaffolding: boolean;
  wealthClass: WealthClass;
  residents: string[];    // citizen IDs
  workplaceFor: string[]; // citizen IDs
  commodities: Record<string, number>;
}

export interface ScheduleItem {
  hour: number;
  state: string;
  location: string;
  task: string;
}

export interface Citizen {
  id: string;
  name: string;
  gender: 'male' | 'female';
  trade: string;
  guildRank: string;
  wealthClass: WealthClass;
  homeParcelId: string;
  bedNumber: number;
  workParcelId: string;
  walletGroschen: number;
  carriedItem: string;
  schedule: ScheduleItem[];
  // Dynamic runtime simulation state
  currentX?: number;
  currentZ?: number;
  targetX?: number;
  targetZ?: number;
  currentTask?: string;
  state?: string;
  animFrame?: number;
  isMoving?: boolean;
  // Locomotion (simulation.ts / navigation): velocity m/s, height of the feet, gait
  vx?: number;
  vz?: number;
  y?: number;
  /** Inside a building that is not cut away: simulated, not drawn. */
  hidden?: boolean;
  /** Heading (radians, atan2(dx, dz)) to face while standing, e.g. at a workbench. */
  faceYaw?: number;
  /** Extra vertical offset this frame (stepping up a stair). */
  stepBob?: number;
  /** 'work' plays the kit's work loop, 'idle' stands; unset = by schedule state. */
  activityAnim?: string;
  /** 0 walk .. 1 run (unset: from measured speed). */
  gait?: number;
  /** Stride length factor: travel is shown sped up, so steps lengthen with it. */
  strideScale?: number;
  /** Lying in a bed (feet at the position, head away from faceYaw) or sitting; unset = standing. */
  pose?: 'lie' | 'sit';
  /** Carrying home: loaves in the crook of the left arm, or a full bucket in the right hand. */
  carrying?: 'bread' | 'water';
}

export interface StreetNode {
  id: string;
  x: number;
  z: number;
}

export interface StreetNetwork {
  nodes: StreetNode[];
  edges: [string, string][];
}

export interface PerimeterElement {
  id: string;
  type: 'tower' | 'gate';
  name: string;
  x: number;
  z: number;
  angle: number;
  height: number;
}

export interface CastleElement {
  id: string;
  type: 'landmark' | 'infrastructure';
  name: string;
  x?: number;
  z?: number;
  width?: number;
  depth?: number;
  height?: number;
  startX?: number;
  startZ?: number;
  endX?: number;
  endZ?: number;
  description?: string;
}

export interface CivicLandmark {
  id: string;
  type: 'landmark' | 'civic_object';
  name: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  height: number;
  description?: string;
}

export interface BellHourInfo {
  hour: number;
  name: string;
  action: string;
}

export interface FairEvent {
  id: string;
  name: string;
  triggerHour: number;
  location: string;
  description: string;
}

export interface VegetationElement {
  id: string;
  type: string;
  x: number;
  z: number;
  scale: number;
  rotation: number;
  zone?: string;
}

export interface CityPlan {
  metadata: {
    city: string;
    year: number;
    reign: string;
    event: string;
    areaHectares: number;
    generatedAt: string;
    version: string;
  };
  districts: Record<string, string>;
  defense: {
    perimeterPoints: PerimeterElement[];
    castleElements: CastleElement[];
  };
  civicLandmarks: CivicLandmark[];
  streetNetwork: StreetNetwork;
  parcels: Parcel[];
  vegetation?: VegetationElement[];
  citizens: Citizen[];
  bellHours: Record<string, BellHourInfo>;
  fairEvents: FairEvent[];
  houseTypesCatalog: string[];
  shedTypesCatalog: string[];
  craftsCatalog: any[];
}

export type HeatmapMode = 'none' | 'wealth' | 'aging' | 'traffic' | 'defense';
export type CameraQuadrant = 0 | 1 | 2 | 3; // 0=SW, 1=NW, 2=NE, 3=SE
