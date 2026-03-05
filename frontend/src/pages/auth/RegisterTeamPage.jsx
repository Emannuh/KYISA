import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { Input, Select, Button } from '../../components/ui'
import { teamsAPI } from '../../api/endpoints'
import { SPORT_TYPES } from '../../utils'

const COUNTIES = [
  'Baringo','Bomet','Bungoma','Busia','Elgeyo-Marakwet','Embu','Garissa','Homa Bay',
  'Isiolo','Kajiado','Kakamega','Kericho','Kiambu','Kilifi','Kirinyaga','Kisii',
  'Kisumu','Kitui','Kwale','Laikipia','Lamu','Machakos','Makueni','Mandera',
  'Marsabit','Meru','Migori','Mombasa','Muranga','Nairobi','Nakuru','Nandi',
  'Narok','Nyamira','Nyandarua','Nyeri','Samburu','Siaya','Taita-Taveta','Tana River',
  'Tharaka-Nithi','Trans-Nzoia','Turkana','Uasin Gishu','Vihiga','Wajir','West Pokot',
]

export default function RegisterTeamPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '',
    county: '',
    sport_type: '',
    gender: '',
    contact_phone: '',
    contact_email: '',
  })
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const handleChange = (e) => {
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }))
    setErrors((p) => ({ ...p, [e.target.name]: undefined }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setErrors({})
    try {
      await teamsAPI.create(form)
      toast.success('Team registered successfully! Pending approval.')
      navigate('/portal/teams')
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
      <Helmet><title>Register Team — KYISA</title></Helmet>

      <section className="py-16">
        <div className="max-w-2xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-3xl font-bold text-brand-50 mb-2">Register Your Team</h1>
            <p className="text-brand-300 mb-8">Fill in the details below to register for KYISA competitions</p>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <div className="rounded-xl bg-surface-elevated border border-border p-6 sm:p-8">
              <form onSubmit={handleSubmit} className="space-y-5">
                <Input label="Team Name *" name="name" value={form.name} onChange={handleChange} error={errors.name} placeholder="e.g. Nairobi County U-20" required />
                <Select label="County *" name="county" value={form.county} onChange={handleChange} error={errors.county} required>
                  <option value="">Select County</option>
                  {COUNTIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </Select>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Select label="Sport *" name="sport_type" value={form.sport_type} onChange={handleChange} error={errors.sport_type} required>
                    <option value="">Select Sport</option>
                    {Object.entries(SPORT_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </Select>
                  <Select label="Gender *" name="gender" value={form.gender} onChange={handleChange} error={errors.gender} required>
                    <option value="">Select</option>
                    <option value="male">Men's</option>
                    <option value="female">Women's</option>
                    <option value="mixed">Mixed</option>
                  </Select>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input label="Phone" name="contact_phone" value={form.contact_phone} onChange={handleChange} error={errors.contact_phone} placeholder="+254..." />
                  <Input label="Email" name="contact_email" type="email" value={form.contact_email} onChange={handleChange} error={errors.contact_email} placeholder="team@example.com" />
                </div>

                {errors.non_field_errors && <p className="text-sm text-red-400">{errors.non_field_errors}</p>}
                {errors.detail && <p className="text-sm text-red-400">{errors.detail}</p>}

                <div className="pt-2">
                  <Button type="submit" variant="primary" className="w-full" loading={loading}>
                    Register Team
                  </Button>
                </div>
              </form>
            </div>
          </motion.div>

          <p className="text-center text-sm text-brand-400 mt-6">
            Already registered? <Link to="/login" className="text-accent hover:text-accent-light">Sign in</Link>
          </p>
        </div>
      </section>
    </>
  )
}
