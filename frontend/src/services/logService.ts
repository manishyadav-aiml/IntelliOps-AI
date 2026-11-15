import type { EntryFilters, Facets, LogEntry, LogUpload, Page, TemplateSummary } from '../types/logs'
import { api } from './api'

export const logService = {
  upload: async (file: File, onProgress?: (percent: number) => void): Promise<LogUpload> => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post<LogUpload>('/logs/upload', form, {
      onUploadProgress: (event) => {
        if (onProgress && event.total) onProgress(Math.round((event.loaded / event.total) * 100))
      },
    })
    return data
  },
  list: async (params: { page: number; status?: string; q?: string }): Promise<Page<LogUpload>> =>
    (await api.get<Page<LogUpload>>('/logs', { params: { page_size: 10, ...params } })).data,
  get: async (id: number): Promise<LogUpload> => (await api.get<LogUpload>(`/logs/${id}`)).data,
  remove: async (id: number): Promise<void> => {
    await api.delete(`/logs/${id}`)
  },
  retry: async (id: number): Promise<LogUpload> => (await api.post<LogUpload>(`/logs/${id}/reprocess`)).data,
  entries: async (id: number, f: EntryFilters): Promise<Page<LogEntry>> =>
    (
      await api.get<Page<LogEntry>>(`/logs/${id}/entries`, {
        params: { page: f.page, page_size: 25, level: f.level, service: f.service, template_id: f.templateId, q: f.q },
      })
    ).data,
  templates: async (id: number): Promise<TemplateSummary[]> =>
    (await api.get<TemplateSummary[]>(`/logs/${id}/templates`, { params: { limit: 10 } })).data,
  facets: async (id: number): Promise<Facets> => (await api.get<Facets>(`/logs/${id}/facets`)).data,
}
