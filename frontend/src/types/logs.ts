export type UploadStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export interface LogUpload {
  id: number
  filename: string
  extension: string
  size_bytes: number
  status: UploadStatus
  total_lines: number
  processed_lines: number
  entry_count: number
  error_message: string | null
  parse_stats: Record<string, unknown> | null
  parser_used: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface LogEntry {
  id: number
  upload_id: number
  line_number: number
  timestamp: string | null
  level: string
  service: string
  hostname: string
  message: string
  original_message: string
  template_id: number | null
  template_text: string | null
  parameters: string[] | null
  truncated: boolean
  source_file: string | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface TemplateSummary {
  template_id: number
  template_hash: string
  template_text: string
  occurrences: number
}

export interface Facets {
  levels: string[]
  services: string[]
}

export interface EntryFilters {
  page: number
  level?: string
  service?: string
  templateId?: number
  q?: string
}
