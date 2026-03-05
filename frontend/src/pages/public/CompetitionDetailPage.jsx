import { useParams, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { ArrowLeftIcon, CalendarIcon, MapPinIcon, UsersIcon, TrophyIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Spinner } from '../../components/ui'
import { useFetch } from '../../hooks'
import { competitionsAPI } from '../../api/endpoints'
import { formatDate, SPORT_TYPES } from '../../utils'

export default function CompetitionDetailPage() {
  const { id } = useParams()
  const { data: comp, loading } = useFetch(() => competitionsAPI.get(id), [id])
  const { data: fixtures } = useFetch(() => competitionsAPI.listFixtures({ competition: id, page_size: 100 }), [id])

  if (loading) return <div className="py-20 flex justify-center"><Spinner size="lg" /></div>
  if (!comp) return <div className="py-20 text-center text-brand-300">Competition not found</div>

  const scheduled = (fixtures?.results || []).filter((f) => f.status === 'scheduled')
  const played = (fixtures?.results || []).filter((f) => f.status === 'completed' || f.status === 'played')

  return (
    <>
      <Helmet><title>{comp.name} — KYISA</title></Helmet>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link to="/competitions" className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-light mb-6">
            <ArrowLeftIcon className="h-4 w-4" /> Back to Competitions
          </Link>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Badge variant={comp.status === 'ongoing' ? 'danger' : comp.status === 'completed' ? 'success' : 'accent'} size="sm" className="mb-3">
              {comp.status}
            </Badge>
            <h1 className="text-3xl font-bold text-brand-50 mb-2">{comp.name}</h1>
            <div className="flex flex-wrap items-center gap-4 text-sm text-brand-300">
              <span>{SPORT_TYPES[comp.sport_type] || comp.sport_type}</span>
              {comp.start_date && (
                <span className="flex items-center gap-1"><CalendarIcon className="h-4 w-4" />{formatDate(comp.start_date)} — {formatDate(comp.end_date)}</span>
              )}
            </div>
            {comp.description && <p className="mt-4 text-brand-200 leading-relaxed max-w-3xl">{comp.description}</p>}
          </motion.div>

          {/* Fixtures */}
          <div className="mt-12 space-y-10">
            {scheduled.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold text-brand-100 mb-4">📅 Upcoming Matches</h2>
                <div className="space-y-3">
                  {scheduled.map((f) => <FixtureRow key={f.id} fixture={f} />)}
                </div>
              </div>
            )}
            {played.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold text-brand-100 mb-4">✅ Results</h2>
                <div className="space-y-3">
                  {played.map((f) => <FixtureRow key={f.id} fixture={f} showScore />)}
                </div>
              </div>
            )}
            {(!fixtures?.results || fixtures.results.length === 0) && (
              <div className="text-center py-12 text-brand-300">
                <TrophyIcon className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>No fixtures generated yet</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </>
  )
}

function FixtureRow({ fixture: f, showScore }) {
  return (
    <Card>
      <Card.Body className="flex items-center justify-between gap-4 py-3">
        <div className="flex items-center gap-6 flex-1 min-w-0">
          <span className="text-xs text-brand-400 w-24 shrink-0">{formatDate(f.match_date, true)}</span>
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <span className="font-medium text-brand-50 truncate text-right flex-1">{f.home_team_name || 'TBD'}</span>
            {showScore ? (
              <span className="text-accent font-bold px-2 text-sm">
                {f.home_score ?? '-'} — {f.away_score ?? '-'}
              </span>
            ) : (
              <span className="text-brand-400 text-xs font-bold px-2">VS</span>
            )}
            <span className="font-medium text-brand-50 truncate flex-1">{f.away_team_name || 'TBD'}</span>
          </div>
        </div>
        {f.venue_name && (
          <span className="text-xs text-brand-400 hidden sm:flex items-center gap-1 shrink-0">
            <MapPinIcon className="h-3.5 w-3.5" /> {f.venue_name}
          </span>
        )}
      </Card.Body>
    </Card>
  )
}
