export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : 'unknown'
}

export const ALLOWED_EXTENSIONS = ['.log', '.txt', '.csv']

/** Client-side convenience check only; the backend validates extension and content. */
export function validateLogFile(file: File, maxMb = 50): string | null {
  const name = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))) return 'Only .log, .txt and .csv files are supported.'
  if (file.size === 0) return 'The file is empty.'
  if (file.size > maxMb * 1024 * 1024) return `File is larger than ${maxMb} MB.`
  return null
}
