import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { apiClient, type Citation, type ConversationSummary } from '../lib/apiClient'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  grounded?: boolean
}

function relativeTime(iso: string | null): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function ChatPage() {
  const { workspaceId } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | undefined>()
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const refreshHistory = useCallback(async () => {
    try {
      const data = await apiClient.listConversations()
      setConversations(data.conversations)
    } catch {
      // ignore
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  useEffect(() => { void refreshHistory() }, [refreshHistory])

  function startNewChat() {
    setMessages([])
    setConversationId(undefined)
    setInput('')
  }

  async function loadConversation(id: string) {
    try {
      const data = await apiClient.getConversationMessages(id)
      setMessages(
        data.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          citations: m.citations,
        }))
      )
      setConversationId(id)
    } catch {
      // ignore
    }
  }

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    setDeletingId(id)
    try {
      await apiClient.deleteConversation(id)
      if (conversationId === id) startNewChat()
      setConversations((prev) => prev.filter((c) => c.id !== id))
    } finally {
      setDeletingId(null)
    }
  }

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
      { question, workspace_id: workspaceId ?? 'default', conversation_id: conversationId },
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
          if (final) patchAssistant(assistantId, { grounded: final.grounded, citations: final.citations })
          setLoading(false)
          void refreshHistory()
        },
        onError: () => {
          patchAssistant(assistantId, { content: 'Error contacting API.' })
          setLoading(false)
        },
      }
    )
  }

  return (
    <div className="flex h-[calc(100vh-120px)] gap-0">
      {/* ── Sidebar ── */}
      <aside className="w-56 shrink-0 flex flex-col border-r border-gray-200 bg-white">
        <div className="p-3 border-b border-gray-100">
          <button
            onClick={startNewChat}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg py-2 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            New chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {historyLoading ? (
            <p className="text-xs text-gray-400 text-center mt-6">Loading…</p>
          ) : conversations.length === 0 ? (
            <p className="text-xs text-gray-400 text-center mt-6 px-3">No chats yet</p>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => loadConversation(c.id)}
                className={[
                  'group relative mx-2 mb-1 rounded-lg px-3 py-2 cursor-pointer transition-colors',
                  conversationId === c.id
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'hover:bg-gray-50 text-gray-700',
                ].join(' ')}
              >
                <p className="text-xs font-medium truncate pr-5">{c.preview}</p>
                <p className="text-xs text-gray-400 mt-0.5">{relativeTime(c.created_at)}</p>

                {/* delete button */}
                <button
                  onClick={(e) => handleDelete(c.id, e)}
                  disabled={deletingId === c.id}
                  className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 p-0.5 rounded text-gray-400 hover:text-red-500 transition-opacity disabled:opacity-50"
                  title="Delete"
                >
                  {deletingId === c.id ? (
                    <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* ── Chat area ── */}
      <div className="flex flex-col flex-1 min-w-0">
        <div className="flex-1 overflow-y-auto space-y-4 p-4">
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
                        ↗ {c.source}{c.page ? ` p.${c.page}` : ''}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t border-gray-200">
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
    </div>
  )
}
