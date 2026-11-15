import { RefreshCw, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import ConfirmModal from '../components/common/ConfirmModal'
import EmptyState from '../components/common/EmptyState'
import ErrorMessage from '../components/common/ErrorMessage'
import Pagination from '../components/common/Pagination'
import SearchBar from '../components/common/SearchBar'
import Spinner from '../components/common/Spinner'
import StatusBadge from '../components/common/StatusBadge'
import { useToast } from '../components/common/Toast'
import { documentService } from '../services/knowledgeService'
import type { DocumentItem } from '../types/knowledge'
import type { Page } from '../types/logs'
import { getErrorMessage } from '../utils/errors'
import { formatBytes, formatDate } from '../utils/format'

const ALLOWED = ['.pdf', '.txt', '.md', '.markdown']

export default function DocumentsPage() {
  const { notify } = useToast()
  const input = useRef<HTMLInputElement>(null)
  const [data, setData] = useState<Page<DocumentItem> | null>(null)
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [toDelete, setToDelete] = useState<DocumentItem | null>(null)

  const load = useCallback(async () => {
    try { setData(await documentService.list({ page, q: q || undefined })); setError(null) }
    catch (e) { setError(getErrorMessage(e)) } finally { setLoading(false) }
  }, [page, q])
  useEffect(() => { void load() }, [load])

  const active = data?.items.some((d) => d.status === 'PENDING' || d.status === 'PROCESSING')
  useEffect(() => {
    if (!active) return
    const t = setInterval(() => void load(), 2000)
    return () => clearInterval(t)
  }, [active, load])

  const upload = async (file: File | undefined) => {
    if (!file) return
    if (!ALLOWED.some((ext) => file.name.toLowerCase().endsWith(ext))) return notify('error', 'Only PDF, TXT and Markdown documents are supported.')
    setProgress(0)
    try { await documentService.upload(file, setProgress); notify('success', 'Uploaded. Indexing started.'); setPage(1); await load() }
    catch (e) { notify('error', getErrorMessage(e)) }
    finally { setProgress(null); if (input.current) input.current.value = '' }
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold">Documentation library</h1>
      <div className="rounded-lg border bg-white p-4">
        <p className="mb-2 text-sm text-slate-600">Upload runbooks and guides (PDF, TXT, Markdown). They are chunked, embedded and indexed so the Assistant can answer with citations.</p>
        <input ref={input} type="file" accept=".pdf,.txt,.md,.markdown" aria-label="Document file" onChange={(e) => void upload(e.target.files?.[0])} disabled={progress !== null} />
        {progress !== null && <span role="progressbar" aria-valuenow={progress} className="ml-3 text-sm text-slate-500">Uploading {progress}%</span>}
      </div>
      <SearchBar value={q} onChange={(v) => { setQ(v); setPage(1) }} placeholder="Search documents" label="Search documents" />
      {error && <ErrorMessage message={error} />}
      {loading ? <Spinner /> : data && data.items.length === 0 ? <EmptyState message="No documents yet. Upload a runbook to enable documentation search." /> : data && (
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600"><tr><th className="p-3">Document</th><th className="p-3">Size</th><th className="p-3">Indexing</th><th className="p-3">Pages / chunks</th><th className="p-3">Uploaded</th><th className="p-3">Actions</th></tr></thead>
            <tbody>{data.items.map((d) => (
              <tr key={d.id} className="border-t">
                <td className="p-3">{d.filename}{d.error_message && <div className="text-xs text-red-600">{d.error_message}</div>}</td>
                <td className="p-3">{formatBytes(d.size_bytes)}</td>
                <td className="p-3"><StatusBadge value={d.status} /></td>
                <td className="p-3">{d.page_count || '-'} / {d.chunk_count}</td>
                <td className="p-3">{formatDate(d.created_at)}</td>
                <td className="flex gap-2 p-3">
                  <button type="button" aria-label={`Re-index ${d.filename}`} disabled={d.status === 'PROCESSING'} onClick={() => void documentService.reindex(d.id).then(load).catch((e) => notify('error', getErrorMessage(e)))} className="rounded border p-1 disabled:opacity-40"><RefreshCw className="h-4 w-4" aria-hidden="true" /></button>
                  <button type="button" aria-label={`Delete ${d.filename}`} disabled={d.status === 'PROCESSING'} onClick={() => setToDelete(d)} className="rounded border p-1 text-red-600 disabled:opacity-40"><Trash2 className="h-4 w-4" aria-hidden="true" /></button>
                </td>
              </tr>))}
            </tbody>
          </table>
          <div className="px-3"><Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} /></div>
        </div>
      )}
      <ConfirmModal open={toDelete !== null} title="Delete document" confirmLabel="Delete"
        message={`Delete ${toDelete?.filename ?? ''}? It will also be removed from search.`} onCancel={() => setToDelete(null)}
        onConfirm={() => { const d = toDelete; setToDelete(null); if (d) void documentService.remove(d.id).then(load).catch((e) => notify('error', getErrorMessage(e))) }} />
    </section>
  )
}
