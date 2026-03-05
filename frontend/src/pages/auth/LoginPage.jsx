import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Helmet } from 'react-helmet-async'
import { useAuth } from '../../contexts/AuthContext'
import { Button, Input } from '../../components/ui'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(email, password)
      navigate('/portal')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Helmet><title>Sign In — KYISA</title></Helmet>
      <div className="min-h-screen bg-brand-900 flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          {/* Logo */}
          <div className="text-center mb-8">
            <Link to="/" className="inline-flex items-center gap-3">
              <div className="h-12 w-12 rounded-xl bg-accent flex items-center justify-center text-brand-900 font-bold text-xl">
                K
              </div>
            </Link>
            <h1 className="mt-4 text-2xl font-bold text-brand-50">Welcome back</h1>
            <p className="mt-1 text-sm text-brand-300">Sign in to KYISA Competition Management System</p>
          </div>

          {/* Form */}
          <div className="bg-surface-elevated border border-border rounded-2xl p-6">
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm"
              >
                {error}
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Email"
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
              <Input
                label="Password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Button type="submit" loading={loading} className="w-full">
                Sign In
              </Button>
            </form>

            <div className="mt-6 text-center text-sm text-brand-300">
              Need to register?{' '}
              <Link to="/register/team" className="text-accent hover:text-accent-light font-medium">
                Register a team
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    </>
  )
}
