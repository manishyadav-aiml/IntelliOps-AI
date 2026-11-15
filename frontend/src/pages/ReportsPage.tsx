import { Download } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import DataTable from '../components/common/DataTable'
import EmptyState from '../components/common/EmptyState'
import ErrorMessage from '../components/common/ErrorMessage'
import Pagination from '../components/common/Pagination'
import Spinner from '../components/common/Spinner'
import { useToast } from '../components/common/Toast'
import { reportService } from '../services/knowledgeService'
import type { Report } from '../types/knowledge'
import type { Page } from '../types/logs'
import { getErrorMessage } from '../utils/errors'
import { formatBytes, formatDate } from '../utils/format'

export default function ReportsPage() {
  const { notify } = useToast()
  const [data, setData] = useState<Page<Report> | null>(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { reportService.list(page).then((d) => { setData(d); setError(null) }).catch((e) => setError(getErrorMessage(e))) }, [page])

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold">Reports</h1>
      <p className="text-sm text-slate-600">Generate PDF, CSV or JSON reports from an incident page. Reports keep AI suggestions and human-confirmed findings separate.</p>
      {error && <ErrorMessage message={error} />}
      {!data && !error ? <Spinner /> : data && data.items.length === 0 ? <EmptyState message="No reports yet. Open an incident and choose a format under Reports." /> : data && (
        <>
          <DataTable<Report> rowKey={(r) => r.id} rows={data.items} columns={[
            { header: 'File', cell: (r) => r.filename },
            { header: 'Incident', cell: (r) => <Link to={`/incidents/${r.incident_id}`} className="text-blue-600 hover:underline">INC-{1000 + r.incident_id}</Link> },
            { header: 'Format', cell: (r) => r.format.toUpperCase() },
            { header: 'Size', cell: (r) => formatBytes(r.size_bytes) },
            { header: 'Created', cell: (r) => formatDate(r.created_at) },
            { header: 'Download', cell: (r) => (
              <button type="button" aria-label={`Download ${r.filename}`} onClick={() => void reportService.download(r).catch((e) => notify('error', getErrorMessage(e)))} className="rounded border p-1"><Download className="h-4 w-4" aria-hidden="true" /></button>) },
          ]} />
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />
        </>
      )}
    </section>
  )
}
