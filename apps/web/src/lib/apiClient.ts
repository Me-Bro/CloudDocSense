import { getToken, signalUnauthorized } from './auth'

const BASE = '/api'

export interface Citation {
  source: string
  page?: number | null
  chunk_id?: string
}

export interface QueryRequest {
  question: string
  workspace_id: string
  conversation_id?: string
}

export interface QueryResponse {
  answer: string
  citations: Citation[]
  grounded: boolean
  workspace_id: string
  conversation_id: string
}

export interface UploadResponse {
  document_id: string
  filename: string
  workspace_id: string
  status: string
  task_id: string
}

export interface DocumentInfo {
  id: string
  filename: string
  mime_type?: string | null
  status: string
  created_at?: string | null
}

export interface StreamMeta {
  conversation_id: string
  grounded: boolean
  citations: Citation[]
}

export interface StreamFinal {
  grounded: boolean
  citations: Citation[]
}

export interface StreamCallbacks {
  onMeta?: (meta: StreamMeta) => void
  onDelta?: (text: string) => void
  onDone?: (final?: StreamFinal) => void
  onError?: (err: unknown) => void
}

export interface UserInfo {
  id: string
  email: string
  display_name: string | null
  is_guest: boolean
  created_at: string | null
}

export interface WorkspaceInfo {
  id: string
  name: string
}

export interface SearchHistoryItem {
  id: string
  query: string
  workspace_id: string
  result_count: number
  created_at: string | null
}

export interface AuthResponse {
  access_token: string
  token_type: string
  is_guest?: boolean
}

export interface ConversationSummary {
  id: string
  workspace_id: string
  preview: string
  created_at: string | null
}

export interface ConversationMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  created_at: string | null
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...init?.headers },
    ...init,
  })
  if (resp.status === 401) {
    signalUnauthorized()
    throw new Error('Unauthorized')
  }
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`)
  return resp.json() as Promise<T>
}

/** Parse a single SSE block into {event, data}. Tolerates CRLF and LF line endings. */
function parseSseBlock(block: string): { event: string; data: string } {
  let event = 'message'
  const dataLines: string[] = []
  for (const raw of block.split(/\r?\n/)) {
    const line = raw.replace(/\r$/, '')
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
  }
  return { event, data: dataLines.join('\n') }
}

export const apiClient = {
  // ── Auth ──────────────────────────────────────────────────────────────────
  register: (email: string, password: string, display_name?: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  loginAsGuest: () =>
    request<AuthResponse>('/auth/guest', { method: 'POST' }),

  getMe: () => request<UserInfo>('/auth/me'),

  // ── Workspaces ────────────────────────────────────────────────────────────
  listWorkspaces: () =>
    request<{ workspaces: WorkspaceInfo[] }>('/workspaces/'),

  createWorkspace: (name: string) =>
    request<WorkspaceInfo>('/workspaces/', { method: 'POST', body: JSON.stringify({ name }) }),

  // ── Query ─────────────────────────────────────────────────────────────────
  query: (body: QueryRequest) =>
    request<QueryResponse>('/query/', { method: 'POST', body: JSON.stringify(body) }),

  streamQuery(body: QueryRequest, cb: StreamCallbacks): () => void {
    const controller = new AbortController()
    ;(async () => {
      try {
        const resp = await fetch(`${BASE}/query/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          body: JSON.stringify(body),
          signal: controller.signal,
        })
        if (resp.status === 401) { signalUnauthorized(); return }
        if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)

        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        let doneFired = false
        for (;;) {
          const { value, done } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          let m: RegExpMatchArray | null
          while ((m = buf.match(/\r\n\r\n|\n\n/)) !== null) {
            const idx = m.index!
            const block = buf.slice(0, idx)
            buf = buf.slice(idx + m[0].length)
            if (!block.trim()) continue
            const { event, data } = parseSseBlock(block)
            if (event === 'meta') cb.onMeta?.(JSON.parse(data) as StreamMeta)
            else if (event === 'delta') cb.onDelta?.(data)
            else if (event === 'done') {
              doneFired = true
              cb.onDone?.(data ? (JSON.parse(data) as StreamFinal) : undefined)
            }
          }
        }
        if (!doneFired) cb.onDone?.()
      } catch (err) {
        if (!controller.signal.aborted) cb.onError?.(err)
      }
    })()
    return () => controller.abort()
  },

  // ── Ingest ────────────────────────────────────────────────────────────────
  uploadDocument: async (file: File, workspaceId: string): Promise<UploadResponse> => {
    const form = new FormData()
    form.append('file', file)
    const resp = await fetch(`${BASE}/ingest/?workspace_id=${workspaceId}`, {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    })
    if (resp.status === 401) { signalUnauthorized(); throw new Error('Unauthorized') }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`)
    return resp.json() as Promise<UploadResponse>
  },

  listDocuments: (workspaceId: string) =>
    request<{ documents: DocumentInfo[]; workspace_id: string }>(
      `/ingest/documents?workspace_id=${workspaceId}`
    ),

  deleteDocument: (docId: string) =>
    request<{ deleted: string }>(`/ingest/documents/${docId}`, { method: 'DELETE' }),

  downloadDocument: async (docId: string, filename: string): Promise<void> => {
    const resp = await fetch(`${BASE}/ingest/documents/${docId}/download`, {
      headers: authHeaders(),
    })
    if (resp.status === 401) { signalUnauthorized(); return }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },

  // ── Conversations ─────────────────────────────────────────────────────────
  listConversations: (limit = 50) =>
    request<{ conversations: ConversationSummary[] }>(`/conversations/?limit=${limit}`),

  getConversationMessages: (id: string) =>
    request<{ conversation_id: string; messages: ConversationMessage[] }>(`/conversations/${id}/messages`),

  deleteConversation: (id: string) =>
    request<{ deleted: string }>(`/conversations/${id}`, { method: 'DELETE' }),

  // ── Search History ─────────────────────────────────────────────────────────
  getSearchHistory: (limit = 50) =>
    request<{ items: SearchHistoryItem[] }>(`/users/me/search-history?limit=${limit}`),

  deleteSearchHistoryEntry: (id: string) =>
    request<{ deleted: string }>(`/users/me/search-history/${id}`, { method: 'DELETE' }),

  clearSearchHistory: () =>
    request<{ cleared: boolean }>('/users/me/search-history', { method: 'DELETE' }),
}
