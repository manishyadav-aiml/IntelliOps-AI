import { useMemo, useState } from 'react'
import { RotateCcw, Search } from 'lucide-react'

import MetricCard from '../components/common/MetricCard'
import DataTable from '../components/common/DataTable'
import StatusBadge from '../components/common/StatusBadge'

import { demoReports } from './data'

export default function DemoReports() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('ALL')

  const filteredReports = useMemo(() => {
    const query = search.trim().toLowerCase()

    return demoReports.filter((report) => {
      const matchesSearch =
        !query ||
        report.id.toLowerCase().includes(query) ||
        report.name.toLowerCase().includes(query) ||
        report.period.toLowerCase().includes(query)

      const matchesStatus =
        status === 'ALL' || report.status.toUpperCase() === status

      return matchesSearch && matchesStatus
    })
  }, [search, status])

  const sampleCount = demoReports.filter(
    (report) => report.status.toUpperCase() === 'SAMPLE',
  ).length

  const reportingPeriodCount = new Set(
    demoReports.map((report) => report.period),
  ).size

  const columns = [
    {
      header: 'Report ID',
      cell: (row: typeof demoReports[number]) => (
        <span className="font-semibold text-blue-700">{row.id}</span>
      ),
    },
    {
      header: 'Report name',
      cell: (row: typeof demoReports[number]) => (
        <span className="font-medium text-slate-800">{row.name}</span>
      ),
    },
    {
      header: 'Reporting period',
      cell: (row: typeof demoReports[number]) => (
        <span className="whitespace-nowrap text-slate-600">
          {row.period}
        </span>
      ),
    },
    {
      header: 'Status',
      cell: (row: typeof demoReports[number]) => (
        <StatusBadge value={row.status.toUpperCase()} />
      ),
    },
  ]

  const hasFilters = search.trim() !== '' || status !== 'ALL'

  return (
    <div className="space-y-6">
      {/* Report metrics */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard
          label="Available reports"
          value={demoReports.length}
          hint="Report records in this workspace"
        />

        <MetricCard
          label="Sample reports"
          value={sampleCount}
          hint="Illustrative report entries"
        />

        <MetricCard
          label="Reporting periods"
          value={reportingPeriodCount}
          hint="Distinct periods represented"
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
              placeholder="Search by report ID, name, or period..."
              aria-label="Search reports"
              className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            aria-label="Filter reports by status"
            className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 lg:w-52"
          >
            <option value="ALL">All statuses</option>
            <option value="SAMPLE">Sample</option>
          </select>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <p className="text-xs text-slate-500" aria-live="polite">
            Showing{' '}
            <span className="font-semibold text-slate-800">
              {filteredReports.length}
            </span>{' '}
            of {demoReports.length} records
          </p>

          <button
            type="button"
            onClick={() => {
              setSearch('')
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

      {/* Report register */}
      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-900">
            Report Register
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Browse operational summaries, incident analysis, and service health reports.
          </p>
        </div>

        <DataTable
          columns={columns}
          rows={filteredReports}
          rowKey={(row) => row.id}
        />

        <p className="text-xs leading-5 text-slate-400">
          These entries contain illustrative report metadata only.
          Report generation, PDF export, scheduling, and downloads are not active.
        </p>
      </section>
    </div>
  )
}