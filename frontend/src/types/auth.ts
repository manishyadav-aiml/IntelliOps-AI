export interface User {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RegisterInput {
  email: string
  full_name: string
  password: string
}
