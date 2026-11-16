import { useState } from 'react'
import { Bot, Send, User, Sparkles } from 'lucide-react'

const EXAMPLE_QUESTIONS = [
  'Why is the payment service experiencing high latency?',
  'How should I investigate database connection exhaustion?',
  'What are the recommended steps for a P1 incident?',
]

const SAMPLE_RESPONSES: Record<string, string> = {
  [EXAMPLE_QUESTIONS[0]]:
    'Sample investigation guidance:\n\n1. Check payment gateway response times.\n2. Review recent deployment and configuration changes.\n3. Inspect request timeouts and retry patterns.\n4. Compare current latency with the normal baseline.\n5. Escalate to the payment-service owner if the issue persists.\n\nThis is predefined example content, not a live AI-generated diagnosis.',

  [EXAMPLE_QUESTIONS[1]]:
    'Sample troubleshooting guidance:\n\n1. Inspect active and idle database connections.\n2. Check the configured connection-pool limit.\n3. Identify long-running queries and connection leaks.\n4. Review database CPU and memory utilization.\n5. Check application logs for connection timeout errors.\n\nThis is predefined example content, not a live AI-generated diagnosis.',

  [EXAMPLE_QUESTIONS[2]]:
    'Sample P1 incident response checklist:\n\n1. Acknowledge the incident and notify the response team.\n2. Identify affected services and customer impact.\n3. Assign an incident owner.\n4. Investigate recent changes and relevant logs.\n5. Apply an approved mitigation or rollback.\n6. Verify service recovery.\n7. Document the timeline and conduct a post-incident review.\n\nThis is predefined example content, not a live AI-generated diagnosis.',
}

type Message = {
  role: 'user' | 'assistant'
  content: string
}

const INITIAL_MESSAGE: Message = {
  role: 'assistant',
  content:
    'Select one of the suggested operations scenarios below to explore troubleshooting guidance and incident response recommendations.',
}

export default function DemoAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    INITIAL_MESSAGE,
  ])

  const [input, setInput] = useState('')

  const sendMessage = (question: string) => {
    const trimmedQuestion = question.trim()

    if (!trimmedQuestion) return

    const response =
      SAMPLE_RESPONSES[trimmedQuestion] ??
      'No predefined response is available for this question. Try one of the suggested scenarios below. This workspace does not connect to a live AI model.'

    setMessages((previous) => [
      ...previous,
      { role: 'user', content: trimmedQuestion },
      { role: 'assistant', content: response },
    ])

    setInput('')
  }

  return (
    <div className="space-y-6">
      {/* Assistant workspace */}
      <section className="flex min-h-[620px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {/* Conversation header */}
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
            <Bot className="h-5 w-5" aria-hidden="true" />
          </div>

          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-slate-900">
              IntelliOps Assistant
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Operations troubleshooting workspace
            </p>
          </div>

          <span className="ml-auto inline-flex shrink-0 items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
            Example responses
          </span>
        </div>

        {/* Conversation */}
        <div
          className="flex-1 space-y-5 overflow-y-auto bg-slate-50/70 p-5"
          aria-live="polite"
          aria-label="Assistant conversation"
        >
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-3 ${
                message.role === 'user'
                  ? 'justify-end'
                  : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-blue-100 bg-blue-50 text-blue-700">
                  <Bot className="h-4 w-4" aria-hidden="true" />
                </div>
              )}

              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 sm:max-w-[75%] ${
                  message.role === 'user'
                    ? 'rounded-br-md bg-blue-600 text-white shadow-sm'
                    : 'rounded-bl-md border border-slate-200 bg-white text-slate-700 shadow-sm'
                }`}
              >
                <p className="whitespace-pre-line">
                  {message.content}
                </p>
              </div>

              {message.role === 'user' && (
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-200 text-slate-600">
                  <User className="h-4 w-4" aria-hidden="true" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Suggested questions and input */}
        <div className="border-t border-slate-100 bg-white p-5">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles
              className="h-4 w-4 text-blue-600"
              aria-hidden="true"
            />
            <p className="text-xs font-semibold text-slate-700">
              Suggested operations scenarios
            </p>
          </div>

          <div className="mb-5 flex flex-wrap gap-2">
            {EXAMPLE_QUESTIONS.map((question) => (
              <button
                key={question}
                type="button"
                onClick={() => sendMessage(question)}
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs leading-5 text-slate-600 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
              >
                {question}
              </button>
            ))}
          </div>

          <form
            onSubmit={(event) => {
              event.preventDefault()
              sendMessage(input)
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Enter an operations question..."
              aria-label="Enter a question"
              className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />

            <button
              type="submit"
              disabled={!input.trim()}
              aria-label="Send question"
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </button>
          </form>

          <p className="mt-3 text-[11px] leading-5 text-slate-400">
            Responses use predefined examples. Live AI generation,
            retrieval, and backend integrations are not connected.
          </p>
        </div>
      </section>
    </div>
  )
}