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
  /** Explicit model (industry sites): placed unscaled, ahead of every parcel-kind rule. */
  model?: string;
  /** Industry site the parcel belongs to (`CityPlan.industrySites` key). */
  site?: string;
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

/** A tree, shrub, reed bed, stone or log; `type` is its model (public/models/<type>.glb). */
export interface VegetationElement {
  id: string;
  type: VegetationType | string;
  x: number;
  z: number;
  scale: number;
  /** Degrees about +Y. */
  rotation: number;
  zone?: string;
}

export type VegetationType =
  | 'tree_oak' | 'tree_oak_b' | 'tree_oak_c' | 'tree_alder' | 'tree_alder_b' | 'tree_hornbeam' | 'tree_lime'
  | 'tree_willow' | 'tree_willow_weeping' | 'tree_birch' | 'tree_birch_b' | 'tree_pine' | 'tree_pine_b'
  | 'bush_hazel' | 'bush_hawthorn' | 'fern_clump' | 'reed_clump' | 'rock_boulder' | 'rock_boulder_b' | 'log_fallen';

/** A footbridge over the river (generate_city_plan.py plan_river_crossing; model footbridge). */
export interface RiverCrossing {
  id: string;
  name: string;
  model: string;
  x: number;
  z: number;
  /** Direction of the deck axis in the x-z plane (deg, atan2(z, x)); the town end is +. */
  angle: number;
  length: number;
  width: number;
  /** Walking height at the ends and mid-span (m): a parabolic hump between them. */
  deckEnd: number;
  deckMid: number;
}

/** A watermill on the bank: its parcel, the wheel's axle and the race it turns in. */
export interface RiverMill {
  parcelId: string;
  wheel: { x: number; z: number; y: number };
  /** Centreline of the mill race, upstream first; leaves and rejoins the river. */
  race: RiverPoint[];
}

/** A trodden path or forest ride painted on the ground (no effect on routing). */
export interface GroundPath {
  id: string;
  kind: 'footpath' | 'track' | 'ride' | string;
  width: number;
  points: { x: number; z: number }[];
}

/** Painted ground outside the walls (generate_city_plan.py INDUSTRY_GROUNDS): pale stone
 *  dust in the quarry, trodden earth in a yard, dark peat mud, standing pools in the bog. */
export interface GroundPatch {
  id: string;
  kind: 'spoil' | 'yard' | 'mud' | 'pool';
  points: { x: number; z: number }[];
}

export interface IndustrySite { x: number; z: number; parcels: string[] }

export interface RiverPoint {
  x: number;
  z: number;
  /** Water surface width (m) at this point, 9-14. */
  width: number;
}

/** A river centreline sampled every ~3 m (generate_city_plan.py generate_river). */
export interface River {
  name: string;
  /** "downstream = increasing index" */
  flow: string;
  lengthM: number;
  points: RiverPoint[];
  crossings?: RiverCrossing[];
  mills?: RiverMill[];
}

export interface PlanProp { id: string; model: string; x: number; z: number; rot: number; near?: string }

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
  /** The Bystrzyca south-east of the city. */
  river?: River;
  /** Footpaths and forest rides (ground paint only). */
  paths?: GroundPath[];
  grounds?: GroundPatch[];
  /** Small placed models outside any parcel (hitching posts, troughs, the stable's dung heap):
   *  generate_city_plan.py add_props; rot = degrees about +Y, as parcels' orientation. */
  props?: PlanProp[];
  industrySites?: Record<string, IndustrySite>;
  citizens: Citizen[];
  bellHours: Record<string, BellHourInfo>;
  fairEvents: FairEvent[];
  houseTypesCatalog: string[];
  shedTypesCatalog: string[];
  craftsCatalog: any[];
}

export type HeatmapMode = 'none' | 'wealth' | 'aging' | 'traffic' | 'defense';
export type CameraQuadrant = 0 | 1 | 2 | 3; // 0=SW, 1=NW, 2=NE, 3=SE
