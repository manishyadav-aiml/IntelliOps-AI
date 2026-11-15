import { UploadCloud } from 'lucide-react'
import { useRef, useState } from 'react'
import type { DragEvent } from 'react'
import ErrorMessage from '../common/ErrorMessage'
import { logService } from '../../services/logService'
import type { LogUpload } from '../../types/logs'
import { getErrorMessage } from '../../utils/errors'
import { validateLogFile } from '../../utils/format'

export default function UploadDropzone({ onUploaded }: { onUploaded: (upload: LogUpload) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFile = async (file: File | undefined) => {
    if (!file) return
    setError(null)
    const problem = validateLogFile(file)
    if (problem) return setError(problem)
    setProgress(0)
    try {
      onUploaded(await logService.upload(file, setProgress))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setProgress(null)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    void handleFile(event.dataTransfer.files[0])
  }

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center gap-2 rounded-lg border-2 border-dashed bg-white p-8 text-center ${
          dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300'
        }`}
      >
        <UploadCloud className="h-8 w-8 text-slate-400" aria-hidden="true" />
        <p className="text-sm text-slate-600">Drag and drop a .log, .txt or .csv file, or</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={progress !== null}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          Choose file
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".log,.txt,.csv"
          aria-label="Log file"
          className="hidden"
          onChange={(e) => void handleFile(e.target.files?.[0])}
        />
        {progress !== null && (
          <div className="w-full max-w-xs" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-2 rounded bg-slate-200">
              <div className="h-2 rounded bg-blue-600" style={{ width: `${progress}%` }} />
            </div>
            <span className="text-xs text-slate-500">Uploading {progress}%</span>
          </div>
        )}
      </div>
      {error && <ErrorMessage message={error} />}
    </div>
  )
}
