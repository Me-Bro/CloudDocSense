import { useEffect, useRef, useState } from 'react'
import { apiClient, type Citation } from '../lib/apiClient'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  grounded?: boolean
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | undefined>()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function patchAssistant(id: string, patch: Partial<Message>) {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    const assistantId = crypto.randomUUID()
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: question },
      { id: assistantId, role: 'assistant', content: '' },
    ])
    setInput('')
    setLoading(true)

    apiClient.streamQuery(
      { question, workspace_id: 'default', conversation_id: conversationId },
      {
        onMeta: (meta) => {
          setConversationId(meta.conversation_id)
          patchAssistant(assistantId, { citations: meta.citations, grounded: meta.grounded })
        },
        onDelta: (text) =>
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + text } : m))
          ),
        onDone: (final) => {
          // The LLM may answer "not found" even when chunks were retrieved —
          // the final event corrects grounded/citations sent provisionally in meta.
          if (final) patchAssistant(assistantId, { grounded: final.grounded, citations: final.citations })
          setLoading(false)
        },
        onError: () => {
          patchAssistant(assistantId, { content: 'Error contacting API.' })
          setLoading(false)
        },
      }
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <p className="text-center text-gray-400 mt-20">Ask anything about your documents.</p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className={
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-2xl px-4 py-2 max-w-lg'
                  : 'bg-white border border-gray-200 rounded-2xl px-4 py-2 max-w-lg'
              }
            >
              <p className="text-sm whitespace-pre-wrap">
                {msg.content || (msg.role === 'assistant' && loading ? '…' : '')}
              </p>
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 text-xs text-gray-500 space-y-0.5">
                  {msg.citations.map((c, i) => (
                    <p key={i}>
                      ↗ {c.source}
                      {c.page ? ` p.${c.page}` : ''}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2 pt-4 border-t border-gray-200">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your documents…"
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-indigo-600 text-white rounded-lg px-5 py-2 text-sm font-medium disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
