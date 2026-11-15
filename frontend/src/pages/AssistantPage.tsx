import { useState } from 'react'
import type { FormEvent } from 'react'
import ErrorMessage from '../components/common/ErrorMessage'
import { ragService } from '../services/knowledgeService'
import type { RagResponse } from '../types/knowledge'
import { getErrorMessage } from '../utils/errors'

interface Turn { question: string; response?: RagResponse; error?: string }

export default function AssistantPage() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<number | null>(null)

  const ask = async (e: FormEvent) => {
    e.preventDefault()
    const q = question.trim()
    if (!q) return
    setBusy(true); setQuestion('')
    const index = turns.length
    setTurns((t) => [...t, { question: q }])
    try {
      const response = await ragService.query(q)
      setTurns((t) => t.map((x, i) => (i === index ? { ...x, response } : x)))
      setSelected(index)
    } catch (err) {
      setTurns((t) => t.map((x, i) => (i === index ? { ...x, error: getErrorMessage(err) } : x)))
    } finally { setBusy(false) }
  }

  const citations = selected !== null ? turns[selected]?.response?.citations ?? [] : []

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Documentation assistant</h1>
      <p className="text-sm text-slate-600">Answers come only from your uploaded documentation and always list their sources. If the documents do not cover the question, you will be told.</p>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <div className="min-h-48 space-y-4 rounded-lg border bg-white p-4" aria-live="polite">
            {turns.length === 0 && <p className="text-sm text-slate-500">Ask a question, for example “What should I check when payments time out?”.</p>}
            {turns.map((t, i) => (
              <div key={i} className="space-y-1 text-sm">
                <p className="font-medium">You: {t.question}</p>
                {!t.response && !t.error && <p className="text-slate-500">Searching documents…</p>}
                {t.error && <ErrorMessage message={t.error} />}
                {t.response && (
                  <div onClick={() => setSelected(i)} className={`cursor-pointer rounded p-2 ${selected === i ? 'bg-blue-50' : ''}`}>
                    <p>{t.response.answer}</p>
                    {t.response.notice && <p className="mt-1 text-xs text-amber-700">{t.response.notice}</p>}
                    {!t.response.llm_used && t.response.sufficient && <p className="text-xs text-slate-500">Showing excerpts only (no AI-written answer).</p>}
                    <p className="mt-1 text-xs text-slate-500">{t.response.citations.length} source(s)</p>
                  </div>
                )}
              </div>
            ))}
          </div>
          <form onSubmit={ask} className="flex gap-2">
            <input aria-label="Question" value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={1000} placeholder="Ask about your documentation" className="flex-1 rounded border px-3 py-2" />
            <button type="submit" disabled={busy} className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-60">Ask</button>
          </form>
        </div>
        <aside aria-label="Sources" className="rounded-lg border bg-white p-4 text-sm">
          <h2 className="mb-2 font-medium">Sources</h2>
          {citations.length === 0 ? <p className="text-slate-500">Select an answer to see its sources.</p> : (
            <ul className="space-y-3">{citations.map((c) => (
              <li key={c.label}>
                <p className="font-medium">[{c.label}] {c.document_name}{c.page_number ? `, page ${c.page_number}` : ''}</p>
                <p className="text-xs text-slate-500">chunk {c.chunk_id} · match score {c.score.toFixed(2)}</p>
                <p className="mt-1 text-slate-700">{c.snippet}</p>
              </li>))}
            </ul>
          )}
        </aside>
      </div>
    </section>
  )
}
