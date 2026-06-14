const BASE = '/api'

export interface Citation {
  source: string
  page?: number
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
}

export interface UploadResponse {
  filename: string
  workspace_id: string
  status: string
  message: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`)
  return resp.json() as Promise<T>
}

export const apiClient = {
  query: (body: QueryRequest) =>
    request<QueryResponse>('/query/', { method: 'POST', body: JSON.stringify(body) }),

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
    request<{ documents: unknown[] }>(`/ingest/documents?workspace_id=${workspaceId}`),
}
