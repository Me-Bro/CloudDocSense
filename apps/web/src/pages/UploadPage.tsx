import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { apiClient, type UploadResponse } from '../lib/apiClient'

export default function UploadPage() {
  const [results, setResults] = useState<UploadResponse[]>([])
  const [uploading, setUploading] = useState(false)

  const onDrop = useCallback(async (accepted: File[]) => {
    setUploading(true)
    const uploads = await Promise.allSettled(
      accepted.map((f) => apiClient.uploadDocument(f, 'default'))
    )
    const newResults = uploads.map((r, i) =>
      r.status === 'fulfilled'
        ? r.value
        : {
            filename: accepted[i].name,
            workspace_id: 'default',
            status: 'error',
            message: String((r as PromiseRejectedResult).reason),
          }
    )
    setResults((prev) => [...newResults, ...prev])
    setUploading(false)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-800">Upload Documents</h1>
      <div
        {...getRootProps()}
        className={[
          'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-gray-300 hover:border-gray-400',
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
      {results.length > 0 && (
        <div className="space-y-2">
          {results.map((r, i) => (
            <div
              key={i}
              className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm"
            >
              <span className="font-medium text-gray-700">{r.filename}</span>
              <span className={r.status === 'error' ? 'text-red-500' : 'text-gray-500'}>
                {r.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
