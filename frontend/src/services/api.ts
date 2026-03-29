import axios from 'axios'
import type {
  Satellite, TLERecord, ConjunctionEvent, ConjunctionListItem,
  PaginatedResponse, Stats, OptimizeResponse,
} from '../types'

const api = axios.create({ baseURL: '/api', timeout: 30000 })

export const satelliteApi = {
  list: (page = 1, pageSize = 50, search?: string) =>
    api.get<PaginatedResponse<Satellite>>('/satellites', {
      params: { page, page_size: pageSize, search },
    }).then(r => r.data),

  getTLE: (noradId: number) =>
    api.get<TLERecord>(`/satellites/${noradId}/tle`).then(r => r.data),

  getTrack: (noradId: number, hours = 1.5) =>
    api.get(`/satellites/${noradId}/track`, { params: { hours } }).then(r => r.data),
}

export const conjunctionApi = {
  list: (page = 1, pageSize = 25, sortBy = 'pc', minPc?: number) =>
    api.get<PaginatedResponse<ConjunctionListItem>>('/conjunctions', {
      params: { page, page_size: pageSize, sort_by: sortBy, sort_dir: 'desc', min_pc: minPc },
    }).then(r => r.data),

  get: (id: number) =>
    api.get<ConjunctionEvent>(`/conjunctions/${id}`).then(r => r.data),

  stats: () =>
    api.get<Stats>('/conjunctions/stats').then(r => r.data),

  optimize: (id: number, leadTimes = [24, 48, 72]) =>
    api.post<OptimizeResponse>(`/conjunctions/${id}/optimize`, {
      lead_times_h: leadTimes,
    }).then(r => r.data),

  triggerScreen: () =>
    api.post('/conjunctions/trigger-screen').then(r => r.data),

  screeningHistory: () =>
    api.get('/conjunctions/runs/history').then(r => r.data),
}
