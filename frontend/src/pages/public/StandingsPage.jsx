import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { TableCellsIcon, ArrowLeftIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Spinner, Select } from '../../components/ui'
import { useFetch } from '../../hooks'
import { competitionsAPI } from '../../api/endpoints'

export default function StandingsPage() {
  const { id: paramId } = useParams()
  const [competitionId, setCompetitionId] = useState(paramId || '')
  const { data: competitions } = useFetch(() => competitionsAPI.list({ page_size: 100, status: 'ongoing' }), [])

  const activeId = competitionId || paramId || ''
  const { data: pools, loading } = useFetch(
    () => activeId ? competitionsAPI.listPools({ competition: activeId }) : Promise.resolve(null),
    [activeId]
  )

  const poolList = pools?.results || []

  return (
    <>
      <Helmet><title>Standings — KYISA</title></Helmet>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-3xl font-bold text-brand-50 mb-2">Standings</h1>
            <p className="text-brand-300 mb-8">Pool tables and league standings</p>
          </motion.div>

          <div className="mb-8 max-w-xs">
            <Select label="Competition" value={activeId} onChange={(e) => setCompetitionId(e.target.value)}>
              <option value="">Select a competition</option>
              {(competitions?.results || []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </Select>
          </div>

          {!activeId ? (
            <div className="text-center py-20 text-brand-300">
              <TableCellsIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
              <p>Select a competition to view standings</p>
            </div>
          ) : loading ? (
            <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
          ) : poolList.length > 0 ? (
            <div className="space-y-8">
              {poolList.map((pool) => (
                <motion.div key={pool.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                  <Card>
                    <Card.Header>
                      <h3 className="font-semibold text-brand-50">{pool.name}</h3>
                    </Card.Header>
                    <Card.Body className="p-0">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border text-brand-300 text-xs uppercase tracking-wider">
                              <th className="px-4 py-3 text-left">#</th>
                              <th className="px-4 py-3 text-left">Team</th>
                              <th className="px-4 py-3 text-center">P</th>
                              <th className="px-4 py-3 text-center">W</th>
                              <th className="px-4 py-3 text-center">D</th>
                              <th className="px-4 py-3 text-center">L</th>
                              <th className="px-4 py-3 text-center">GF</th>
                              <th className="px-4 py-3 text-center">GA</th>
                              <th className="px-4 py-3 text-center">GD</th>
                              <th className="px-4 py-3 text-center font-bold">Pts</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {(pool.teams || [])
                              .sort((a, b) => (b.points ?? 0) - (a.points ?? 0))
                              .map((team, idx) => (
                                <tr key={team.id} className="hover:bg-brand-800/30 transition-colors">
                                  <td className="px-4 py-2.5 text-brand-300">{idx + 1}</td>
                                  <td className="px-4 py-2.5 font-medium text-brand-50">{team.team_name || team.name}</td>
                                  <td className="px-4 py-2.5 text-center text-brand-200">{team.played ?? 0}</td>
                                  <td className="px-4 py-2.5 text-center text-brand-200">{team.won ?? 0}</td>
                                  <td className="px-4 py-2.5 text-center text-brand-200">{team.drawn ?? 0}</td>
                                  <td className="px-4 py-2.5 text-center text-brand-200">{team.lost ?? 0}</td>
                                  <td className="px-4 py-2.5 text-center text-brand-200">{team.goals_for ?? 0}</td>
                                  <td className="px-4 py-2.5 text-center text-brand-200">{team.goals_against ?? 0}</td>
                                  <td className="px-4 py-2.5 text-center text-brand-200">
                                    {(team.goals_for ?? 0) - (team.goals_against ?? 0)}
                                  </td>
                                  <td className="px-4 py-2.5 text-center font-bold text-accent">{team.points ?? 0}</td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </Card.Body>
                  </Card>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="text-center py-20 text-brand-300">
              <TableCellsIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
              <p>No pool standings available for this competition</p>
            </div>
          )}
        </div>
      </section>
    </>
  )
}
