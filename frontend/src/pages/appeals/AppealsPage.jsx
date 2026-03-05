import { useState } from 'react'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { ScaleIcon, PlusIcon, EyeIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Button, Spinner, Input, Select, Modal } from '../../components/ui'
import { useFetch, useMutation } from '../../hooks'
import { useAuth } from '../../contexts/AuthContext'
import { formatDate } from '../../utils'
import apiClient from '../../api/client'

const appealsAPI = {
  list: (params) => apiClient.get('/appeals/', { params }),
  create: (data) => apiClient.post('/appeals/', data),
  get: (id) => apiClient.get(`/appeals/${id}/`),
  respond: (id, data) => apiClient.post(`/appeals/${id}/respond/`, data),
}

export default function AppealsPage() {
  const { isAdmin } = useAuth()
  const [statusFilter, setStatusFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [viewAppeal, setViewAppeal] = useState(null)

  const { data, loading, refetch } = useFetch(
    () => appealsAPI.list({ status: statusFilter || undefined, page_size: 50 }),
    [statusFilter]
  )

  const appeals = data?.results || data || []

  return (
    <>
      <Helmet><title>Appeals — KYISA Portal</title></Helmet>

      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-2xl font-bold text-brand-50">Appeals</h1>
            <p className="text-sm text-brand-300">Submit and track appeals, disciplinary reviews</p>
          </motion.div>
          {!isAdmin && (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              <PlusIcon className="h-4 w-4 mr-1" /> File Appeal
            </Button>
          )}
        </div>

        <div className="max-w-xs">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="under_review">Under Review</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </Select>
        </div>

        {loading ? (
          <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
        ) : appeals.length > 0 ? (
          <div className="space-y-3">
            {appeals.map((appeal) => (
              <Card key={appeal.id}>
                <Card.Body className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        variant={
                          appeal.status === 'resolved' ? 'success' :
                          appeal.status === 'dismissed' ? 'danger' :
                          appeal.status === 'under_review' ? 'accent' : 'warning'
                        }
                        size="xs"
                      >
                        {appeal.status?.replace('_', ' ')}
                      </Badge>
                      <span className="text-xs text-brand-400">{formatDate(appeal.created_at)}</span>
                    </div>
                    <h3 className="font-medium text-brand-50 truncate">{appeal.subject || appeal.title || 'Appeal'}</h3>
                    <p className="text-sm text-brand-300 truncate">{appeal.description || appeal.reason || '—'}</p>
                  </div>
                  <button onClick={() => setViewAppeal(appeal)} className="p-2 rounded-lg hover:bg-brand-700 text-brand-300 hover:text-brand-50 transition-colors">
                    <EyeIcon className="h-5 w-5" />
                  </button>
                </Card.Body>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 text-brand-300">
            <ScaleIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
            <p>{statusFilter ? `No ${statusFilter} appeals` : 'No appeals filed'}</p>
          </div>
        )}
      </div>

      {/* View Modal */}
      <Modal open={!!viewAppeal} onClose={() => setViewAppeal(null)} title="Appeal Details" size="lg">
        {viewAppeal && (
          <div className="space-y-4">
            <div>
              <p className="text-xs text-brand-400 uppercase tracking-wider">Subject</p>
              <p className="text-brand-50 font-medium">{viewAppeal.subject || viewAppeal.title}</p>
            </div>
            <div>
              <p className="text-xs text-brand-400 uppercase tracking-wider">Description</p>
              <p className="text-brand-200 text-sm whitespace-pre-wrap">{viewAppeal.description || viewAppeal.reason}</p>
            </div>
            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs text-brand-400 uppercase tracking-wider">Status</p>
                <Badge variant={viewAppeal.status === 'resolved' ? 'success' : 'warning'} size="sm" className="mt-1">
                  {viewAppeal.status?.replace('_', ' ')}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-brand-400 uppercase tracking-wider">Filed</p>
                <p className="text-brand-200 text-sm mt-1">{formatDate(viewAppeal.created_at)}</p>
              </div>
            </div>
            {viewAppeal.response && (
              <div className="rounded-lg bg-surface border border-border p-4">
                <p className="text-xs text-brand-400 uppercase tracking-wider mb-1">Response</p>
                <p className="text-brand-200 text-sm whitespace-pre-wrap">{viewAppeal.response}</p>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="File an Appeal" size="md">
        <AppealForm onSuccess={() => { setShowCreate(false); refetch() }} onCancel={() => setShowCreate(false)} />
      </Modal>
    </>
  )
}

function AppealForm({ onSuccess, onCancel }) {
  const [form, setForm] = useState({ subject: '', description: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await appealsAPI.create(form)
      onSuccess?.()
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input label="Subject" value={form.subject} onChange={(e) => setForm((p) => ({ ...p, subject: e.target.value }))} required />
      <div>
        <label className="block text-sm font-medium text-brand-200 mb-1">Description</label>
        <textarea
          value={form.description}
          onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
          className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-brand-50 placeholder-brand-400 focus:outline-none focus:ring-2 focus:ring-accent/40 resize-none"
          rows={5}
          required
        />
      </div>
      <div className="flex justify-end gap-3">
        <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
        <Button type="submit" variant="primary" loading={loading}>Submit Appeal</Button>
      </div>
    </form>
  )
}
