import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { UNAUTHORIZED_EVENT } from '../services/api'
import { authService } from '../services/authService'
import type { RegisterInput, User } from '../types/auth'
import { tokenStorage } from '../utils/tokenStorage'

export interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (input: RegisterInput) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState<boolean>(() => tokenStorage.get() !== null)

  const clearSession = useCallback(() => {
    tokenStorage.clear()
    setUser(null)
  }, [])

  // Restore the session from a stored token.
  useEffect(() => {
    if (!tokenStorage.get()) return
    authService
      .me()
      .then(setUser)
      .catch(clearSession)
      .finally(() => setLoading(false))
  }, [clearSession])

  // The API layer signals expired/invalid sessions.
  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, clearSession)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, clearSession)
  }, [clearSession])

  const login = useCallback(async (email: string, password: string) => {
    const response = await authService.login(email, password)
    tokenStorage.set(response.access_token)
    setUser(response.user)
  }, [])

  const register = useCallback(
    async (input: RegisterInput) => {
      await authService.register(input)
      await login(input.email, input.password)
    },
    [login],
  )

  const logout = useCallback(async () => {
    try {
      await authService.logout()
    } catch {
      // The local session is cleared regardless of whether the server call succeeded.
    }
    clearSession()
  }, [clearSession])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
