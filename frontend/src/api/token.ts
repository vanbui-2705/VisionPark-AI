const KEY = 'visionpark.access_token'

export function getToken(): string | null {
  return localStorage.getItem(KEY)
}
export function setToken(token: string): void {
  localStorage.setItem(KEY, token)
}
export function removeToken(): void {
  localStorage.removeItem(KEY)
}
export const TOKEN_KEY = KEY
