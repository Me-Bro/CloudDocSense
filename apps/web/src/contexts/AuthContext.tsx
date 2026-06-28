import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { apiClient } from '../lib/apiClient'
import { getToken, setToken, signalUnauthorized } from '../lib/auth'

interface AuthUser {
  id: string
  email: string
  displayName: string | null
}

interface AuthState {
  user: AuthUser | null
  workspaceId: string | null
  isAuthed: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [workspaceId, setWorkspaceId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    setWorkspaceId(null)
  }, [])

  const hydrate = useCallback(async () => {
    const token = getToken()
    if (!token) { setIsLoading(false); return }
    try {
      const [me, wsList] = await Promise.all([apiClient.getMe(), apiClient.listWorkspaces()])
      setUser({ id: me.id, email: me.email, displayName: me.display_name })
      setWorkspaceId(wsList.workspaces[0]?.id ?? null)
    } catch {
      setToken(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void hydrate()
    const handler = () => logout()
    window.addEventListener('ds:unauthorized', handler)
    return () => window.removeEventListener('ds:unauthorized', handler)
  }, [hydrate, logout])

  const afterAuth = async (token: string) => {
    setToken(token)
    const [me, wsList] = await Promise.all([apiClient.getMe(), apiClient.listWorkspaces()])
    setUser({ id: me.id, email: me.email, displayName: me.display_name })
    setWorkspaceId(wsList.workspaces[0]?.id ?? null)
  }

  const login = async (email: string, password: string) => {
    const r = await apiClient.login(email, password)
    await afterAuth(r.access_token)
  }

  const register = async (email: string, password: string, displayName?: string) => {
    const r = await apiClient.register(email, password, displayName)
    await afterAuth(r.access_token)
  }

  return (
    <AuthContext.Provider value={{ user, workspaceId, isAuthed: !!user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
