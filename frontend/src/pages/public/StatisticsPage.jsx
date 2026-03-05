import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { ChartBarIcon } from '@heroicons/react/24/outline'
import { Card, Spinner } from '../../components/ui'
import { useFetch } from '../../hooks'
import { publicAPI, matchesAPI } from '../../api/endpoints'

export default function StatisticsPage() {
  const { data: stats, loading } = useFetch(() => matchesAPI.getStatistics({ page_size: 20, ordering: '-goals' }), [])

  const topScorers = stats?.results || []

  return (
    <>
      <Helmet><title>Statistics — KYISA</title></Helmet>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-3xl font-bold text-brand-50 mb-2">Statistics</h1>
            <p className="text-brand-300 mb-8">Top performers across KYISA competitions</p>
          </motion.div>

          {loading ? (
            <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
          ) : topScorers.length > 0 ? (
            <Card>
              <Card.Header>
                <h2 className="font-semibold text-brand-50">🏅 Top Scorers</h2>
              </Card.Header>
              <Card.Body className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-brand-300 text-xs uppercase tracking-wider">
                        <th className="px-4 py-3 text-left">#</th>
                        <th className="px-4 py-3 text-left">Player</th>
                        <th className="px-4 py-3 text-left">Team</th>
                        <th className="px-4 py-3 text-center">Goals</th>
                        <th className="px-4 py-3 text-center">Assists</th>
                        <th className="px-4 py-3 text-center">Matches</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {topScorers.map((p, idx) => (
                        <tr key={p.id} className="hover:bg-brand-800/30 transition-colors">
                          <td className="px-4 py-2.5 text-brand-300">{idx + 1}</td>
                          <td className="px-4 py-2.5 font-medium text-brand-50">{p.player_name}</td>
                          <td className="px-4 py-2.5 text-brand-200">{p.team_name}</td>
                          <td className="px-4 py-2.5 text-center font-bold text-accent">{p.goals ?? 0}</td>
                          <td className="px-4 py-2.5 text-center text-brand-200">{p.assists ?? 0}</td>
                          <td className="px-4 py-2.5 text-center text-brand-200">{p.matches_played ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card.Body>
            </Card>
          ) : (
            <div className="text-center py-20 text-brand-300">
              <ChartBarIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
              <p className="text-lg">No statistics available yet</p>
              <p className="text-sm mt-2">Statistics will appear once matches are played and recorded</p>
            </div>
          )}
        </div>
      </section>
    </>
  )
}
