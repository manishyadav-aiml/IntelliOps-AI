import type { RegisterInput, TokenResponse, User } from '../types/auth'
import { api } from './api'

export const authService = {
  register: async (input: RegisterInput): Promise<User> =>
    (await api.post<User>('/auth/register', input)).data,
  login: async (email: string, password: string): Promise<TokenResponse> =>
    (await api.post<TokenResponse>('/auth/login', { email, password })).data,
  me: async (): Promise<User> => (await api.get<User>('/auth/me')).data,
  logout: async (): Promise<void> => {
    await api.post('/auth/logout')
  },
}
