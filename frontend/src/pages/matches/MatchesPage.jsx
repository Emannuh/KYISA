import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { CalendarIcon, ClipboardDocumentListIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Spinner } from '../../components/ui'
import { useFetch } from '../../hooks'
import { competitionsAPI, matchesAPI } from '../../api/endpoints'
import { formatDate } from '../../utils'

export default function MatchesPage() {
  const { data, loading } = useFetch(
    () => competitionsAPI.listFixtures({ page_size: 50, ordering: '-match_date' }),
    []
  )

  const fixtures = data?.results || []
  const scheduled = fixtures.filter((f) => f.status === 'scheduled')
  const completed = fixtures.filter((f) => f.status === 'completed' || f.status === 'played')

  return (
    <>
      <Helmet><title>Matches — KYISA Portal</title></Helmet>

      <div className="space-y-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-brand-50">Matches & Fixtures</h1>
          <p className="text-sm text-brand-300">View and manage match fixtures, submit results</p>
        </motion.div>

        {loading ? (
          <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
        ) : (
          <>
            {/* Upcoming */}
            {scheduled.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold text-brand-100 mb-4">📅 Upcoming ({scheduled.length})</h2>
                <div className="space-y-3">
                  {scheduled.map((f) => <MatchRow key={f.id} fixture={f} />)}
                </div>
              </div>
            )}

            {/* Completed */}
            {completed.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold text-brand-100 mb-4">✅ Completed ({completed.length})</h2>
                <div className="space-y-3">
                  {completed.map((f) => <MatchRow key={f.id} fixture={f} showScore />)}
                </div>
              </div>
            )}

            {fixtures.length === 0 && (
              <div className="text-center py-16 text-brand-300">
                <ClipboardDocumentListIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
                <p>No fixtures available</p>
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}

function MatchRow({ fixture: f, showScore }) {
  return (
    <Card>
      <Card.Body className="flex items-center justify-between gap-4 py-3">
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <span className="text-xs text-brand-400 w-24 shrink-0">{formatDate(f.match_date, true)}</span>
          <Badge variant="accent" size="xs" className="hidden sm:block shrink-0">{f.competition_name || '—'}</Badge>
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <span className="font-medium text-brand-50 truncate text-right flex-1">{f.home_team_name || 'TBD'}</span>
            {showScore ? (
              <span className="text-accent font-bold text-sm px-2">{f.home_score ?? '-'} — {f.away_score ?? '-'}</span>
            ) : (
              <span className="text-brand-400 text-xs font-bold px-2">VS</span>
            )}
            <span className="font-medium text-brand-50 truncate flex-1">{f.away_team_name || 'TBD'}</span>
          </div>
        </div>
      </Card.Body>
    </Card>
  )
}
