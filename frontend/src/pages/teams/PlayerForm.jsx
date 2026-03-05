import { useState } from 'react'
import toast from 'react-hot-toast'
import { Input, Select, Button } from '../../components/ui'
import { teamsAPI } from '../../api/endpoints'

const POSITIONS = [
  '', 'Goalkeeper', 'Defender', 'Midfielder', 'Forward',
  'Wing Spiker', 'Setter', 'Libero', 'Middle Blocker',
  'Point Guard', 'Shooting Guard', 'Small Forward', 'Power Forward', 'Center',
  'Goal Keeper', 'Left Wing', 'Right Wing', 'Pivot', 'Centre Back',
  'Goal Shooter', 'Goal Attack', 'Wing Attack', 'Centre', 'Wing Defence', 'Goal Defence',
]

export default function PlayerForm({ teamId, player, onSuccess, onCancel }) {
  const [form, setForm] = useState({
    first_name: player?.first_name || '',
    last_name: player?.last_name || '',
    id_number: player?.id_number || '',
    date_of_birth: player?.date_of_birth || '',
    jersey_number: player?.jersey_number || '',
    position: player?.position || '',
    phone: player?.phone || '',
    email: player?.email || '',
  })
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
    setErrors((prev) => ({ ...prev, [e.target.name]: undefined }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setErrors({})
    try {
      if (player) {
        await teamsAPI.updatePlayer(teamId, player.id, form)
        toast.success('Player updated')
      } else {
        await teamsAPI.addPlayer(teamId, form)
        toast.success('Player added')
      }
      onSuccess?.()
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') setErrors(data)
      else toast.error('Failed to save player')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input label="First Name *" name="first_name" value={form.first_name} onChange={handleChange} error={errors.first_name} required />
        <Input label="Last Name *" name="last_name" value={form.last_name} onChange={handleChange} error={errors.last_name} required />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input label="ID Number" name="id_number" value={form.id_number} onChange={handleChange} error={errors.id_number} placeholder="National ID" />
        <Input label="Date of Birth" name="date_of_birth" type="date" value={form.date_of_birth} onChange={handleChange} error={errors.date_of_birth} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input label="Jersey Number" name="jersey_number" type="number" value={form.jersey_number} onChange={handleChange} error={errors.jersey_number} />
        <Select label="Position" name="position" value={form.position} onChange={handleChange} error={errors.position}>
          {POSITIONS.map((p) => <option key={p} value={p}>{p || '— Select —'}</option>)}
        </Select>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input label="Phone" name="phone" value={form.phone} onChange={handleChange} error={errors.phone} />
        <Input label="Email" name="email" type="email" value={form.email} onChange={handleChange} error={errors.email} />
      </div>

      {errors.non_field_errors && (
        <p className="text-sm text-red-400">{errors.non_field_errors}</p>
      )}
      {errors.detail && (
        <p className="text-sm text-red-400">{errors.detail}</p>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
        <Button type="submit" variant="primary" loading={loading}>
          {player ? 'Save Changes' : 'Add Player'}
        </Button>
      </div>
    </form>
  )
}
