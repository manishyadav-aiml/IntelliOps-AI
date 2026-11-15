const KEY = 'intelliops.access_token'

// localStorage is readable by any script on the page (XSS risk); see SECURITY.md.
export const tokenStorage = {
  get: (): string | null => localStorage.getItem(KEY),
  set: (token: string): void => localStorage.setItem(KEY, token),
  clear: (): void => localStorage.removeItem(KEY),
}
