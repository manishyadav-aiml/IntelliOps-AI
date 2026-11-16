import { useMemo, useState } from 'react'
import { RotateCcw, Search } from 'lucide-react'

import DataTable from '../components/common/DataTable'
import StatusBadge from '../components/common/StatusBadge'
import { demoLogs } from './data'

const LEVELS = [
  'ALL',
  'CRITICAL',
  'ERROR',
  'WARNING',
  'INFO',
  'DEBUG',
]

export default function DemoLogs() {
  const [search, setSearch] = useState('')
  const [level, setLevel] = useState('ALL')

  const filteredLogs = useMemo(() => {
    const query = search.trim().toLowerCase()

    return demoLogs.filter((log) => {
      const matchesSearch =
        !query ||
        log.id.toLowerCase().includes(query) ||
        log.service.toLowerCase().includes(query) ||
        log.message.toLowerCase().includes(query)

      const matchesLevel = level === 'ALL' || log.level === level

      return matchesSearch && matchesLevel
    })
  }, [search, level])

  const columns = [
    {
      header: 'Log ID',
      cell: (row: typeof demoLogs[number]) => (
        <span className="font-semibold text-blue-700">{row.id}</span>
      ),
    },
    {
      header: 'Service',
      cell: (row: typeof demoLogs[number]) => (
        <span className="font-mono text-xs text-slate-600">
          {row.service}
        </span>
      ),
    },
    {
      header: 'Severity',
      cell: (row: typeof demoLogs[number]) => (
        <StatusBadge value={row.level} />
      ),
    },
    {
      header: 'Message',
      cell: (row: typeof demoLogs[number]) => (
        <span className="text-slate-700">{row.message}</span>
      ),
    },
    {
      header: 'Timestamp',
      cell: (row: typeof demoLogs[number]) => (
        <span className="whitespace-nowrap text-xs text-slate-500">
          {row.time}
        </span>
      ),
    },
  ]

  const hasFilters = search.trim() !== '' || level !== 'ALL'

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm leading-6 text-slate-500">
          Search, inspect, and filter application events across services.
        </p>
      </section>

      {/* Search and filters */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative min-w-0 flex-1">
            <Search
              className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              aria-hidden="true"
            />

            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by log ID, service, or message..."
              aria-label="Search logs"
              className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <select
            value={level}
            onChange={(event) => setLevel(event.target.value)}
            aria-label="Filter logs by severity"
            className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 lg:w-52"
          >
            {LEVELS.map((item) => (
              <option key={item} value={item}>
                {item === 'ALL'
                  ? 'All severity levels'
                  : item.charAt(0) + item.slice(1).toLowerCase()}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <p className="text-xs text-slate-500" aria-live="polite">
            Showing{' '}
            <span className="font-semibold text-slate-800">
              {filteredLogs.length}
            </span>{' '}
            of {demoLogs.length} records
          </p>

          <button
            type="button"
            onClick={() => {
              setSearch('')
              setLevel('ALL')
            }}
            disabled={!hasFilters}
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-blue-700 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-slate-300 disabled:hover:bg-transparent"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Clear filters
          </button>
        </div>
      </section>

      {/* Logs table */}
      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-900">
            Application Logs
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Event records organized by service, severity, and timestamp.
          </p>
        </div>

        <DataTable
          columns={columns}
          rows={filteredLogs}
          rowKey={(row) => row.id}
        />
      </section>
    </div>
  )
}