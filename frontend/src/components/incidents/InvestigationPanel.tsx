import { useState } from 'react'
import ErrorMessage from '../common/ErrorMessage'
import { incidentService } from '../../services/incidentService'
import type { EvidenceRef, IncidentDetail, InvestigationResult } from '../../types/incidents'
import { getErrorMessage } from '../../utils/errors'

function Section({ title, items, evidence }: { title: string; items: EvidenceRef[]; evidence: InvestigationResult['evidence'] }) {
  if (items.length === 0) return null
  return (
    <div>
      <h3 className="font-medium">{title}</h3>
      <ul className="list-disc pl-5">
        {items.map((i) => (
          <li key={i.text}>{i.text}{i.evidence.length > 0 && (
            <span className="ml-1 text-xs text-slate-500">[{i.evidence.map((id) => {
              const e = evidence.find((x) => x.id === id)
              return <span key={id} title={e?.text} className="mr-1 cursor-help underline decoration-dotted">{id}</span>
            })}]</span>
          )}</li>
        ))}
      </ul>
    </div>
  )
}

export default function InvestigationPanel({ incident, onDone }: { incident: IncidentDetail; onDone: () => void }) {
  const [question, setQuestion] = useState('')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const latest = incident.latest_investigation
  const result = latest?.status === 'COMPLETED' ? latest.result : null

  const run = async () => {
    setRunning(true); setError(null)
    try { await incidentService.investigate(incident.id, question); onDone() }
    catch (e) { setError(getErrorMessage(e)); onDone() }
    finally { setRunning(false) }
  }

  return (
    <section className="space-y-3 rounded-lg border bg-white p-4 text-sm">
      <h2 className="font-medium">AI investigation</h2>
      <p className="rounded bg-amber-50 p-2 text-xs text-amber-800">AI-generated suggestions, not confirmed findings. Verify against the evidence before acting. The assistant never executes actions.</p>
      <div className="flex gap-2">
        <input aria-label="Question for the AI assistant" value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500}
          placeholder={`Why is the ${incident.service} service failing?`} className="flex-1 rounded border px-2 py-1" />
        <button type="button" disabled={running} onClick={() => void run()} className="rounded bg-blue-600 px-3 py-1 text-white disabled:opacity-60">{running ? 'Investigating…' : 'Investigate'}</button>
      </div>
      {error && <ErrorMessage message={error} />}
      {latest?.status === 'FAILED' && !error && <ErrorMessage message={latest.error_message ?? 'The AI service failed.'} />}
      {result && (
        <div className="space-y-3">
          <p><strong>Summary:</strong> {result.incident_summary}</p>
          <Section title="Observed symptoms" items={result.observed_symptoms} evidence={result.evidence} />
          <Section title="Potential contributing factors" items={result.potential_contributing_factors} evidence={result.evidence} />
          <Section title="Suspected root causes (unconfirmed)" items={result.suspected_root_causes} evidence={result.evidence} />
          <Section title="Recommended investigation (for a human to evaluate)" items={result.recommended_investigation} evidence={result.evidence} />
          <Section title="Relevant documentation" items={result.relevant_documentation} evidence={result.evidence} />
          {result.relevant_historical_incidents.length > 0 && <p><strong>Historical incidents:</strong> {result.relevant_historical_incidents.join(', ')}</p>}
          <p><strong>Confidence:</strong> {result.confidence}. <strong>Limitations:</strong> {result.limitations.join('; ') || 'none stated'}</p>
          {result.validation_notes.length > 0 && <p className="text-xs text-slate-500">Automatic checks: {result.validation_notes.join(' ')}</p>}
          <details><summary className="cursor-pointer">Evidence references ({result.evidence.length})</summary>
            <ul className="mt-1 space-y-1 text-xs">{result.evidence.map((e) => <li key={e.id}><strong>{e.id}</strong> ({e.kind}) {e.text}</li>)}</ul></details>
        </div>
      )}
    </section>
  )
}
