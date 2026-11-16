import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import StatusBadge from '../components/common/StatusBadge'
import { demoLogs } from './data'

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

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900">Log Explorer</h1>
        <p className="mt-1 text-sm text-slate-500">
          Explore and filter illustrative application log records.
        </p>
      </section>

      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search log ID, service, or message..."
              aria-label="Search logs"
              className="w-full rounded-md border py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <select
            value={level}
            onChange={(event) => setLevel(event.target.value)}
            aria-label="Filter by severity"
            className="rounded-md border px-3 py-2 text-sm outline-none focus:border-blue-500"
          >
            <option value="ALL">All severity levels</option>
            <option value="CRITICAL">Critical</option>
            <option value="ERROR">Error</option>
            <option value="WARNING">Warning</option>
            <option value="INFO">Info</option>
            <option value="DEBUG">Debug</option>
          </select>
        </div>

        <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
          <span>{filteredLogs.length} matching sample records</span>
          <button
            type="button"
            onClick={() => {
              setSearch('')
              setLevel('ALL')
            }}
            className="font-medium text-blue-700 hover:underline"
          >
            Clear filters
          </button>
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border bg-white shadow-sm">
        <div className="border-b px-4 py-3">
          <h2 className="font-semibold text-slate-800">Application Logs</h2>
          <p className="mt-1 text-xs text-slate-500">
            Static demonstration records. No live log ingestion is active.
          </p>
        </div>

        {filteredLogs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Log ID</th>
                  <th className="px-4 py-3">Service</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Message</th>
                  <th className="px-4 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="border-t hover:bg-slate-50">
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-blue-700">
                      {log.id}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs">
                      {log.service}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge value={log.level} />
                    </td>
                    <td className="min-w-56 px-4 py-3">{log.message}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                      {log.time}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-10 text-center">
            <p className="font-medium text-slate-700">No matching logs found</p>
            <p className="mt-1 text-sm text-slate-500">
              Try changing your search or severity filter.
            </p>
          </div>
        )}
      </section>

      <p className="text-xs text-slate-500">
        Demo limitation: uploading, deleting, and reprocessing logs are not available.
      </p>
    </div>
  )
}
