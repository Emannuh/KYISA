import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  UsersIcon, TrophyIcon, ClipboardDocumentListIcon,
  ShieldCheckIcon, BanknotesIcon, ScaleIcon,
} from '@heroicons/react/24/outline'
import { StatCard, Card, Spinner } from '../../components/ui'
import { useFetch } from '../../hooks'
import { useAuth } from '../../contexts/AuthContext'
import { portalAPI, teamsAPI, competitionsAPI } from '../../api/endpoints'

export default function DashboardPage() {
  const { user, isAdmin, isTeamManager, isReferee, isTreasurer } = useAuth()

  return (
    <>
      <Helmet><title>Dashboard — KYISA Portal</title></Helmet>

      <div className="space-y-8">
        {/* Greeting */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-brand-50">
            Welcome back, {user?.first_name || user?.username}
          </h1>
          <p className="text-brand-300 text-sm mt-1">
            Here's what's happening in your {isAdmin ? 'administration' : 'workspace'} today.
          </p>
        </motion.div>

        {/* Admin Dashboard */}
        {isAdmin && <AdminDashboard />}

        {/* Team Manager Dashboard */}
        {isTeamManager && <TeamManagerDashboard />}

        {/* Referee Dashboard */}
        {isReferee && <RefereeDashboard />}

        {/* Treasurer Dashboard */}
        {isTreasurer && <TreasurerDashboard />}

        {/* Quick Links */}
        <QuickLinks />
      </div>
    </>
  )
}

function AdminDashboard() {
  const { data, loading } = useFetch(() => portalAPI.getDashboard(), [])
  const stats = data || {}

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard title="Total Teams" value={stats.total_teams ?? '—'} icon={UsersIcon} gradient="from-teal-500/10 to-teal-600/5" />
      <StatCard title="Competitions" value={stats.total_competitions ?? '—'} icon={TrophyIcon} gradient="from-blue-500/10 to-blue-600/5" />
      <StatCard title="Pending Clearance" value={stats.pending_clearance ?? '—'} icon={ShieldCheckIcon} gradient="from-amber-500/10 to-amber-600/5" />
      <StatCard title="Active Appeals" value={stats.active_appeals ?? '—'} icon={ScaleIcon} gradient="from-red-500/10 to-red-600/5" />
    </div>
  )
}

function TeamManagerDashboard() {
  const { data: teams } = useFetch(() => teamsAPI.list({ mine: true }), [])
  const myTeams = teams?.results || []

  return (
    <div>
      <h2 className="text-lg font-semibold text-brand-100 mb-4">My Teams</h2>
      {myTeams.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {myTeams.map((team) => (
            <Link key={team.id} to={`/portal/teams/${team.id}`}>
              <Card hover>
                <Card.Body>
                  <h3 className="font-semibold text-brand-50">{team.name}</h3>
                  <p className="text-sm text-brand-300 mt-1">{team.county}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-brand-400">
                    <span>{team.players_count ?? 0} players</span>
                    <span>{team.sport_type}</span>
                  </div>
                </Card.Body>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card>
          <Card.Body className="text-center py-8 text-brand-300">
            <UsersIcon className="h-10 w-10 mx-auto mb-2 opacity-30" />
            <p>No teams yet. Register a team to get started.</p>
          </Card.Body>
        </Card>
      )}
    </div>
  )
}

function RefereeDashboard() {
  const { data } = useFetch(() => portalAPI.getDashboard(), [])
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <StatCard title="Upcoming Matches" value={data?.upcoming_appointments ?? '—'} icon={ClipboardDocumentListIcon} gradient="from-teal-500/10 to-teal-600/5" />
      <StatCard title="Matches Officiated" value={data?.matches_officiated ?? '—'} icon={TrophyIcon} gradient="from-blue-500/10 to-blue-600/5" />
      <StatCard title="Avg Rating" value={data?.avg_rating ?? '—'} icon={ShieldCheckIcon} gradient="from-amber-500/10 to-amber-600/5" />
    </div>
  )
}

function TreasurerDashboard() {
  const { data } = useFetch(() => portalAPI.getDashboard(), [])
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <StatCard title="Pending Payments" value={data?.pending_payments ?? '—'} icon={BanknotesIcon} gradient="from-amber-500/10 to-amber-600/5" />
      <StatCard title="Verified Payments" value={data?.verified_payments ?? '—'} icon={ShieldCheckIcon} gradient="from-green-500/10 to-green-600/5" />
      <StatCard title="Total Revenue" value={data?.total_revenue ?? '—'} icon={BanknotesIcon} gradient="from-teal-500/10 to-teal-600/5" />
    </div>
  )
}

function QuickLinks() {
  const { isAdmin, isTeamManager, isReferee } = useAuth()

  const links = [
    isTeamManager && { to: '/portal/teams', icon: UsersIcon, label: 'Manage Teams', color: 'text-teal-400' },
    isAdmin && { to: '/portal/competitions', icon: TrophyIcon, label: 'Competitions', color: 'text-blue-400' },
    isAdmin && { to: '/portal/verification', icon: ShieldCheckIcon, label: 'Verification', color: 'text-amber-400' },
    isReferee && { to: '/portal/referee-dashboard', icon: ClipboardDocumentListIcon, label: 'My Schedule', color: 'text-purple-400' },
    isAdmin && { to: '/portal/admin', icon: ScaleIcon, label: 'Admin Panel', color: 'text-red-400' },
  ].filter(Boolean)

  if (!links.length) return null

  return (
    <div>
      <h2 className="text-lg font-semibold text-brand-100 mb-4">Quick Actions</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {links.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className="flex flex-col items-center gap-2 p-4 rounded-xl bg-surface-elevated border border-border hover:border-accent/30 hover:bg-accent/5 transition-all text-center group"
          >
            <link.icon className={`h-6 w-6 ${link.color} group-hover:scale-110 transition-transform`} />
            <span className="text-sm text-brand-200 font-medium">{link.label}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
