interface Props {
  page: number
  pageSize: number
  total: number
  onChange: (page: number) => void
}

export default function Pagination({ page, pageSize, total, onChange }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between py-3 text-sm">
      <span className="text-slate-600">
        Page {page} of {pages} ({total} total)
      </span>
      <div className="flex gap-2">
        <button type="button" disabled={page <= 1} onClick={() => onChange(page - 1)} className="rounded border px-3 py-1 disabled:opacity-40">
          Previous
        </button>
        <button type="button" disabled={page >= pages} onClick={() => onChange(page + 1)} className="rounded border px-3 py-1 disabled:opacity-40">
          Next
        </button>
      </div>
    </nav>
  )
}
