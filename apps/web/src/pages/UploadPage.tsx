import { useCallback, useEffect, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useAuth } from '../contexts/AuthContext'
import { apiClient, type DocumentInfo } from '../lib/apiClient'

const STATUS_STYLE: Record<string, string> = {
  indexed: 'text-green-600',
  pending: 'text-amber-600',
  processing: 'text-amber-600',
  failed: 'text-red-500',
  unsupported: 'text-red-500',
  error: 'text-red-500',
}

const STATUS_DOT: Record<string, string> = {
  indexed: 'bg-green-500',
  pending: 'bg-amber-400 animate-pulse',
  processing: 'bg-amber-400 animate-pulse',
  failed: 'bg-red-500',
  unsupported: 'bg-red-500',
  error: 'bg-red-500',
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function UploadPage() {
  const { workspaceId } = useAuth()
  const WORKSPACE = workspaceId ?? 'default'
  const [docs, setDocs] = useState<DocumentInfo[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<DocumentInfo | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await apiClient.listDocuments(WORKSPACE)
      setDocs(data.documents)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    const inFlight = docs.some((d) => d.status === 'pending' || d.status === 'processing')
    if (!inFlight) return
    const t = setInterval(refresh, 1500)
    return () => clearInterval(t)
  }, [docs, refresh])

  const onDrop = useCallback(
    async (accepted: File[]) => {
      setUploading(true)
      setError(null)
      await Promise.allSettled(accepted.map((f) => apiClient.uploadDocument(f, WORKSPACE)))
      setUploading(false)
      void refresh()
    },
    [refresh]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop })

  async function handleDownload(doc: DocumentInfo) {
    setDownloading(doc.id)
    try {
      await apiClient.downloadDocument(doc.id, doc.filename)
    } catch {
      setError(`Failed to download ${doc.filename}`)
    } finally {
      setDownloading(null)
    }
  }

  async function handleDelete(doc: DocumentInfo) {
    setConfirmDelete(null)
    setDeleting(doc.id)
    try {
      await apiClient.deleteDocument(doc.id)
      await refresh()
    } catch (e) {
      setError(`Failed to delete ${doc.filename}: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-800">Upload Documents</h1>

      <div
        {...getRootProps()}
        className={[
          'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors',
          isDragActive ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-gray-400',
        ].join(' ')}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <p className="text-gray-500">Uploading…</p>
        ) : isDragActive ? (
          <p className="text-indigo-600">Drop files here</p>
        ) : (
          <p className="text-gray-500">Drag & drop files here, or click to select</p>
        )}
        <p className="text-xs text-gray-400 mt-2">PDF, DOCX, TXT supported</p>
      </div>

      {error && (
        <p className="text-sm text-red-500 flex items-center gap-2">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 text-xs underline">
            dismiss
          </button>
        </p>
      )}

      {docs.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-gray-400 px-4 pb-1">
            <span>{docs.length} document{docs.length !== 1 ? 's' : ''}</span>
          </div>
          {docs.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-4 py-3 text-sm gap-4"
            >
              {/* Left: status dot + name + date */}
              <div className="flex items-center gap-3 min-w-0">
                <span className={`shrink-0 w-2 h-2 rounded-full ${STATUS_DOT[d.status] ?? 'bg-gray-400'}`} />
                <div className="min-w-0">
                  <p className="font-medium text-gray-800 truncate">{d.filename}</p>
                  <p className="text-xs text-gray-400">{formatDate(d.created_at)}</p>
                </div>
              </div>

              {/* Right: status badge + actions */}
              <div className="flex items-center gap-3 shrink-0">
                <span className={`text-xs font-medium ${STATUS_STYLE[d.status] ?? 'text-gray-500'}`}>
                  {d.status}
                </span>

                {/* Download */}
                <button
                  onClick={() => handleDownload(d)}
                  disabled={downloading === d.id || deleting === d.id}
                  title="Download"
                  className="p-1.5 rounded-md text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 disabled:opacity-40 transition-colors"
                >
                  {downloading === d.id ? (
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
                    </svg>
                  )}
                </button>

                {/* Delete */}
                <button
                  onClick={() => setConfirmDelete(d)}
                  disabled={deleting === d.id || downloading === d.id}
                  title="Delete"
                  className="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 disabled:opacity-40 transition-colors"
                >
                  {deleting === d.id ? (
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7V4h6v3M3 7h18" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete confirm modal */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4 space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Delete document?</h2>
            <p className="text-sm text-gray-600">
              <span className="font-medium">{confirmDelete.filename}</span> will be permanently removed from storage and the index.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(confirmDelete)}
                className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
