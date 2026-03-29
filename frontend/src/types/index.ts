export interface Satellite {
  id: number
  norad_id: number
  name: string
  classification: string
  object_type: string | null
  country: string | null
  is_active: boolean
  updated_at: string
}

export interface TLERecord {
  id: number
  satellite_id: number
  epoch: string
  line1: string
  line2: string
  inclination: number | null
  eccentricity: number | null
  perigee_km: number | null
  apogee_km: number | null
  ingested_at: string
}

export interface PcHistoryPoint {
  time: string
  hours_to_tca: number
  pc: number
  miss_distance_km: number
}

export interface BurnPlan {
  burn_epoch: string | null
  burn_rtn_ms: [number, number, number] | null
  delta_v_ms: number | null
  pc_post_burn: number | null
  lead_time_h: number | null
}

export interface ConjunctionEvent {
  id: number
  primary_sat_id: number
  secondary_sat_id: number
  primary_name: string | null
  secondary_name: string | null
  primary_norad: number | null
  secondary_norad: number | null
  tca_time: string
  miss_distance_km: number
  relative_speed_km_s: number | null
  pc: number
  pc_method: string
  covariance_available: boolean
  pc_history: PcHistoryPoint[]
  optimal_burn_epoch: string | null
  burn_rtn_ms: [number, number, number] | null
  burn_delta_v_ms: number | null
  pc_post_burn: number | null
  burn_lead_time_h: number | null
  status: string
  created_at: string
  updated_at: string
}

export interface ConjunctionListItem {
  id: number
  primary_sat_id: number
  secondary_sat_id: number
  primary_name: string | null
  secondary_name: string | null
  primary_norad: number | null
  secondary_norad: number | null
  tca_time: string
  miss_distance_km: number
  pc: number
  status: string
  has_burn_plan: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface Stats {
  active_conjunctions: number
  high_pc_count: number
  satellites_tracked: number
  last_screen_at: string | null
  last_screen_status: string | null
}

export interface OptimizeResponse {
  event_id: number
  burn_plans: BurnPlan[]
  best_plan: BurnPlan
  message: string
}

export interface AlertMessage {
  type: string
  event_id?: number
  pc?: number
  primary_name?: string
  secondary_name?: string
  tca_time?: string
  message: string
  delta_v_ms?: number
  pc_post_burn?: number
}
