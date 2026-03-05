import { NavLink, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  HomeIcon, UserGroupIcon, TrophyIcon, CalendarIcon, ShieldCheckIcon,
  ClipboardDocumentListIcon, BanknotesIcon, Cog6ToothIcon,
  ChevronLeftIcon, ArrowRightStartOnRectangleIcon, UserIcon,
  ScaleIcon, FlagIcon, ChartBarIcon, DocumentCheckIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '../../contexts/AuthContext'

export default function Sidebar() {
  const { user, logout, hasRole } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()

  const navSections = [
    {
      label: 'Main',
      items: [
        { to: '/portal', icon: HomeIcon, label: 'Dashboard', end: true },
      ],
    },
    hasRole('admin', 'competition_manager', 'team_manager') && {
      label: 'Management',
      items: [
        hasRole('admin', 'competition_manager', 'team_manager') && { to: '/portal/teams', icon: UserGroupIcon, label: 'Teams' },
        hasRole('admin', 'competition_manager') && { to: '/portal/competitions', icon: TrophyIcon, label: 'Competitions' },
        hasRole('admin', 'competition_manager') && { to: '/portal/fixtures', icon: CalendarIcon, label: 'Fixtures' },
        hasRole('admin', 'competition_manager', 'team_manager', 'referee') && { to: '/portal/matches', icon: ClipboardDocumentListIcon, label: 'Matches' },
      ].filter(Boolean),
    },
    hasRole('admin', 'competition_manager', 'referee_manager', 'referee') && {
      label: 'Referees',
      items: [
        hasRole('admin', 'referee_manager') && { to: '/portal/referees', icon: FlagIcon, label: 'Referees' },
        hasRole('referee') && { to: '/portal/referee-dashboard', icon: HomeIcon, label: 'My Dashboard' },
      ].filter(Boolean),
    },
    hasRole('admin', 'competition_manager') && {
      label: 'Verification',
      items: [
        { to: '/portal/verification', icon: ShieldCheckIcon, label: 'Player Clearance' },
        { to: '/portal/verification/players', icon: DocumentCheckIcon, label: 'Doc Verification' },
      ],
    },
    hasRole('treasurer') && {
      label: 'Finance',
      items: [
        { to: '/portal/treasurer', icon: BanknotesIcon, label: 'Treasurer' },
      ],
    },
    hasRole('admin', 'jury_chair') && {
      label: 'Appeals',
      items: [
        { to: '/portal/appeals', icon: ScaleIcon, label: 'Appeals' },
      ],
    },
    hasRole('admin') && {
      label: 'Admin',
      items: [
        { to: '/portal/admin', icon: Cog6ToothIcon, label: 'Admin Dashboard' },
        { to: '/portal/admin/users', icon: UserIcon, label: 'Users' },
        { to: '/portal/admin/activity', icon: ChartBarIcon, label: 'Activity Logs' },
      ],
    },
  ].filter(Boolean)

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 260 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-y-0 left-0 z-40 bg-brand-800 border-r border-border flex flex-col"
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-4 h-16 border-b border-border shrink-0">
        {!collapsed && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center text-brand-900 font-bold text-xs">K</div>
            <span className="text-sm font-bold text-brand-50">KYISA CMS</span>
          </motion.div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg hover:bg-brand-700 text-brand-300 hover:text-brand-50 transition-colors"
        >
          <ChevronLeftIcon className={`h-4 w-4 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
        {navSections.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider text-brand-400">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map(({ to, icon: Icon, label, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 group ${
                      isActive
                        ? 'bg-accent/10 text-accent'
                        : 'text-brand-200 hover:text-brand-50 hover:bg-brand-700'
                    }`
                  }
                  title={collapsed ? label : undefined}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {!collapsed && <span>{label}</span>}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="border-t border-border px-3 py-3 shrink-0">
        {!collapsed ? (
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-brand-600 flex items-center justify-center shrink-0">
              <span className="text-xs font-bold text-accent">
                {user?.first_name?.[0]}{user?.last_name?.[0]}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-brand-50 truncate">{user?.first_name} {user?.last_name}</p>
              <p className="text-[10px] text-brand-300 capitalize">{user?.role?.replace('_', ' ')}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg hover:bg-brand-700 text-brand-300 hover:text-danger transition-colors"
              title="Logout"
            >
              <ArrowRightStartOnRectangleIcon className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={handleLogout}
            className="w-full p-2 rounded-lg hover:bg-brand-700 text-brand-300 hover:text-danger transition-colors flex justify-center"
            title="Logout"
          >
            <ArrowRightStartOnRectangleIcon className="h-5 w-5" />
          </button>
        )}
      </div>
    </motion.aside>
  )
}
