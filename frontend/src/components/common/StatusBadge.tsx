const STYLES: Record<string, string> = {
  PENDING: 'bg-slate-100 text-slate-700',
  PROCESSING: 'bg-blue-100 text-blue-700',
  COMPLETED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
  INFO: 'bg-sky-100 text-sky-700',
  DEBUG: 'bg-slate-100 text-slate-600',
  WARNING: 'bg-amber-100 text-amber-800',
  ERROR: 'bg-red-100 text-red-700',
  CRITICAL: 'bg-red-600 text-white',
  OPEN: 'bg-red-100 text-red-700',
  INVESTIGATING: 'bg-blue-100 text-blue-700',
  MITIGATED: 'bg-amber-100 text-amber-800',
  RESOLVED: 'bg-green-100 text-green-700',
  UNKNOWN: 'bg-slate-100 text-slate-500',
}

export default function StatusBadge({ value }: { value: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[value] ?? STYLES.UNKNOWN}`}>
      {value}
    </span>
  )
}
