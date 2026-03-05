import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { UserGroupIcon, CalendarIcon, StarIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Spinner, StatCard } from '../../components/ui'
import { useFetch } from '../../hooks'
import { useAuth } from '../../contexts/AuthContext'
import { refereesAPI } from '../../api/endpoints'
import { formatDate } from '../../utils'

export default function RefereesPage() {
  const { isAdmin, isReferee } = useAuth()
  const { data: refs, loading } = useFetch(
    () => refereesAPI.listProfiles({ page_size: 50 }),
    []
  )
  const { data: appointments } = useFetch(
    () => refereesAPI.listAppointments({ page_size: 20, ordering: 'match_date' }),
    []
  )

  const referees = refs?.results || []
  const upcomingAppts = (appointments?.results || []).filter(
    (a) => a.status === 'confirmed' || a.status === 'pending'
  )

  return (
    <>
      <Helmet><title>Referees — KYISA Portal</title></Helmet>

      <div className="space-y-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-brand-50">Referees</h1>
          <p className="text-sm text-brand-300">
            {isAdmin ? 'Manage referees, appointments & reviews' : 'View your profile, schedule & performance'}
          </p>
        </motion.div>

        {/* Upcoming Appointments */}
        {upcomingAppts.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-brand-100 mb-4">📋 Upcoming Appointments</h2>
            <div className="space-y-3">
              {upcomingAppts.map((appt) => (
                <Card key={appt.id}>
                  <Card.Body className="flex items-center justify-between gap-4 py-3">
                    <div className="flex items-center gap-4 flex-1">
                      <span className="text-xs text-brand-400 w-24 shrink-0">{formatDate(appt.match_date)}</span>
                      <span className="font-medium text-brand-50">{appt.match_name || appt.fixture_name || 'Match'}</span>
                    </div>
                    <Badge variant={appt.status === 'confirmed' ? 'success' : 'warning'} size="xs">
                      {appt.status}
                    </Badge>
                  </Card.Body>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Referees List (admin) */}
        {isAdmin && (
          <div>
            <h2 className="text-lg font-semibold text-brand-100 mb-4">All Referees ({referees.length})</h2>
            {loading ? (
              <div className="py-8 flex justify-center"><Spinner /></div>
            ) : referees.length > 0 ? (
              <Card>
                <Card.Body className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-brand-300 text-xs uppercase tracking-wider">
                          <th className="px-4 py-3 text-left">Name</th>
                          <th className="px-4 py-3 text-left">License</th>
                          <th className="px-4 py-3 text-center">Rating</th>
                          <th className="px-4 py-3 text-center">Matches</th>
                          <th className="px-4 py-3 text-center">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {referees.map((ref) => (
                          <tr key={ref.id} className="hover:bg-brand-800/30 transition-colors">
                            <td className="px-4 py-2.5 font-medium text-brand-50">
                              {ref.user?.first_name} {ref.user?.last_name || ref.name}
                            </td>
                            <td className="px-4 py-2.5 text-brand-200">{ref.badge_level || ref.license_number || '—'}</td>
                            <td className="px-4 py-2.5 text-center">
                              <span className="flex items-center justify-center gap-1 text-amber-400">
                                <StarIcon className="h-3.5 w-3.5" /> {ref.average_rating ? ref.average_rating.toFixed(1) : '—'}
                              </span>
                            </td>
                            <td className="px-4 py-2.5 text-center text-brand-200">{ref.matches_officiated ?? 0}</td>
                            <td className="px-4 py-2.5 text-center">
                              <Badge variant={ref.is_active ? 'success' : 'default'} size="xs">
                                {ref.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card.Body>
              </Card>
            ) : (
              <div className="text-center py-12 text-brand-300">
                <UserGroupIcon className="h-10 w-10 mx-auto mb-2 opacity-30" />
                <p>No referees registered</p>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
