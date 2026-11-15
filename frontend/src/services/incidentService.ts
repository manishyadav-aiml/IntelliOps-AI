import type { AnalysisResult, Anomaly, Incident, IncidentDetail, IncidentEvent, IncidentStatus, Investigation, Note, Severity, SimilarIncident } from '../types/incidents'
import type { Page } from '../types/logs'
import { api } from './api'

export interface IncidentQuery { page: number; status?: string; severity?: string; service?: string; q?: string }
export interface IncidentPatch {
  title?: string
  description?: string
  severity?: Severity
  status?: IncidentStatus
  assigned_user_id?: number | null
  resolution_notes?: string | null
}

export const incidentService = {
  list: async (q: IncidentQuery): Promise<Page<Incident>> => (await api.get<Page<Incident>>('/incidents', { params: { page_size: 10, ...q } })).data,
  get: async (id: number): Promise<IncidentDetail> => (await api.get<IncidentDetail>(`/incidents/${id}`)).data,
  create: async (body: { title: string; description?: string; service?: string; severity?: Severity }): Promise<IncidentDetail> =>
    (await api.post<IncidentDetail>('/incidents', body)).data,
  update: async (id: number, patch: IncidentPatch): Promise<IncidentDetail> => (await api.patch<IncidentDetail>(`/incidents/${id}`, patch)).data,
  timeline: async (id: number, eventTypes?: string[]): Promise<IncidentEvent[]> =>
    (await api.get<IncidentEvent[]>(`/incidents/${id}/timeline`, { params: { event_type: eventTypes }, paramsSerializer: { indexes: null } })).data,
  similar: async (id: number): Promise<SimilarIncident[]> => (await api.get<SimilarIncident[]>(`/incidents/${id}/similar`)).data,
  addNote: async (id: number, content: string): Promise<Note> => (await api.post<Note>(`/incidents/${id}/notes`, { content })).data,
  investigate: async (id: number, question?: string): Promise<Investigation> =>
    (await api.post<Investigation>(`/incidents/${id}/investigate`, { question: question || null })).data,
  analyzeLog: async (logId: number, windowSeconds: number): Promise<AnalysisResult> =>
    (await api.post<AnalysisResult>(`/logs/${logId}/analyze`, null, { params: { window_seconds: windowSeconds } })).data,
  anomalies: async (params: { page: number; upload_id?: number; detected_only?: boolean }): Promise<Page<Anomaly>> =>
    (await api.get<Page<Anomaly>>('/anomalies', { params: { page_size: 25, ...params } })).data,
}
