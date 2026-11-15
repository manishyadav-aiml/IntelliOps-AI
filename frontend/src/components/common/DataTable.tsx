import type { ReactNode } from 'react'

export interface Column<T> { header: string; cell: (row: T) => ReactNode }
interface Props<T> { columns: Column<T>[]; rows: T[]; rowKey: (row: T) => string | number }

/** Small presentational table used by the list pages. */
export default function DataTable<T>({ columns, rows, rowKey }: Props<T>) {
  return (
    <div className="overflow-x-auto rounded-lg border bg-white">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-slate-600">
          <tr>{columns.map((c) => <th key={c.header} className="p-3">{c.header}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-t">
              {columns.map((c) => <td key={c.header} className="p-3 align-top">{c.cell(row)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
