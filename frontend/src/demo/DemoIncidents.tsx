import { useMemo, useState } from 'react'
import { RotateCcw, Search } from 'lucide-react'

import MetricCard from '../components/common/MetricCard'
import DataTable from '../components/common/DataTable'
import SeverityBadge from '../components/common/SeverityBadge'
import StatusBadge from '../components/common/StatusBadge'

import { demoIncidents } from './data'

const SEVERITIES = ['ALL', 'P1', 'P2', 'P3', 'P4']

const STATUSES = [
  'ALL',
  'OPEN',
  'INVESTIGATING',
  'MITIGATED',
  'RESOLVED',
]

export default function DemoIncidents() {
  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('ALL')
  const [status, setStatus] = useState('ALL')

  const filteredIncidents = useMemo(() => {
    const query = search.trim().toLowerCase()

    return demoIncidents.filter((incident) => {
      const matchesSearch =
        !query ||
        incident.id.toLowerCase().includes(query) ||
        incident.title.toLowerCase().includes(query) ||
        incident.service.toLowerCase().includes(query)

      const matchesSeverity =
        severity === 'ALL' || incident.severity === severity

      const matchesStatus =
        status === 'ALL' || incident.status === status

      return matchesSearch && matchesSeverity && matchesStatus
    })
  }, [search, severity, status])

  const openCount = demoIncidents.filter(
    (incident) =>
      incident.status === 'OPEN' ||
      incident.status === 'INVESTIGATING',
  ).length

  const resolvedCount = demoIncidents.filter(
    (incident) => incident.status === 'RESOLVED',
  ).length

  const criticalCount = demoIncidents.filter(
    (incident) => incident.severity === 'P1',
  ).length

  const columns = [
    {
      header: 'Incident ID',
      cell: (row: typeof demoIncidents[number]) => (
        <span className="font-semibold text-blue-700">{row.id}</span>
      ),
    },
    {
      header: 'Incident',
      cell: (row: typeof demoIncidents[number]) => (
        <span className="font-medium text-slate-800">{row.title}</span>
      ),
    },
    {
      header: 'Service',
      cell: (row: typeof demoIncidents[number]) => (
        <span className="font-mono text-xs text-slate-600">
          {row.service}
        </span>
      ),
    },
    {
      header: 'Severity',
      cell: (row: typeof demoIncidents[number]) => (
        <SeverityBadge value={row.severity} />
      ),
    },
    {
      header: 'Status',
      cell: (row: typeof demoIncidents[number]) => (
        <StatusBadge value={row.status} />
      ),
    },
    {
      header: 'Reported',
      cell: (row: typeof demoIncidents[number]) => (
        <span className="whitespace-nowrap text-xs text-slate-500">
          {row.time}
        </span>
      ),
    },
  ]

  const hasFilters =
    search.trim() !== '' ||
    severity !== 'ALL' ||
    status !== 'ALL'

  return (
    <div className="space-y-6">
      {/* Incident metrics */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard
          label="Total incidents"
          value={demoIncidents.length}
          hint="Recorded incident entries"
        />

        <MetricCard
          label="Open / investigating"
          value={openCount}
          hint="Requiring attention"
        />

        <MetricCard
          label="Critical incidents"
          value={criticalCount}
          hint={`${resolvedCount} resolved incident`}
        />
      </section>

      {/* Search and filters */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <div className="relative min-w-0">
            <Search
              className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              aria-hidden="true"
            />

            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search incidents..."
              aria-label="Search incidents"
              className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <select
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
            aria-label="Filter incidents by severity"
            className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          >
            {SEVERITIES.map((item) => (
              <option key={item} value={item}>
                {item === 'ALL'
                  ? 'All severities'
                  : item === 'P1'
                    ? 'Critical (P1)'
                    : item === 'P2'
                      ? 'High (P2)'
                      : item === 'P3'
                        ? 'Medium (P3)'
                        : 'Low (P4)'}
              </option>
            ))}
          </select>

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            aria-label="Filter incidents by status"
            className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          >
            {STATUSES.map((item) => (
              <option key={item} value={item}>
                {item === 'ALL'
                  ? 'All statuses'
                  : item.charAt(0) + item.slice(1).toLowerCase()}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <p className="text-xs text-slate-500" aria-live="polite">
            Showing{' '}
            <span className="font-semibold text-slate-800">
              {filteredIncidents.length}
            </span>{' '}
            of {demoIncidents.length} records
          </p>

          <button
            type="button"
            onClick={() => {
              setSearch('')
              setSeverity('ALL')
              setStatus('ALL')
            }}
            disabled={!hasFilters}
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-blue-700 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-slate-300 disabled:hover:bg-transparent"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Clear filters
          </button>
        </div>
      </section>

      {/* Incident register */}
      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-900">
            Incident Register
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Review incidents by service, priority, and response status.
          </p>
        </div>

        <DataTable
          columns={columns}
          rows={filteredIncidents}
          rowKey={(row) => row.id}
        />

        <p className="text-xs leading-5 text-slate-400">
          These are illustrative records. Creating, assigning, updating,
          and resolving incidents is not available in this workspace.
        </p>
      </section>
    </div>
  )
}