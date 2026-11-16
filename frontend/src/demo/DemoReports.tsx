import { useMemo, useState } from 'react'
import { FileBarChart, Search } from 'lucide-react'
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

      const matchesStatus = status === 'ALL' || report.status.toUpperCase() === status

      return matchesSearch && matchesStatus
    })
  }, [search, status])

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900">Operations Reports</h1>
        <p className="mt-1 text-sm text-slate-500">
          Browse example operational and incident reporting records.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <FileBarChart className="h-4 w-4" />
            Sample reports
          </div>
          <p className="mt-2 text-2xl font-semibold">{demoReports.length}</p>
        </div>

        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Report categories</p>
          <p className="mt-2 text-2xl font-semibold">{demoReports.length}</p>
        </div>

        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Demo status</p>
          <p className="mt-2 text-lg font-semibold text-amber-700">Sample only</p>
        </div>
      </section>

      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search report ID, name, or period..."
              aria-label="Search reports"
              className="w-full rounded-md border py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
            />
          </div>

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            aria-label="Filter reports by status"
            className="rounded-md border px-3 py-2 text-sm outline-none focus:border-blue-500"
          >
            <option value="ALL">All statuses</option>
            <option value="SAMPLE">Sample</option>
          </select>
        </div>

        <div className="mt-3 flex justify-between text-xs text-slate-500">
          <span>{filteredReports.length} matching sample reports</span>
          <button
            type="button"
            onClick={() => {
              setSearch('')
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
          <h2 className="font-semibold text-slate-800">Report Register</h2>
          <p className="mt-1 text-xs text-slate-500">
            Illustrative report metadata. No actual report files are available.
          </p>
        </div>

        {filteredReports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Report ID</th>
                  <th className="px-4 py-3">Report name</th>
                  <th className="px-4 py-3">Reporting period</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredReports.map((report) => (
                  <tr key={report.id} className="border-t hover:bg-slate-50">
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-blue-700">
                      {report.id}
                    </td>
                    <td className="min-w-56 px-4 py-3 font-medium text-slate-800">
                      {report.name}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                      {report.period}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge value={report.status.toUpperCase()} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-10 text-center text-sm text-slate-500">
            No matching reports found.
          </div>
        )}
      </section>

      <p className="text-xs text-slate-500">
        Demo limitation: report generation, PDF export, scheduling, and downloads are disabled.
      </p>
    </div>
  )
}
