import { motion } from 'framer-motion'
import { Link, useParams } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { TrophyIcon, MapPinIcon, CalendarIcon, UsersIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Spinner } from '../../components/ui'
import { useFetch } from '../../hooks'
import { competitionsAPI } from '../../api/endpoints'
import { formatDate, SPORT_TYPES } from '../../utils'

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.4 } }),
}

export default function CompetitionsPage() {
  const { data, loading } = useFetch(() => competitionsAPI.list({ page_size: 50 }), [])

  const competitions = data?.results || []
  const ongoing = competitions.filter((c) => c.status === 'ongoing')
  const upcoming = competitions.filter((c) => c.status === 'registration' || c.status === 'scheduling')
  const completed = competitions.filter((c) => c.status === 'completed')

  return (
    <>
      <Helmet><title>Competitions — KYISA</title></Helmet>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-3xl font-bold text-brand-50 mb-2">Competitions</h1>
            <p className="text-brand-300">Browse all KYISA tournaments and leagues across 9 disciplines</p>
          </motion.div>

          {loading ? (
            <div className="py-20 flex justify-center"><Spinner size="lg" /></div>
          ) : (
            <div className="mt-10 space-y-12">
              <CompSection title="🔴 Ongoing" items={ongoing} />
              <CompSection title="📅 Upcoming" items={upcoming} />
              <CompSection title="✅ Completed" items={completed} />
              {competitions.length === 0 && (
                <div className="text-center py-20 text-brand-300">
                  <TrophyIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
                  <p className="text-lg">No competitions found</p>
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </>
  )
}

function CompSection({ title, items }) {
  if (!items.length) return null
  return (
    <div>
      <h2 className="text-lg font-semibold text-brand-100 mb-4">{title}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((comp, i) => (
          <motion.div key={comp.id} custom={i} variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}>
            <Link to={`/competitions/${comp.id}`}>
              <Card hover className="h-full">
                <Card.Body>
                  <div className="flex items-start justify-between mb-3">
                    <Badge variant={comp.status === 'ongoing' ? 'danger' : comp.status === 'completed' ? 'success' : 'accent'} size="xs">
                      {comp.status}
                    </Badge>
                    <span className="text-xs text-brand-400">{formatDate(comp.start_date)}</span>
                  </div>
                  <h3 className="font-semibold text-brand-50 mb-1 line-clamp-2">{comp.name}</h3>
                  <p className="text-sm text-brand-300">{SPORT_TYPES[comp.sport_type] || comp.sport_type}</p>
                  <div className="flex items-center gap-4 mt-3 text-xs text-brand-400">
                    {comp.venue_name && (
                      <span className="flex items-center gap-1"><MapPinIcon className="h-3.5 w-3.5" />{comp.venue_name}</span>
                    )}
                    {comp.teams_count != null && (
                      <span className="flex items-center gap-1"><UsersIcon className="h-3.5 w-3.5" />{comp.teams_count} teams</span>
                    )}
                  </div>
                </Card.Body>
              </Card>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
