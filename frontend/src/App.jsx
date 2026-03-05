import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { PublicLayout, PortalLayout } from './components/layout'
import { Spinner } from './components/ui'

// Lazy-loaded pages for code splitting
const HomePage = lazy(() => import('./pages/public/HomePage'))
const CompetitionsPage = lazy(() => import('./pages/public/CompetitionsPage'))
const CompetitionDetailPage = lazy(() => import('./pages/public/CompetitionDetailPage'))
const ResultsPage = lazy(() => import('./pages/public/ResultsPage'))
const StandingsPage = lazy(() => import('./pages/public/StandingsPage'))
const StatisticsPage = lazy(() => import('./pages/public/StatisticsPage'))
const ContactPage = lazy(() => import('./pages/public/ContactPage'))
const AboutPage = lazy(() => import('./pages/public/AboutPage'))

const LoginPage = lazy(() => import('./pages/auth/LoginPage'))
const RegisterTeamPage = lazy(() => import('./pages/auth/RegisterTeamPage'))
const RegisterRefereePage = lazy(() => import('./pages/auth/RegisterRefereePage'))

const DashboardPage = lazy(() => import('./pages/dashboard/DashboardPage'))
const TeamsListPage = lazy(() => import('./pages/teams/TeamsListPage'))
const TeamDetailPage = lazy(() => import('./pages/teams/TeamDetailPage'))
const CompetitionsManagePage = lazy(() => import('./pages/competitions/CompetitionsManagePage'))
const MatchesPage = lazy(() => import('./pages/matches/MatchesPage'))
const RefereesPage = lazy(() => import('./pages/referees/RefereesPage'))
const VerificationPage = lazy(() => import('./pages/verification/VerificationPage'))
const TreasurerPage = lazy(() => import('./pages/treasurer/TreasurerPage'))
const AppealsPage = lazy(() => import('./pages/appeals/AppealsPage'))
const AdminDashboardPage = lazy(() => import('./pages/admin/AdminDashboardPage'))
const UsersManagePage = lazy(() => import('./pages/admin/UsersManagePage'))
const ActivityLogPage = lazy(() => import('./pages/admin/ActivityLogPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

/* ── Role gate component ─────────────────────────────────────────────── */
function RequireRole({ roles, children }) {
  const { user, hasRole } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.some((r) => hasRole(r))) return <Navigate to="/portal" replace />
  return children
}

export default function App() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-brand-900"><Spinner size="lg" /></div>}>
      <Routes>
      {/* ── Public site ──────────────────────────────────────────────── */}
      <Route element={<PublicLayout />}>
        <Route index element={<HomePage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="competitions" element={<CompetitionsPage />} />
        <Route path="competitions/:id" element={<CompetitionDetailPage />} />
        <Route path="results" element={<ResultsPage />} />
        <Route path="statistics" element={<StatisticsPage />} />
        <Route path="standings" element={<StandingsPage />} />
        <Route path="standings/:id" element={<StandingsPage />} />
        <Route path="contact" element={<ContactPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register/team" element={<RegisterTeamPage />} />
        <Route path="register/referee" element={<RegisterRefereePage />} />
      </Route>

      {/* ── Portal (authenticated) ───────────────────────────────────── */}
      <Route path="portal" element={<PortalLayout />}>
        <Route index element={<DashboardPage />} />

        {/* Teams */}
        <Route path="teams" element={<TeamsListPage />} />
        <Route path="teams/:id" element={<TeamDetailPage />} />

        {/* Competitions */}
        <Route path="competitions" element={<CompetitionsManagePage />} />

        {/* Matches */}
        <Route path="matches" element={<MatchesPage />} />

        {/* Referees */}
        <Route path="referees" element={<RefereesPage />} />
        <Route path="referee-dashboard" element={<RefereesPage />} />

        {/* Verification */}
        <Route
          path="verification"
          element={
            <RequireRole roles={['admin', 'fkf_admin']}>
              <VerificationPage />
            </RequireRole>
          }
        />

        {/* Treasurer */}
        <Route
          path="treasurer"
          element={
            <RequireRole roles={['admin', 'treasurer']}>
              <TreasurerPage />
            </RequireRole>
          }
        />

        {/* Appeals */}
        <Route path="appeals" element={<AppealsPage />} />

        {/* Admin */}
        <Route
          path="admin"
          element={
            <RequireRole roles={['admin']}>
              <AdminDashboardPage />
            </RequireRole>
          }
        />
        <Route
          path="admin/users"
          element={
            <RequireRole roles={['admin']}>
              <UsersManagePage />
            </RequireRole>
          }
        />
        <Route
          path="admin/activity"
          element={
            <RequireRole roles={['admin']}>
              <ActivityLogPage />
            </RequireRole>
          }
        />
      </Route>

      {/* ── Catch-all ────────────────────────────────────────────────── */}
      <Route path="*" element={<PublicLayout />}>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
    </Suspense>
  )
}
