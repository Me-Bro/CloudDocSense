import { useCallback, useEffect, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { apiClient, type DocumentInfo } from '../lib/apiClient'

const WORKSPACE = 'default'

const STATUS_STYLE: Record<string, string> = {
  indexed: 'text-green-600',
  pending: 'text-amber-600',
  processing: 'text-amber-600',
  failed: 'text-red-500',
  unsupported: 'text-red-500',
  error: 'text-red-500',
}

export default function UploadPage() {
  const [docs, setDocs] = useState<DocumentInfo[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await apiClient.listDocuments(WORKSPACE)
      setDocs(data.documents)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  // Initial load + poll while anything is still pending/processing.
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

      {error && <p className="text-sm text-red-500">{error}</p>}

      {docs.length > 0 && (
        <div className="space-y-2">
          {docs.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm"
            >
              <span className="font-medium text-gray-700">{d.filename}</span>
              <span className={STATUS_STYLE[d.status] ?? 'text-gray-500'}>{d.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
