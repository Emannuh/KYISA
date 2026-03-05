import { useState } from 'react'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { UsersIcon, MagnifyingGlassIcon, PencilIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Spinner, Input, Select, Modal, Button } from '../../components/ui'
import { useFetch, useDebounce, useMutation } from '../../hooks'
import { authAPI } from '../../api/endpoints'
import { formatDate, ROLE_LABELS } from '../../utils'

export default function UsersManagePage() {
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const debouncedSearch = useDebounce(search, 400)
  const [editUser, setEditUser] = useState(null)

  const { data, loading, refetch } = useFetch(
    () => authAPI.listUsers({ search: debouncedSearch || undefined, role: roleFilter || undefined, page_size: 100 }),
    [debouncedSearch, roleFilter]
  )

  const users = data?.results || data || []

  return (
    <>
      <Helmet><title>Users — KYISA Admin</title></Helmet>

      <div className="space-y-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-brand-50">User Management</h1>
          <p className="text-sm text-brand-300">Manage accounts, roles & permissions</p>
        </motion.div>

        <div className="flex flex-col sm:flex-row gap-3 max-w-lg">
          <Input placeholder="Search users..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <Select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
            <option value="">All Roles</option>
            {Object.entries(ROLE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </Select>
        </div>

        {loading ? (
          <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
        ) : users.length > 0 ? (
          <Card>
            <Card.Body className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-brand-300 text-xs uppercase tracking-wider">
                      <th className="px-4 py-3 text-left">User</th>
                      <th className="px-4 py-3 text-left">Email</th>
                      <th className="px-4 py-3 text-center">Role</th>
                      <th className="px-4 py-3 text-center">Status</th>
                      <th className="px-4 py-3 text-center">Joined</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {users.map((u) => (
                      <tr key={u.id} className="hover:bg-brand-800/30 transition-colors">
                        <td className="px-4 py-2.5">
                          <p className="font-medium text-brand-50">{u.first_name} {u.last_name}</p>
                          <p className="text-xs text-brand-400">@{u.username}</p>
                        </td>
                        <td className="px-4 py-2.5 text-brand-200">{u.email}</td>
                        <td className="px-4 py-2.5 text-center">
                          <Badge variant="accent" size="xs">{ROLE_LABELS[u.role] || u.role}</Badge>
                        </td>
                        <td className="px-4 py-2.5 text-center">
                          <Badge variant={u.is_active ? 'success' : 'danger'} size="xs">
                            {u.is_active ? 'Active' : u.is_suspended ? 'Suspended' : 'Inactive'}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5 text-center text-brand-300 text-xs">{formatDate(u.date_joined)}</td>
                        <td className="px-4 py-2.5 text-right">
                          <button
                            onClick={() => setEditUser(u)}
                            className="p-1 rounded hover:bg-brand-700 text-brand-300 hover:text-brand-50 transition-colors"
                          >
                            <PencilIcon className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card.Body>
          </Card>
        ) : (
          <div className="text-center py-16 text-brand-300">
            <UsersIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
            <p>No users found</p>
          </div>
        )}
      </div>

      <Modal open={!!editUser} onClose={() => setEditUser(null)} title="Edit User" size="sm">
        {editUser && <UserEditForm user={editUser} onSuccess={() => { setEditUser(null); refetch() }} onCancel={() => setEditUser(null)} />}
      </Modal>
    </>
  )
}

function UserEditForm({ user, onSuccess, onCancel }) {
  const [role, setRole] = useState(user.role || '')
  const [isActive, setIsActive] = useState(user.is_active)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authAPI.updateUser(user.id, { role, is_active: isActive })
      onSuccess()
    } catch { /* handled */ } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-brand-200 text-sm">{user.first_name} {user.last_name} (@{user.username})</p>
      <Select label="Role" value={role} onChange={(e) => setRole(e.target.value)}>
        {Object.entries(ROLE_LABELS).map(([k, v]) => (
          <option key={k} value={k}>{v}</option>
        ))}
      </Select>
      <div className="flex items-center gap-2">
        <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} id="active" className="rounded border-border bg-surface" />
        <label htmlFor="active" className="text-sm text-brand-200">Active</label>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
        <Button type="submit" variant="primary" loading={loading}>Save</Button>
      </div>
    </form>
  )
}
