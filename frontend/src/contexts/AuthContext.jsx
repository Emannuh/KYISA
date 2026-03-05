import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authAPI } from '../api/endpoints'
import toast from 'react-hot-toast'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('kyisa_user')
    return saved ? JSON.parse(saved) : null
  })
  const [loading, setLoading] = useState(true)

  // On mount, verify token is still valid
  useEffect(() => {
    const tokens = JSON.parse(localStorage.getItem('kyisa_tokens') || '{}')
    if (tokens.access) {
      authAPI.getProfile()
        .then(({ data }) => {
          setUser(data)
          localStorage.setItem('kyisa_user', JSON.stringify(data))
        })
        .catch(() => {
          localStorage.removeItem('kyisa_tokens')
          localStorage.removeItem('kyisa_user')
          setUser(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const { data } = await authAPI.login(email, password)
    const tokens = { access: data.access, refresh: data.refresh }
    localStorage.setItem('kyisa_tokens', JSON.stringify(tokens))
    localStorage.setItem('kyisa_user', JSON.stringify(data.user))
    setUser(data.user)
    toast.success(`Welcome back, ${data.user.first_name}!`)
    return data.user
  }, [])

  const logout = useCallback(async () => {
    try {
      const tokens = JSON.parse(localStorage.getItem('kyisa_tokens') || '{}')
      if (tokens.refresh) await authAPI.logout(tokens.refresh)
    } catch { /* ignore */ }
    localStorage.removeItem('kyisa_tokens')
    localStorage.removeItem('kyisa_user')
    setUser(null)
    toast.success('Logged out')
  }, [])

  const updateUser = useCallback((data) => {
    setUser(data)
    localStorage.setItem('kyisa_user', JSON.stringify(data))
  }, [])

  const value = {
    user,
    loading,
    login,
    logout,
    updateUser,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    isCompetitionManager: user?.role === 'competition_manager',
    isTeamManager: user?.role === 'team_manager',
    isTreasurer: user?.role === 'treasurer',
    isRefereeManager: user?.role === 'referee_manager',
    isReferee: user?.role === 'referee',
    isJuryChair: user?.role === 'jury_chair',
    hasRole: (...roles) => roles.includes(user?.role),
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
