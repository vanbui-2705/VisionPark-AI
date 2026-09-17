import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authApi } from '../../api/authApi.ts'
import { setUnauthorizedHandler } from '../../api/client.ts'
import { getToken, removeToken, setToken } from '../../api/token.ts'
import type { CurrentUser } from '../../api/types.ts'
import { ApiError } from '../../api/errors.ts'

export interface AuthContextValue {
  user: CurrentUser | null
  token: string | null
  initialized: boolean
  loading: boolean
  error: string | null
  login(username: string, password: string): Promise<void>
  logout(): void
  refreshCurrentUser(): Promise<void>
  isAuthenticated: boolean
  isAdmin: boolean
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [token, setTokenState] = useState<string | null>(() => getToken())
  const [initialized, setInitialized] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const logout = useCallback(() => {
    removeToken()
    setTokenState(null)
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null)
      setTokenState(null)
      if (window.location.pathname !== '/login') {
        const returnUrl = window.location.pathname + window.location.search
        window.location.assign(`/login?returnUrl=${encodeURIComponent(returnUrl)}`)
      }
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  const refreshCurrentUser = useCallback(async () => {
    const t = getToken()
    if (!t) {
      setInitialized(true)
      return
    }
    setLoading(true)
    try {
      const u = await authApi.me()
      setUser(u)
      setTokenState(t)
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 401) {
        removeToken()
        setTokenState(null)
        setUser(null)
      } else {
        // network/5xx: do not clear token, keep unauthenticated state with error
        setError(e instanceof Error ? e.message : 'Failed to load user')
      }
    } finally {
      setLoading(false)
      setInitialized(true)
    }
  }, [])

  useEffect(() => {
    void refreshCurrentUser()
  }, [refreshCurrentUser])

  const login = useCallback(
    async (username: string, password: string) => {
      setLoading(true)
      setError(null)
      try {
        const res = await authApi.login(username, password)
        const tok = res.access_token
        if (!tok) throw new Error('Missing access_token in login response')
        setToken(tok)
        setTokenState(tok)
        const u = await authApi.me()
        setUser(u)
      } catch (e: unknown) {
        removeToken()
        setTokenState(null)
        setUser(null)
        if (e instanceof ApiError) throw e
        throw e as Error
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      initialized,
      loading,
      error,
      login,
      logout,
      refreshCurrentUser,
      isAuthenticated: !!user && !!token,
      isAdmin: user?.role === 'ADMIN',
    }),
    [user, token, initialized, loading, error, login, logout, refreshCurrentUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
