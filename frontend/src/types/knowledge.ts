export interface DocumentItem {
  id: number
  filename: string
  extension: string
  size_bytes: number
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  page_count: number
  chunk_count: number
  embedder_name: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}
export interface Citation { label: string; document_id: number; document_name: string; page_number: number | null; chunk_id: string; snippet: string; score: number }
export interface RagResponse { answer: string; sufficient: boolean; llm_used: boolean; citations: Citation[]; notice: string | null }
export interface Report { id: number; incident_id: number; format: 'pdf' | 'csv' | 'json'; filename: string; size_bytes: number; created_at: string }
export interface DashboardSummary {
  total_logs_processed: number
  uploads_total: number
  active_incidents: number
  critical_incidents: number
  anomalies_detected: number
  services_monitored: number
  resolved_incidents: number
  avg_time_to_acknowledge_seconds: number | null
  avg_time_to_resolve_seconds: number | null
}
export interface Bucket { bucket: string; count: number }
export interface NamedCount { name: string; count: number }
export interface DashboardTrends {
  bucket: 'hour' | 'day'
  error_frequency: Bucket[]
  anomaly_trend: Bucket[]
  resolution_trend: Bucket[]
  severity_distribution: NamedCount[]
  top_templates: NamedCount[]
  truncated: boolean
}
export interface DashboardFilters { bucket: 'hour' | 'day'; start?: string; end?: string; service?: string }
export interface SystemStatus {
  version: string
  environment: string
  llm_provider: string
  llm_configured: boolean
  embedder: string
  embedder_fallback_reason: string | null
  vector_backend: string
  template_miner: string
  trained_model: string | null
}
