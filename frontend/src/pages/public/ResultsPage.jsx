import { useState } from 'react'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { CalendarIcon, FunnelIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Spinner, Select } from '../../components/ui'
import { useFetch } from '../../hooks'
import { competitionsAPI } from '../../api/endpoints'
import { formatDate } from '../../utils'

export default function ResultsPage() {
  const [competitionId, setCompetitionId] = useState('')
  const { data: competitions } = useFetch(() => competitionsAPI.list({ page_size: 100 }), [])
  const { data: fixtures, loading } = useFetch(
    () => competitionsAPI.listFixtures({
      page_size: 50,
      status: 'completed',
      ordering: '-match_date',
      ...(competitionId ? { competition: competitionId } : {}),
    }),
    [competitionId]
  )

  const results = fixtures?.results || []

  return (
    <>
      <Helmet><title>Results — KYISA</title></Helmet>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-3xl font-bold text-brand-50 mb-2">Match Results</h1>
            <p className="text-brand-300 mb-8">Latest scores from all KYISA competitions</p>
          </motion.div>

          {/* Filter */}
          <div className="mb-8 max-w-xs">
            <Select
              label="Filter by Competition"
              value={competitionId}
              onChange={(e) => setCompetitionId(e.target.value)}
            >
              <option value="">All Competitions</option>
              {(competitions?.results || []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </Select>
          </div>

          {loading ? (
            <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
          ) : results.length > 0 ? (
            <div className="space-y-3">
              {results.map((f, i) => (
                <motion.div
                  key={f.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                >
                  <Card>
                    <Card.Body className="flex items-center justify-between gap-4 py-3">
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        <span className="text-xs text-brand-400 w-24 shrink-0">{formatDate(f.match_date)}</span>
                        <Badge variant="accent" size="xs" className="hidden sm:block shrink-0">
                          {f.competition_name || 'Match'}
                        </Badge>
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <span className="font-medium text-brand-50 truncate text-right flex-1">
                            {f.home_team_name || 'TBD'}
                          </span>
                          <span className="text-accent font-bold text-sm px-2 shrink-0">
                            {f.home_score ?? '-'} — {f.away_score ?? '-'}
                          </span>
                          <span className="font-medium text-brand-50 truncate flex-1">
                            {f.away_team_name || 'TBD'}
                          </span>
                        </div>
                      </div>
                    </Card.Body>
                  </Card>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="text-center py-20 text-brand-300">
              <CalendarIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
              <p className="text-lg">No results available yet</p>
            </div>
          )}
        </div>
      </section>
    </>
  )
}
