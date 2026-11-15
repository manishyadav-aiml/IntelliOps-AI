import { RefreshCw, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ConfirmModal from '../components/common/ConfirmModal'
import ErrorMessage from '../components/common/ErrorMessage'
import Pagination from '../components/common/Pagination'
import Spinner from '../components/common/Spinner'
import StatusBadge from '../components/common/StatusBadge'
import UploadDropzone from '../components/logs/UploadDropzone'
import { logService } from '../services/logService'
import type { LogUpload, Page } from '../types/logs'
import { getErrorMessage } from '../utils/errors'
import { formatBytes, formatDate } from '../utils/format'

const POLL_MS = 2000

export default function LogsPage() {
  const [data, setData] = useState<Page<LogUpload> | null>(null)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [toDelete, setToDelete] = useState<LogUpload | null>(null)

  const load = useCallback(async () => {
    try {
      setData(await logService.list({ page, status: status || undefined, q: search || undefined }))
      setError(null)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [page, status, search])

  useEffect(() => {
    void load()
  }, [load])

  // Poll while any file is still being processed.
  const active = data?.items.some((u) => u.status === 'PENDING' || u.status === 'PROCESSING')
  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => void load(), POLL_MS)
    return () => clearInterval(timer)
  }, [active, load])

  const confirmDelete = async () => {
    if (!toDelete) return
    try {
      await logService.remove(toDelete.id)
      setToDelete(null)
      await load()
    } catch (err) {
      setToDelete(null)
      setError(getErrorMessage(err))
    }
  }

  const retry = async (upload: LogUpload) => {
    try {
      await logService.retry(upload.id)
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold">Log files</h1>
      <UploadDropzone onUploaded={() => { setPage(1); void load() }} />
      {error && <ErrorMessage message={error} />}

      <div className="flex flex-wrap gap-3">
        <input
          type="search"
          aria-label="Search files"
          placeholder="Search by file name"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          className="rounded-md border px-3 py-1.5 text-sm"
        />
        <select
          aria-label="Filter by status"
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1) }}
          className="rounded-md border px-3 py-1.5 text-sm"
        >
          <option value="">All statuses</option>
          {['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <button type="button" onClick={() => void load()} className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm">
          <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh
        </button>
      </div>

      {loading ? (
        <Spinner />
      ) : data && data.items.length === 0 ? (
        <p className="rounded-lg border bg-white p-6 text-center text-slate-500">
          No log files yet. Upload one above to get started.
        </p>
      ) : (
        data && (
          <div className="overflow-x-auto rounded-lg border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="p-3">File</th><th className="p-3">Size</th><th className="p-3">Status</th>
                  <th className="p-3">Entries</th><th className="p-3">Uploaded</th><th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((u) => (
                  <tr key={u.id} className="border-t">
                    <td className="p-3">
                      {u.status === 'COMPLETED' ? (
                        <Link to={`/logs/${u.id}`} className="text-blue-600 hover:underline">{u.filename}</Link>
                      ) : (
                        u.filename
                      )}
                      {u.error_message && <div className="text-xs text-red-600">{u.error_message}</div>}
                    </td>
                    <td className="p-3">{formatBytes(u.size_bytes)}</td>
                    <td className="p-3">
                      <StatusBadge value={u.status} />
                      {u.status === 'PROCESSING' && u.total_lines > 0 && (
                        <span className="ml-2 text-xs text-slate-500">
                          {Math.round((u.processed_lines / u.total_lines) * 100)}%
                        </span>
                      )}
                    </td>
                    <td className="p-3">{u.entry_count}</td>
                    <td className="p-3">{formatDate(u.created_at)}</td>
                    <td className="flex gap-2 p-3">
                      {u.status === 'FAILED' && (
                        <button type="button" onClick={() => void retry(u)} className="rounded border px-2 py-1 text-xs">Retry</button>
                      )}
                      <button
                        type="button"
                        aria-label={`Delete ${u.filename}`}
                        disabled={u.status === 'PROCESSING'}
                        onClick={() => setToDelete(u)}
                        className="rounded border p-1 text-red-600 disabled:opacity-40"
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-3">
              <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />
            </div>
          </div>
        )
      )}

      <ConfirmModal
        open={toDelete !== null}
        title="Delete log file"
        message={`Delete ${toDelete?.filename ?? ''} and all its parsed entries? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={() => void confirmDelete()}
        onCancel={() => setToDelete(null)}
      />
    </section>
  )
}
