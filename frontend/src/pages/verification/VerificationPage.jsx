import { useState } from 'react'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { ShieldCheckIcon, CheckCircleIcon, XCircleIcon, ClockIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Button, Spinner, Input, Select, Modal } from '../../components/ui'
import { useFetch, useDebounce, useMutation } from '../../hooks'
import { portalAPI, teamsAPI } from '../../api/endpoints'
import { formatDate } from '../../utils'

export default function VerificationPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('pending')
  const debouncedSearch = useDebounce(search, 400)
  const [selectedPlayer, setSelectedPlayer] = useState(null)

  const { data, loading, refetch } = useFetch(
    () => portalAPI.getClearanceRequests({
      search: debouncedSearch || undefined,
      status: statusFilter || undefined,
      page_size: 50,
    }),
    [debouncedSearch, statusFilter]
  )

  const requests = data?.results || data || []

  const approveMutation = useMutation(
    (id) => portalAPI.approveClearance(id),
    { successMsg: 'Player cleared', onSuccess: () => { setSelectedPlayer(null); refetch() } }
  )
  const rejectMutation = useMutation(
    (args) => portalAPI.rejectClearance(args.id, { reason: args.reason }),
    { successMsg: 'Clearance rejected', onSuccess: () => { setSelectedPlayer(null); refetch() } }
  )

  return (
    <>
      <Helmet><title>Verification — KYISA Portal</title></Helmet>

      <div className="space-y-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-brand-50">Player Verification & Clearance</h1>
          <p className="text-sm text-brand-300">Review and approve player verification requests</p>
        </motion.div>

        <div className="flex flex-col sm:flex-row gap-3 max-w-lg">
          <Input placeholder="Search player..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </Select>
        </div>

        {loading ? (
          <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
        ) : requests.length > 0 ? (
          <Card>
            <Card.Body className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-brand-300 text-xs uppercase tracking-wider">
                      <th className="px-4 py-3 text-left">Player</th>
                      <th className="px-4 py-3 text-left">Team</th>
                      <th className="px-4 py-3 text-left">ID Number</th>
                      <th className="px-4 py-3 text-center">Submitted</th>
                      <th className="px-4 py-3 text-center">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {requests.map((req) => (
                      <tr key={req.id} className="hover:bg-brand-800/30 transition-colors">
                        <td className="px-4 py-2.5 font-medium text-brand-50">{req.player_name || `${req.first_name} ${req.last_name}`}</td>
                        <td className="px-4 py-2.5 text-brand-200">{req.team_name || '—'}</td>
                        <td className="px-4 py-2.5 text-brand-200">{req.id_number || '—'}</td>
                        <td className="px-4 py-2.5 text-center text-brand-300 text-xs">{formatDate(req.created_at || req.submitted_at)}</td>
                        <td className="px-4 py-2.5 text-center">
                          <Badge
                            variant={req.status === 'approved' ? 'success' : req.status === 'rejected' ? 'danger' : 'warning'}
                            size="xs"
                          >
                            {req.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          {req.status === 'pending' && (
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => approveMutation.mutate(req.id)}
                                className="p-1 rounded hover:bg-green-900/30 text-green-400 transition-colors"
                                title="Approve"
                              >
                                <CheckCircleIcon className="h-5 w-5" />
                              </button>
                              <button
                                onClick={() => setSelectedPlayer(req)}
                                className="p-1 rounded hover:bg-red-900/30 text-red-400 transition-colors"
                                title="Reject"
                              >
                                <XCircleIcon className="h-5 w-5" />
                              </button>
                            </div>
                          )}
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
            <ShieldCheckIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
            <p>{statusFilter ? `No ${statusFilter} requests` : 'No verification requests'}</p>
          </div>
        )}
      </div>

      {/* Reject Modal */}
      <RejectModal
        open={!!selectedPlayer}
        player={selectedPlayer}
        onClose={() => setSelectedPlayer(null)}
        onReject={(reason) => {
          if (selectedPlayer) rejectMutation.mutate({ id: selectedPlayer.id, reason })
        }}
      />
    </>
  )
}

function RejectModal({ open, player, onClose, onReject }) {
  const [reason, setReason] = useState('')
  return (
    <Modal open={open} onClose={onClose} title="Reject Clearance" size="sm">
      <p className="text-brand-200 text-sm mb-3">
        Rejecting clearance for <strong className="text-brand-50">{player?.player_name || 'this player'}</strong>. Provide a reason:
      </p>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-brand-50 placeholder-brand-400 focus:outline-none focus:ring-2 focus:ring-accent/40 resize-none"
        rows={3}
        placeholder="Reason for rejection..."
      />
      <div className="flex justify-end gap-3 mt-4">
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button variant="danger" onClick={() => onReject(reason)} disabled={!reason.trim()}>
          Reject
        </Button>
      </div>
    </Modal>
  )
}
