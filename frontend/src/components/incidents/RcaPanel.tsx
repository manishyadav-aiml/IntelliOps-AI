import EmptyState from '../common/EmptyState'

interface Rca {
  summary?: string[]
  disclaimer?: string
  earliest_error_services?: { service: string; error_count: number; seconds_after_first: number }[]
  new_error_templates?: { template: string; incident_count: number }[]
}

/** Deterministic, LLM-free evidence computed from the logs. Temporal correlation only, never a confirmed cause. */
export default function RcaPanel({ summary }: { summary: Record<string, unknown> | null }) {
  const rca = (summary?.rca ?? null) as Rca | null
  return (
    <section className="rounded-lg border bg-white p-4 text-sm">
      <h2 className="mb-2 font-medium">Root-cause evidence (computed from the logs, unconfirmed)</h2>
      {!rca || !rca.summary || rca.summary.length === 0 ? (
        <EmptyState message="No log-based evidence is available for this incident (for example a manually created one)." />
      ) : (
        <>
          <ul className="list-disc space-y-1 pl-5">{rca.summary.map((line) => <li key={line}>{line}</li>)}</ul>
          {rca.earliest_error_services && rca.earliest_error_services.length > 0 && (
            <table className="mt-3 w-full text-left text-xs">
              <thead className="text-slate-500"><tr><th className="py-1">Service</th><th>Errors</th><th>Started (s after first)</th></tr></thead>
              <tbody>{rca.earliest_error_services.map((s) => (
                <tr key={s.service} className="border-t"><td className="py-1">{s.service}</td><td>{s.error_count}</td><td>{s.seconds_after_first}</td></tr>
              ))}</tbody>
            </table>
          )}
          <p className="mt-3 rounded bg-amber-50 p-2 text-xs text-amber-800">{rca.disclaimer}</p>
        </>
      )}
    </section>
  )
}
