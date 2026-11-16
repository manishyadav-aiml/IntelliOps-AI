import { useMemo, useState } from 'react'
import { RotateCcw, Search } from 'lucide-react'

import MetricCard from '../components/common/MetricCard'
import DataTable from '../components/common/DataTable'
import SeverityBadge from '../components/common/SeverityBadge'

import { demoAnomalies } from './data'

const SEVERITIES = ['ALL', 'P1', 'P2', 'P3', 'P4']

export default function DemoAnomalies() {
  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('ALL')

  const filteredAnomalies = useMemo(() => {
    const query = search.trim().toLowerCase()

    return demoAnomalies.filter((anomaly) => {
      const matchesSearch =
        !query ||
        anomaly.id.toLowerCase().includes(query) ||
        anomaly.service.toLowerCase().includes(query) ||
        anomaly.description.toLowerCase().includes(query)

      const matchesSeverity =
        severity === 'ALL' || anomaly.severity === severity

      return matchesSearch && matchesSeverity
    })
  }, [search, severity])

  const criticalCount = demoAnomalies.filter(
    (item) => item.severity === 'P1',
  ).length

  const affectedServices = new Set(
    demoAnomalies.map((item) => item.service),
  ).size

  const columns = [
    {
      header: 'Anomaly ID',
      cell: (row: typeof demoAnomalies[number]) => (
        <span className="font-semibold text-blue-700">{row.id}</span>
      ),
    },
    {
      header: 'Service',
      cell: (row: typeof demoAnomalies[number]) => (
        <span className="font-mono text-xs text-slate-600">
          {row.service}
        </span>
      ),
    },
    {
      header: 'Description',
      cell: (row: typeof demoAnomalies[number]) => (
        <span className="text-slate-700">{row.description}</span>
      ),
    },
    {
      header: 'Example score',
      cell: (row: typeof demoAnomalies[number]) => (
        <span className="font-semibold tabular-nums text-slate-800">
          {row.score}
        </span>
      ),
    },
    {
      header: 'Severity',
      cell: (row: typeof demoAnomalies[number]) => (
        <SeverityBadge value={row.severity} />
      ),
    },
  ]

  const hasFilters = search.trim() !== '' || severity !== 'ALL'

  return (
    <div className="space-y-6">
      {/* Summary metrics */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard
          label="Total anomalies"
          value={demoAnomalies.length}
          hint="Recorded anomaly entries"
        />

        <MetricCard
          label="Critical anomalies"
          value={criticalCount}
          hint="Priority P1 records"
        />

        <MetricCard
          label="Affected services"
          value={affectedServices}
          hint="Distinct services represented"
        />
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
              placeholder="Search by anomaly ID, service, or description..."
              aria-label="Search anomalies"
              className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <select
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
            aria-label="Filter anomalies by severity"
            className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 lg:w-52"
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
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <p className="text-xs text-slate-500" aria-live="polite">
            Showing{' '}
            <span className="font-semibold text-slate-800">
              {filteredAnomalies.length}
            </span>{' '}
            of {demoAnomalies.length} records
          </p>

          <button
            type="button"
            onClick={() => {
              setSearch('')
              setSeverity('ALL')
            }}
            disabled={!hasFilters}
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-blue-700 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-slate-300 disabled:hover:bg-transparent"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Clear filters
          </button>
        </div>
      </section>

      {/* Anomaly records */}
      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-900">
            Detected Anomalies
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Review anomaly records by affected service, score, and severity.
          </p>
        </div>

        <DataTable
          columns={columns}
          rows={filteredAnomalies}
          rowKey={(row) => row.id}
        />

        <p className="text-xs leading-5 text-slate-400">
          Scores are illustrative values and were not generated by a live
          machine learning model.
        </p>
      </section>
    </div>
  )
}