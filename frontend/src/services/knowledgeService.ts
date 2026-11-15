import type { DashboardFilters, DashboardSummary, DashboardTrends, DocumentItem, NamedCount, RagResponse, Report, SystemStatus } from '../types/knowledge'
import type { Page } from '../types/logs'
import { api } from './api'

export const documentService = {
  upload: async (file: File, onProgress?: (percent: number) => void): Promise<DocumentItem> => {
    const form = new FormData()
    form.append('file', file)
    return (
      await api.post<DocumentItem>('/documents/upload', form, {
        onUploadProgress: (e) => onProgress && e.total && onProgress(Math.round((e.loaded / e.total) * 100)),
      })
    ).data
  },
  list: async (params: { page: number; q?: string; status?: string }): Promise<Page<DocumentItem>> =>
    (await api.get<Page<DocumentItem>>('/documents', { params: { page_size: 10, ...params } })).data,
  remove: async (id: number): Promise<void> => {
    await api.delete(`/documents/${id}`)
  },
  reindex: async (id: number): Promise<DocumentItem> => (await api.post<DocumentItem>(`/documents/${id}/index`)).data,
}

export const ragService = {
  query: async (question: string, documentIds?: number[]): Promise<RagResponse> =>
    (await api.post<RagResponse>('/rag/query', { question, document_ids: documentIds?.length ? documentIds : null })).data,
}

export const reportService = {
  list: async (page: number): Promise<Page<Report>> => (await api.get<Page<Report>>('/reports', { params: { page, page_size: 10 } })).data,
  generate: async (incidentId: number, format: 'pdf' | 'csv' | 'json'): Promise<Report> =>
    (await api.post<Report>('/reports/generate', { incident_id: incidentId, format })).data,
  /** Downloads through axios so the Authorization header is sent. */
  download: async (report: Report): Promise<void> => {
    const response = await api.get<Blob>(`/reports/${report.id}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = report.filename
    link.click()
    URL.revokeObjectURL(url)
  },
}

export const dashboardService = {
  summary: async (f: DashboardFilters): Promise<DashboardSummary> =>
    (await api.get<DashboardSummary>('/dashboard/summary', { params: { start: f.start, end: f.end, service: f.service } })).data,
  trends: async (f: DashboardFilters): Promise<DashboardTrends> =>
    (await api.get<DashboardTrends>('/dashboard/trends', { params: { bucket: f.bucket, start: f.start, end: f.end, service: f.service } })).data,
  services: async (): Promise<NamedCount[]> => (await api.get<NamedCount[]>('/dashboard/services')).data,
}

export const systemService = {
  status: async (): Promise<SystemStatus> => (await api.get<SystemStatus>('/system/status')).data,
}
