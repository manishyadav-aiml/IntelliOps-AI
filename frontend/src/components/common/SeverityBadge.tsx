const STYLES: Record<string, string> = {
  P1: 'bg-red-600 text-white',
  P2: 'bg-orange-100 text-orange-800',
  P3: 'bg-amber-100 text-amber-800',
  P4: 'bg-slate-100 text-slate-700',
}
const LABELS: Record<string, string> = { P1: 'CRITICAL', P2: 'HIGH', P3: 'MEDIUM', P4: 'LOW' }

export default function SeverityBadge({ value }: { value: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[value] ?? STYLES.P4}`} title={LABELS[value]}>
      {value} {LABELS[value]}
    </span>
  )
}
