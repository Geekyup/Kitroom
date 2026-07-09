"use client"

import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { authApi, type AuthUser } from "@/lib/auth"

type AuthContextValue = {
  user: AuthUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  async function refreshUser() {
    const current = await authApi.fetchCurrentUser()
    setUser(current)
  }

  useEffect(() => {
    refreshUser().finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    await authApi.login(email, password)
    await refreshUser()
  }

  async function logout() {
    await authApi.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
