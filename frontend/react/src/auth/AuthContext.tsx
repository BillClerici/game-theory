import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useQuery } from '@apollo/client'
import { ME_QUERY } from '../api/queries'

interface AuthUser {
  id: string
  email: string
  firstName: string
  lastName: string
  isSuperuser: boolean
}

interface AuthState {
  user: AuthUser | null
  loading: boolean
  login: () => void
  logout: () => void
}

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  login: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const token = localStorage.getItem('access_token')
  const { data, loading: queryLoading, error } = useQuery(ME_QUERY, {
    skip: !token,
  })

  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    if (data?.me) {
      setUser({
        id: data.me.id,
        email: data.me.email,
        firstName: data.me.firstName,
        lastName: data.me.lastName,
        isSuperuser: data.me.isSuperuser,
      })
      setLoading(false)
    } else if (error || !queryLoading) {
      setUser(null)
      setLoading(false)
    }
  }, [data, error, queryLoading, token])

  const login = () => {
    window.location.href = '/auth/login/google-oauth2/'
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
    window.location.href = '/'
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
