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

export interface Document {
  id: string
  workspace_id: string
  filename: string
  mime_type: string | null
  status: 'pending' | 'processing' | 'ready' | 'failed'
  created_at: string
}

export interface Workspace {
  id: string
  name: string
  settings: Record<string, unknown>
}
