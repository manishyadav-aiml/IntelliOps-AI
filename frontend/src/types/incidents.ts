export type Severity = 'P1' | 'P2' | 'P3' | 'P4'
export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'MITIGATED' | 'RESOLVED'

export interface Incident {
  id: number
  public_id: string
  title: string
  description: string
  service: string
  severity: Severity
  severity_label: string
  severity_reasons: string[]
  status: IncidentStatus
  services: string[]
  upload_id: number | null
  detection_time: string
  first_occurrence: string | null
  last_occurrence: string | null
  assigned_user_id: number | null
  assigned_to: string | null
  resolution_notes: string | null
  acknowledged_at: string | null
  resolved_at: string | null
  created_at: string
  updated_at: string
  anomaly_summary: Record<string, unknown> | null
}

export interface Note { id: number; author_id: number | null; author_name: string | null; content: string; created_at: string }
export interface IncidentEvent { id: number; event_type: string; timestamp: string; description: string; actor_user_id: number | null; details: Record<string, unknown> | null }
export interface SimilarIncident {
  incident_id: string
  similar_incident_id: string
  similar_incident_pk: number | null
  title: string | null
  similarity_score: number
  shared_services: string[]
  shared_templates: string[]
  shared_error_patterns: string[]
  note: string
}
export interface EvidenceRef { text: string; evidence: string[] }
export interface InvestigationResult {
  incident_summary: string
  observed_symptoms: EvidenceRef[]
  potential_contributing_factors: EvidenceRef[]
  suspected_root_causes: EvidenceRef[]
  recommended_investigation: EvidenceRef[]
  relevant_historical_incidents: string[]
  relevant_documentation: EvidenceRef[]
  confidence: string
  limitations: string[]
  evidence: { id: string; kind: string; text: string }[]
  status: string
  validation_notes: string[]
}
export interface Investigation {
  id: number
  incident_id: number
  question: string
  status: string
  provider: string
  result: InvestigationResult | null
  error_code: string | null
  error_message: string | null
  created_at: string
}
export interface IncidentDetail extends Incident {
  templates: string[]
  notes: Note[]
  related: SimilarIncident[]
  latest_investigation: Investigation | null
  linked_log_count: number
}
export interface Anomaly {
  id: number
  upload_id: number
  window_start: string
  window_end: string
  anomaly_detected: boolean
  anomaly_score: number
  threshold: number
  method: string
  model_version: string
  affected_service: string
  contributing_features: { name: string; z_score: number }[]
  note: string
}
export interface AnalysisResult {
  upload_id: number
  method: string
  window_seconds: number
  windows_analyzed: number
  anomalous_windows: number
  entries_without_timestamp: number
  incidents_created: number
  incidents_updated: number
  incident_ids: number[]
  note: string
}
