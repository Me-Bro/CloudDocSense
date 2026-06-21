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

export interface StreamCallbacks {
  onMeta?: (meta: StreamMeta) => void
  onDelta?: (text: string) => void
  onDone?: () => void
  onError?: (err: unknown) => void
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`)
  return resp.json() as Promise<T>
}

/** Parse a single SSE block ("event: x\ndata: a\ndata: b") into {event, data}. */
function parseSseBlock(block: string): { event: string; data: string } {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
  }
  return { event, data: dataLines.join('\n') }
}

export const apiClient = {
  query: (body: QueryRequest) =>
    request<QueryResponse>('/query/', { method: 'POST', body: JSON.stringify(body) }),

  /** Stream an answer via the SSE endpoint. Returns an abort function. */
  streamQuery(body: QueryRequest, cb: StreamCallbacks): () => void {
    const controller = new AbortController()
    ;(async () => {
      try {
        const resp = await fetch(`${BASE}/query/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          signal: controller.signal,
        })
        if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)

        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        for (;;) {
          const { value, done } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          let idx: number
          while ((idx = buf.indexOf('\n\n')) !== -1) {
            const block = buf.slice(0, idx)
            buf = buf.slice(idx + 2)
            if (!block.trim()) continue
            const { event, data } = parseSseBlock(block)
            if (event === 'meta') cb.onMeta?.(JSON.parse(data) as StreamMeta)
            else if (event === 'delta') cb.onDelta?.(data)
            else if (event === 'done') cb.onDone?.()
          }
        }
        cb.onDone?.()
      } catch (err) {
        if (!controller.signal.aborted) cb.onError?.(err)
      }
    })()
    return () => controller.abort()
  },

  uploadDocument: async (file: File, workspaceId: string): Promise<UploadResponse> => {
    const form = new FormData()
    form.append('file', file)
    const resp = await fetch(`${BASE}/ingest/?workspace_id=${workspaceId}`, {
      method: 'POST',
      body: form,
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`)
    return resp.json() as Promise<UploadResponse>
  },

  listDocuments: (workspaceId: string) =>
    request<{ documents: DocumentInfo[]; workspace_id: string }>(
      `/ingest/documents?workspace_id=${workspaceId}`
    ),
}
