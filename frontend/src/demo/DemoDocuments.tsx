import { useMemo, useState } from 'react'
import { BookOpen, FileText, Search } from 'lucide-react'
import StatusBadge from '../components/common/StatusBadge'
import { demoDocuments } from './data'

export default function DemoDocuments() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('ALL')

  const categories = [...new Set(demoDocuments.map((document) => document.category))]

  const filteredDocuments = useMemo(() => {
    const query = search.trim().toLowerCase()

    return demoDocuments.filter((document) => {
      const matchesSearch =
        !query ||
        document.id.toLowerCase().includes(query) ||
        document.name.toLowerCase().includes(query) ||
        document.category.toLowerCase().includes(query)

      const matchesCategory =
        category === 'ALL' || document.category === category

      return matchesSearch && matchesCategory
    })
  }, [search, category])

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900">Knowledge Documents</h1>
        <p className="mt-1 text-sm text-slate-500">
          Explore example documents that represent a searchable operations knowledge base.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <FileText className="h-4 w-4" />
            Sample documents
          </div>
          <p className="mt-2 text-2xl font-semibold">{demoDocuments.length}</p>
        </div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <BookOpen className="h-4 w-4" />
            Categories
          </div>
          <p className="mt-2 text-2xl font-semibold">{categories.length}</p>
        </div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="text-sm text-slate-500">Example indexed records</div>
          <p className="mt-2 text-2xl font-semibold">
            {demoDocuments.filter((document) => document.status === 'Indexed').length}
          </p>
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
              placeholder="Search document name, ID, or category..."
              aria-label="Search documents"
              className="w-full rounded-md border py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
            />
          </div>

          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            aria-label="Filter documents by category"
            className="rounded-md border px-3 py-2 text-sm outline-none focus:border-blue-500"
          >
            <option value="ALL">All categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>

        <div className="mt-3 flex justify-between text-xs text-slate-500">
          <span>{filteredDocuments.length} matching sample documents</span>
          <button
            type="button"
            onClick={() => {
              setSearch('')
              setCategory('ALL')
            }}
            className="font-medium text-blue-700 hover:underline"
          >
            Clear filters
          </button>
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border bg-white shadow-sm">
        <div className="border-b px-4 py-3">
          <h2 className="font-semibold text-slate-800">Document Library</h2>
          <p className="mt-1 text-xs text-slate-500">
            Illustrative document metadata. These files are not stored or downloadable.
          </p>
        </div>

        {filteredDocuments.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Document ID</th>
                  <th className="px-4 py-3">Document name</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Example status</th>
                </tr>
              </thead>
              <tbody>
                {filteredDocuments.map((document) => (
                  <tr key={document.id} className="border-t hover:bg-slate-50">
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-blue-700">
                      {document.id}
                    </td>
                    <td className="min-w-64 px-4 py-3 font-medium text-slate-800">
                      {document.name}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                      {document.category}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge value={document.status.toUpperCase()} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-10 text-center text-sm text-slate-500">
            No matching documents found.
          </div>
        )}
      </section>

      <p className="text-xs text-slate-500">
        Demo limitation: document uploads, deletion, text extraction, vector indexing, and retrieval are disabled.
      </p>
    </div>
  )
}
