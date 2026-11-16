interface Props {
  label: string
  value: string | number | null
  hint?: string
}

export default function MetricCard({ label, value, hint }: Props) {
  return (
    <section className="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">
          {label}
        </p>

        <span className="h-2 w-2 shrink-0 rounded-full bg-blue-500" />
      </div>

      <div className="mt-4 text-3xl font-bold tracking-tight text-slate-900">
        {value === null ? 'n/a' : value}
      </div>

      {hint && (
        <p className="mt-2 text-xs leading-5 text-slate-400">
          {hint}
        </p>
      )}
    </section>
  )
}