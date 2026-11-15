import axios from 'axios'

/** Extract the backend's {"error": {"message"}} text, or a safe generic fallback. */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'Cannot reach the server. Please check your connection.'
    const message = error.response.data?.error?.message
    if (typeof message === 'string') return message
  }
  return 'Something went wrong. Please try again.'
}
