import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import SeverityBadge from '../components/common/SeverityBadge'
import StatusBadge from '../components/common/StatusBadge'
import { demoIncidents } from './data'

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
    (incident) => incident.status === 'OPEN' || incident.status === 'INVESTIGATING',
  ).length

  const resolvedCount = demoIncidents.filter(
    (incident) => incident.status === 'RESOLVED',
  ).length

  const criticalCount = demoIncidents.filter(
    (incident) => incident.severity === 'P1',
  ).length

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900">Incident Management</h1>
        <p className="mt-1 text-sm text-slate-500">
          Review and filter illustrative operational incidents.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Total sample incidents</p>
          <p className="mt-1 text-2xl font-semibold">{demoIncidents.length}</p>
        </div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Open / investigating</p>
          <p className="mt-1 text-2xl font-semibold text-amber-600">{openCount}</p>
        </div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Critical incidents</p>
          <p className="mt-1 text-2xl font-semibold text-red-600">{criticalCount}</p>
          <p className="mt-1 text-xs text-slate-500">{resolvedCount} resolved</p>
        </div>
      </section>

      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search incidents..."
              aria-label="Search incidents"
              className="w-full rounded-md border py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
            />
          </div>

          <select
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
            aria-label="Filter by incident severity"
            className="rounded-md border px-3 py-2 text-sm outline-none focus:border-blue-500"
          >
            <option value="ALL">All severities</option>
            <option value="P1">Critical (P1)</option>
            <option value="P2">High (P2)</option>
            <option value="P3">Medium (P3)</option>
            <option value="P4">Low (P4)</option>
          </select>

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            aria-label="Filter by incident status"
            className="rounded-md border px-3 py-2 text-sm outline-none focus:border-blue-500"
          >
            <option value="ALL">All statuses</option>
            <option value="OPEN">Open</option>
            <option value="INVESTIGATING">Investigating</option>
            <option value="MITIGATED">Mitigated</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>

        <div className="mt-3 flex justify-between text-xs text-slate-500">
          <span>{filteredIncidents.length} matching sample records</span>
          <button
            type="button"
            onClick={() => {
              setSearch('')
              setSeverity('ALL')
              setStatus('ALL')
            }}
            className="font-medium text-blue-700 hover:underline"
          >
            Clear filters
          </button>
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border bg-white shadow-sm">
        <div className="border-b px-4 py-3">
          <h2 className="font-semibold text-slate-800">Incident Register</h2>
          <p className="mt-1 text-xs text-slate-500">
            Sample records only. No live incident management system is connected.
          </p>
        </div>

        {filteredIncidents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Incident ID</th>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Service</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Reported</th>
                </tr>
              </thead>
              <tbody>
                {filteredIncidents.map((incident) => (
                  <tr key={incident.id} className="border-t hover:bg-slate-50">
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-blue-700">
                      {incident.id}
                    </td>
                    <td className="min-w-52 px-4 py-3 font-medium text-slate-800">
                      {incident.title}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs">
                      {incident.service}
                    </td>
                    <td className="px-4 py-3">
                      <SeverityBadge value={incident.severity} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge value={incident.status} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                      {incident.time}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-10 text-center text-sm text-slate-500">
            No matching incidents found. Try changing your filters.
          </div>
        )}
      </section>

      <p className="text-xs text-slate-500">
        Demo limitation: creating, assigning, updating, and resolving incidents are disabled.
      </p>
    </div>
  )
}
