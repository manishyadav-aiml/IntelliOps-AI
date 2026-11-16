import { useState } from 'react'
import { Bot, Send, User } from 'lucide-react'

const EXAMPLE_QUESTIONS = [
  'Why is the payment service experiencing high latency?',
  'How should I investigate database connection exhaustion?',
  'What are the recommended steps for a P1 incident?',
]

const SAMPLE_RESPONSES: Record<string, string> = {
  [EXAMPLE_QUESTIONS[0]]:
    'Sample investigation guidance:\n\n1. Check payment gateway response times.\n2. Review recent deployment and configuration changes.\n3. Inspect request timeouts and retry patterns.\n4. Compare current latency with the normal baseline.\n5. Escalate to the payment-service owner if the issue persists.\n\nThis is predefined demonstration content, not a live AI-generated diagnosis.',

  [EXAMPLE_QUESTIONS[1]]:
    'Sample troubleshooting guidance:\n\n1. Inspect active and idle database connections.\n2. Check the configured connection-pool limit.\n3. Identify long-running queries and connection leaks.\n4. Review database CPU and memory utilization.\n5. Check application logs for connection timeout errors.\n\nThis is predefined demonstration content, not a live AI-generated diagnosis.',

  [EXAMPLE_QUESTIONS[2]]:
    'Sample P1 incident response checklist:\n\n1. Acknowledge the incident and notify the response team.\n2. Identify affected services and customer impact.\n3. Assign an incident owner.\n4. Investigate recent changes and relevant logs.\n5. Apply an approved mitigation or rollback.\n6. Verify service recovery.\n7. Document the timeline and conduct a post-incident review.\n\nThis is predefined demonstration content, not a live AI-generated diagnosis.',
}

type Message = {
  role: 'user' | 'assistant'
  content: string
}

export default function DemoAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Welcome to the IntelliOps AI demonstration assistant. Choose an example question below to explore predefined operations guidance.',
    },
  ])

  const [input, setInput] = useState('')

  const sendMessage = (question: string) => {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) return

    const response =
      SAMPLE_RESPONSES[trimmedQuestion] ??
      'No predefined response is available for this question. Try one of the example questions above. This demonstration does not connect to a live AI model.'

    setMessages((previous) => [
      ...previous,
      { role: 'user', content: trimmedQuestion },
      { role: 'assistant', content: response },
    ])

    setInput('')
  }

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900">Operations Assistant</h1>
        <p className="mt-1 text-sm text-slate-500">
          Explore example troubleshooting guidance for common operations scenarios.
        </p>
      </section>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        <strong>Simulation notice:</strong> Responses are predefined examples.
        No LLM, RAG pipeline, knowledge base, or backend service is connected.
      </div>

      <section className="flex min-h-[480px] flex-col overflow-hidden rounded-lg border bg-white shadow-sm">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <div className="rounded-full bg-blue-100 p-2 text-blue-700">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-semibold text-slate-800">IntelliOps Assistant</h2>
            <p className="text-xs text-slate-500">Predefined demonstration mode</p>
          </div>
          <span className="ml-auto rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800">
            Simulated
          </span>
        </div>

        <div
          className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-4"
          aria-live="polite"
          aria-label="Assistant conversation"
        >
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.role === 'assistant' && (
                <div className="h-fit rounded-full bg-blue-100 p-2 text-blue-700">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              <div
                className={`max-w-[85%] rounded-lg px-4 py-3 text-sm leading-6 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'border bg-white text-slate-700 shadow-sm'
                }`}
              >
                <p className="whitespace-pre-line">{message.content}</p>
              </div>

              {message.role === 'user' && (
                <div className="h-fit rounded-full bg-slate-200 p-2 text-slate-600">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="border-t bg-white p-4">
          <p className="mb-3 text-xs font-medium text-slate-500">
            Try an example question
          </p>

          <div className="mb-4 flex flex-wrap gap-2">
            {EXAMPLE_QUESTIONS.map((question) => (
              <button
                key={question}
                type="button"
                onClick={() => sendMessage(question)}
                className="rounded-full border border-blue-200 bg-blue-50 px-3 py-2 text-left text-xs text-blue-800 transition hover:bg-blue-100"
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
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Try an example question..."
              aria-label="Enter a question"
              className="min-w-0 flex-1 rounded-md border px-3 py-2 text-sm outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              aria-label="Send question"
              className="rounded-md bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </section>
    </div>
  )
}
