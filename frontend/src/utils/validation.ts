/** Mirrors the backend password rules (backend/app/schemas/auth.py). The backend remains authoritative. */
export function validatePassword(password: string): string | null {
  if (password.length < 8) return 'Password must be at least 8 characters.'
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password))
    return 'Password must contain at least one letter and one digit.'
  return null
}
