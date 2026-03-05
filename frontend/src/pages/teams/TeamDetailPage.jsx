import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { ArrowLeftIcon, PlusIcon, PencilIcon, TrashIcon, UserIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Button, Spinner, Modal } from '../../components/ui'
import { useFetch, useMutation } from '../../hooks'
import { useAuth } from '../../contexts/AuthContext'
import { teamsAPI } from '../../api/endpoints'
import { formatDate, SPORT_TYPES } from '../../utils'
import PlayerForm from './PlayerForm'

export default function TeamDetailPage() {
  const { id } = useParams()
  const { isAdmin, isTeamManager } = useAuth()
  const [showPlayerForm, setShowPlayerForm] = useState(false)
  const [editingPlayer, setEditingPlayer] = useState(null)

  const { data: team, loading, refetch } = useFetch(() => teamsAPI.get(id), [id])
  const { data: playersData, refetch: refetchPlayers } = useFetch(() => teamsAPI.listPlayers(id), [id])
  const deletePlayer = useMutation(
    (playerId) => teamsAPI.deletePlayer(id, playerId),
    { successMsg: 'Player removed', onSuccess: refetchPlayers }
  )

  const players = playersData?.results || playersData || []
  const canEdit = isAdmin || isTeamManager

  if (loading) return <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
  if (!team) return <div className="py-16 text-center text-brand-300">Team not found</div>

  return (
    <>
      <Helmet><title>{team.name} — KYISA Portal</title></Helmet>

      <div className="space-y-8">
        {/* Header */}
        <div>
          <Link to="/portal/teams" className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-light mb-4">
            <ArrowLeftIcon className="h-4 w-4" /> Back to Teams
          </Link>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between gap-4">
            <div>
              <Badge variant={team.is_approved ? 'success' : 'warning'} size="sm" className="mb-2">
                {team.is_approved ? 'Approved' : 'Pending Approval'}
              </Badge>
              <h1 className="text-2xl font-bold text-brand-50">{team.name}</h1>
              <p className="text-brand-300 text-sm mt-1">
                {team.county} • {SPORT_TYPES[team.sport_type] || team.sport_type}
                {team.gender && ` • ${team.gender}`}
              </p>
            </div>
            {canEdit && (
              <Link to={`/portal/teams/${id}/edit`}>
                <Button variant="secondary" size="sm">
                  <PencilIcon className="h-4 w-4 mr-1" /> Edit
                </Button>
              </Link>
            )}
          </motion.div>
        </div>

        {/* Team Info */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Manager', value: team.manager_name || team.manager?.username || '—' },
            { label: 'Contact', value: team.contact_phone || '—' },
            { label: 'Sport', value: SPORT_TYPES[team.sport_type] || team.sport_type },
            { label: 'Players', value: `${players.length}` },
          ].map((item) => (
            <Card key={item.label}>
              <Card.Body>
                <p className="text-xs text-brand-400 uppercase tracking-wider">{item.label}</p>
                <p className="text-brand-50 font-medium mt-1">{item.value}</p>
              </Card.Body>
            </Card>
          ))}
        </div>

        {/* Players */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-brand-100">Squad ({players.length})</h2>
            {canEdit && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => { setEditingPlayer(null); setShowPlayerForm(true) }}
              >
                <PlusIcon className="h-4 w-4 mr-1" /> Add Player
              </Button>
            )}
          </div>

          {players.length > 0 ? (
            <Card>
              <Card.Body className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-brand-300 text-xs uppercase tracking-wider">
                        <th className="px-4 py-3 text-left">#</th>
                        <th className="px-4 py-3 text-left">Name</th>
                        <th className="px-4 py-3 text-left">ID Number</th>
                        <th className="px-4 py-3 text-center">DOB</th>
                        <th className="px-4 py-3 text-center">Position</th>
                        <th className="px-4 py-3 text-center">Status</th>
                        {canEdit && <th className="px-4 py-3 text-right">Actions</th>}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {players.map((p, idx) => (
                        <tr key={p.id} className="hover:bg-brand-800/30 transition-colors">
                          <td className="px-4 py-2.5 text-brand-300">{p.jersey_number || idx + 1}</td>
                          <td className="px-4 py-2.5 font-medium text-brand-50">
                            {p.first_name} {p.last_name}
                          </td>
                          <td className="px-4 py-2.5 text-brand-200">{p.id_number || '—'}</td>
                          <td className="px-4 py-2.5 text-center text-brand-200">{p.date_of_birth ? formatDate(p.date_of_birth) : '—'}</td>
                          <td className="px-4 py-2.5 text-center text-brand-200">{p.position || '—'}</td>
                          <td className="px-4 py-2.5 text-center">
                            <Badge
                              variant={p.is_cleared ? 'success' : p.clearance_status === 'pending' ? 'warning' : 'default'}
                              size="xs"
                            >
                              {p.is_cleared ? 'Cleared' : p.clearance_status || 'Unverified'}
                            </Badge>
                          </td>
                          {canEdit && (
                            <td className="px-4 py-2.5 text-right">
                              <div className="flex items-center justify-end gap-1">
                                <button
                                  onClick={() => { setEditingPlayer(p); setShowPlayerForm(true) }}
                                  className="p-1 rounded hover:bg-brand-700 text-brand-300 hover:text-brand-50 transition-colors"
                                >
                                  <PencilIcon className="h-4 w-4" />
                                </button>
                                <button
                                  onClick={() => { if (confirm('Remove this player?')) deletePlayer.mutate(p.id) }}
                                  className="p-1 rounded hover:bg-red-900/30 text-brand-300 hover:text-red-400 transition-colors"
                                >
                                  <TrashIcon className="h-4 w-4" />
                                </button>
                              </div>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card.Body>
            </Card>
          ) : (
            <Card>
              <Card.Body className="text-center py-12 text-brand-300">
                <UserIcon className="h-10 w-10 mx-auto mb-2 opacity-30" />
                <p>No players registered yet</p>
              </Card.Body>
            </Card>
          )}
        </div>
      </div>

      {/* Player Form Modal */}
      <Modal open={showPlayerForm} onClose={() => setShowPlayerForm(false)} title={editingPlayer ? 'Edit Player' : 'Add Player'} size="lg">
        <PlayerForm
          teamId={id}
          player={editingPlayer}
          onSuccess={() => { setShowPlayerForm(false); refetchPlayers() }}
          onCancel={() => setShowPlayerForm(false)}
        />
      </Modal>
    </>
  )
}
