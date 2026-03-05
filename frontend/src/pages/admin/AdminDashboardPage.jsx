import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  UsersIcon, TrophyIcon, ShieldCheckIcon, BanknotesIcon,
  ScaleIcon, ClipboardDocumentListIcon, Cog6ToothIcon, ChartBarIcon,
} from '@heroicons/react/24/outline'
import { StatCard, Card, Spinner } from '../../components/ui'
import { useFetch } from '../../hooks'
import { portalAPI } from '../../api/endpoints'

export default function AdminDashboardPage() {
  const { data, loading } = useFetch(() => portalAPI.getAdminDashboard(), [])
  const stats = data || {}

  const cards = [
    { to: '/portal/admin/users', icon: UsersIcon, label: 'User Management', count: stats.total_users, color: 'text-teal-400' },
    { to: '/portal/teams', icon: UsersIcon, label: 'Teams', count: stats.total_teams, color: 'text-blue-400' },
    { to: '/portal/competitions', icon: TrophyIcon, label: 'Competitions', count: stats.total_competitions, color: 'text-purple-400' },
    { to: '/portal/verification', icon: ShieldCheckIcon, label: 'Verification Queue', count: stats.pending_clearance, color: 'text-amber-400' },
    { to: '/portal/treasurer', icon: BanknotesIcon, label: 'Payments', count: stats.pending_payments, color: 'text-green-400' },
    { to: '/portal/appeals', icon: ScaleIcon, label: 'Appeals', count: stats.active_appeals, color: 'text-red-400' },
    { to: '/portal/admin/activity', icon: ClipboardDocumentListIcon, label: 'Activity Logs', color: 'text-gray-400' },
    { to: '/portal/referees', icon: Cog6ToothIcon, label: 'Referees', count: stats.total_referees, color: 'text-indigo-400' },
  ]

  return (
    <>
      <Helmet><title>Admin Dashboard — KYISA Portal</title></Helmet>

      <div className="space-y-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-brand-50">Administration</h1>
          <p className="text-sm text-brand-300">System overview and management tools</p>
        </motion.div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard title="Users" value={stats.total_users ?? '—'} icon={UsersIcon} gradient="from-teal-500/10 to-teal-600/5" />
          <StatCard title="Teams" value={stats.total_teams ?? '—'} icon={UsersIcon} gradient="from-blue-500/10 to-blue-600/5" />
          <StatCard title="Competitions" value={stats.total_competitions ?? '—'} icon={TrophyIcon} gradient="from-purple-500/10 to-purple-600/5" />
          <StatCard title="Pending Actions" value={(stats.pending_clearance ?? 0) + (stats.pending_payments ?? 0)} icon={ShieldCheckIcon} gradient="from-amber-500/10 to-amber-600/5" />
        </div>

        {/* Quick Access Grid */}
        <div>
          <h2 className="text-lg font-semibold text-brand-100 mb-4">Quick Access</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {cards.map((card) => (
              <Link key={card.to} to={card.to}>
                <Card hover className="h-full">
                  <Card.Body className="text-center py-6">
                    <card.icon className={`h-8 w-8 mx-auto mb-2 ${card.color}`} />
                    <h3 className="font-medium text-brand-50 text-sm">{card.label}</h3>
                    {card.count != null && (
                      <p className="text-2xl font-bold text-accent mt-1">{card.count}</p>
                    )}
                  </Card.Body>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
