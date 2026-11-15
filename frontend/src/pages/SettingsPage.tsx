import { useEffect, useState } from 'react'
import ErrorMessage from '../components/common/ErrorMessage'
import Spinner from '../components/common/Spinner'
import { systemService } from '../services/knowledgeService'
import type { SystemStatus } from '../types/knowledge'
import { getErrorMessage } from '../utils/errors'

export default function SettingsPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { systemService.status().then(setStatus).catch((e) => setError(getErrorMessage(e))) }, [])
  if (error) return <ErrorMessage message={error} />
  if (!status) return <Spinner />
  const rows: [string, string][] = [
    ['Application version', status.version], ['Environment', status.environment],
    ['AI provider', `${status.llm_provider} (${status.llm_configured ? 'API key configured' : 'not configured'})`],
    ['Embedding model in use', status.embedder], ['Vector search backend', status.vector_backend],
    ['Log template miner', status.template_miner], ['Trained anomaly model', status.trained_model ?? 'none (baseline detector in use)'],
  ]
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <p className="text-sm text-slate-600">Read-only runtime information. Configuration is set with server environment variables; secrets are never shown here.</p>
      <dl className="max-w-2xl divide-y rounded-lg border bg-white text-sm">
        {rows.map(([k, v]) => <div key={k} className="flex justify-between gap-4 p-3"><dt className="text-slate-500">{k}</dt><dd className="text-right font-medium">{v}</dd></div>)}
      </dl>
      {!status.llm_configured && <p className="rounded bg-amber-50 p-3 text-sm text-amber-800">The AI assistant is off because no API key is configured. Log processing, anomaly detection, incidents, search over documents (excerpts) and reports still work.</p>}
      {status.embedder_fallback_reason && <p className="rounded bg-amber-50 p-3 text-sm text-amber-800">Using the lexical fallback embedder: {status.embedder_fallback_reason}. Matching is keyword-based rather than semantic.</p>}
    </section>
  )
}
