import type { ReactNode } from 'react'
import EmptyState from './EmptyState'

interface Props {
  title: string
  empty: boolean
  emptyMessage?: string
  children: ReactNode
}

export default function ChartCard({
  title,
  empty,
  emptyMessage = 'No data available for this period.',
  children,
}: Props) {
  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <h2 className="text-sm font-semibold tracking-tight text-slate-800">
          {title}
        </h2>
        <span className="h-2 w-2 rounded-full bg-blue-500" />
      </div>

      <div className="p-5">
        {empty ? (
          <EmptyState message={emptyMessage} />
        ) : (
          <div className="h-64 min-w-0">{children}</div>
        )}
      </div>
    </section>
  )
}