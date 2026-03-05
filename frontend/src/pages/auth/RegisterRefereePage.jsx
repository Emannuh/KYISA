import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { Input, Select, Button } from '../../components/ui'
import { authAPI } from '../../api/endpoints'

export default function RegisterRefereePage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    password_confirm: '',
    phone: '',
  })
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const handleChange = (e) => {
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }))
    setErrors((p) => ({ ...p, [e.target.name]: undefined }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password !== form.password_confirm) {
      setErrors({ password_confirm: 'Passwords do not match' })
      return
    }
    setLoading(true)
    setErrors({})
    try {
      await authAPI.register({ ...form, role: 'referee' })
      toast.success('Registration successful! Pending admin approval.')
      navigate('/login')
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') setErrors(data)
      else toast.error('Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Helmet><title>Referee Registration — KYISA</title></Helmet>

      <section className="py-16">
        <div className="max-w-2xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-3xl font-bold text-brand-50 mb-2">Referee Registration</h1>
            <p className="text-brand-300 mb-8">Register as a referee for KYISA competitions</p>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <div className="rounded-xl bg-surface-elevated border border-border p-6 sm:p-8">
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input label="First Name *" name="first_name" value={form.first_name} onChange={handleChange} error={errors.first_name} required />
                  <Input label="Last Name *" name="last_name" value={form.last_name} onChange={handleChange} error={errors.last_name} required />
                </div>
                <Input label="Username *" name="username" value={form.username} onChange={handleChange} error={errors.username} required />
                <Input label="Email *" name="email" type="email" value={form.email} onChange={handleChange} error={errors.email} required />
                <Input label="Phone" name="phone" value={form.phone} onChange={handleChange} error={errors.phone} placeholder="+254..." />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input label="Password *" name="password" type="password" value={form.password} onChange={handleChange} error={errors.password} required />
                  <Input label="Confirm Password *" name="password_confirm" type="password" value={form.password_confirm} onChange={handleChange} error={errors.password_confirm} required />
                </div>

                {errors.non_field_errors && <p className="text-sm text-red-400">{errors.non_field_errors}</p>}
                {errors.detail && <p className="text-sm text-red-400">{errors.detail}</p>}

                <div className="pt-2">
                  <Button type="submit" variant="primary" className="w-full" loading={loading}>
                    Register as Referee
                  </Button>
                </div>
              </form>
            </div>
          </motion.div>

          <p className="text-center text-sm text-brand-400 mt-6">
            Already have an account? <Link to="/login" className="text-accent hover:text-accent-light">Sign in</Link>
          </p>
        </div>
      </section>
    </>
  )
}
