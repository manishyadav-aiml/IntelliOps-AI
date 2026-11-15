import type { ReactNode } from 'react'

export default function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
        <h1 className="text-2xl font-semibold text-navy-900">IntelliOps AI</h1>
        <h2 className="mb-6 mt-1 text-slate-600">{title}</h2>
        {children}
      </div>
    </main>
  )
}
