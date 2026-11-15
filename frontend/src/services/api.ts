import axios from 'axios'
import { tokenStorage } from '../utils/tokenStorage'

export const UNAUTHORIZED_EVENT = 'auth:unauthorized'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = tokenStorage.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url: string = error.config?.url ?? ''
    // A 401 from login itself is just "wrong password"; any other 401 means the session is gone.
    if (error.response?.status === 401 && !url.includes('/auth/login')) {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    }
    return Promise.reject(error)
  },
)
