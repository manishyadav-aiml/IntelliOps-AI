import { useMemo, useState } from 'react'
import { RotateCcw, Search } from 'lucide-react'

import MetricCard from '../components/common/MetricCard'
import DataTable from '../components/common/DataTable'
import StatusBadge from '../components/common/StatusBadge'

import { demoDocuments } from './data'

export default function DemoDocuments() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('ALL')

  const categories = [
    ...new Set(demoDocuments.map((document) => document.category)),
  ]

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


  const columns = [
    {
      header: 'Document ID',
      cell: (row: typeof demoDocuments[number]) => (
        <span className="font-semibold text-blue-700">{row.id}</span>
      ),
    },
    {
      header: 'Document name',
      cell: (row: typeof demoDocuments[number]) => (
        <span className="font-medium text-slate-800">{row.name}</span>
      ),
    },
    {
      header: 'Category',
      cell: (row: typeof demoDocuments[number]) => (
        <span className="text-slate-600">{row.category}</span>
      ),
    },
    {
      header: 'Entry status',
      cell: () => (<StatusBadge value="LISTED" />
      ),
    },
  ]

  const hasFilters = search.trim() !== '' || category !== 'ALL'

  return (
    <div className="space-y-6">
      {/* Document metrics */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard
          label="Total documents"
          value={demoDocuments.length}
          hint="Document records available"
        />

        <MetricCard
          label="Categories"
          value={categories.length}
          hint="Distinct document groups"
        />

        <MetricCard
          label="Records matching filters"
          value={filteredDocuments.length}
          hint="Updates with search and category filters"
        />
      </section>

      {/* Search and category filter */}
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
              placeholder="Search by document name, ID, or category..."
              aria-label="Search documents"
              className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            aria-label="Filter documents by category"
            className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 lg:w-56"
          >
            <option value="ALL">All categories</option>

            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <p className="text-xs text-slate-500" aria-live="polite">
            Showing{' '}
            <span className="font-semibold text-slate-800">
              {filteredDocuments.length}
            </span>{' '}
            of {demoDocuments.length} records
          </p>

          <button
            type="button"
            onClick={() => {
              setSearch('')
              setCategory('ALL')
            }}
            disabled={!hasFilters}
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-blue-700 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-slate-300 disabled:hover:bg-transparent"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Clear filters
          </button>
        </div>
      </section>

      {/* Document library */}
      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-900">
            Document Library
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Browse operational guides, architecture references, and technical documentation.
          </p>
        </div>

        <DataTable
          columns={columns}
          rows={filteredDocuments}
          rowKey={(row) => row.id}
        />

        <p className="text-xs leading-5 text-slate-400">
          These entries represent document metadata only. File downloads,
          uploads, text extraction, indexing, and retrieval are not active.
        </p>
      </section>
    </div>
  )
}