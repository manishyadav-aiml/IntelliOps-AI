import type { ReactNode } from 'react'
import EmptyState from './EmptyState'

interface Props { title: string; empty: boolean; emptyMessage?: string; children: ReactNode }

export default function ChartCard({ title, empty, emptyMessage = 'No data for this period.', children }: Props) {
  return (
    <section className="rounded-lg border bg-white p-4 shadow-sm">
      <h2 className="mb-3 font-medium">{title}</h2>
      {empty ? <EmptyState message={emptyMessage} /> : <div className="h-56">{children}</div>}
    </section>
  )
}
