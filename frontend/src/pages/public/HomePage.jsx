import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { TrophyIcon, CalendarIcon, ChartBarIcon, ArrowRightIcon } from '@heroicons/react/24/outline'
import { Card, Badge } from '../../components/ui'
import { useFetch } from '../../hooks'
import { competitionsAPI, matchesAPI } from '../../api/endpoints'
import { formatDate, SPORT_TYPES } from '../../utils'

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  show: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.1, duration: 0.5 } }),
}

export default function HomePage() {
  const { data: competitions } = useFetch(() => competitionsAPI.list({ page_size: 6, status: 'ongoing' }), [])
  const { data: fixtures } = useFetch(() => competitionsAPI.listFixtures({ page_size: 6, status: 'scheduled', ordering: 'match_date' }), [])

  return (
    <>
      <Helmet><title>KYISA — Kenya Youth Intercounty Sports Association</title></Helmet>

      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <section className="relative min-h-[85vh] flex items-center overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-brand-900 via-brand-800 to-brand-900" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(32,178,170,0.12),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(32,178,170,0.08),transparent_60%)]" />

        {/* Floating orbs */}
        <motion.div
          animate={{ y: [-20, 20, -20], x: [-10, 10, -10] }}
          transition={{ duration: 8, repeat: Infinity }}
          className="absolute top-1/4 right-1/4 w-80 h-80 bg-accent/5 rounded-full blur-3xl"
        />
        <motion.div
          animate={{ y: [20, -20, 20] }}
          transition={{ duration: 10, repeat: Infinity }}
          className="absolute bottom-1/4 left-1/4 w-60 h-60 bg-accent/3 rounded-full blur-3xl"
        />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="max-w-3xl"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 mb-6"
            >
              <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
              <span className="text-accent text-sm font-medium">11th Edition — 2026 Season</span>
            </motion.div>

            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight">
              <span className="text-brand-50">Kenya Youth</span>
              <br />
              <span className="text-gradient">Intercounty Sports</span>
              <br />
              <span className="text-brand-50">Association</span>
            </h1>

            <p className="mt-6 text-lg text-brand-200 max-w-2xl leading-relaxed">
              Uniting counties through competitive youth sports across 9 disciplines.
              Football, Volleyball, Basketball, Handball & Netball — where future champions rise.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                to="/competitions"
                className="inline-flex items-center gap-2 px-6 py-3 bg-accent text-brand-900 font-semibold rounded-xl hover:bg-accent-light transition-all duration-200 hover:shadow-lg hover:shadow-accent/20"
              >
                View Competitions <ArrowRightIcon className="h-4 w-4" />
              </Link>
              <Link
                to="/register/team"
                className="inline-flex items-center gap-2 px-6 py-3 bg-brand-700 text-brand-50 font-semibold rounded-xl border border-border hover:bg-brand-600 transition-all duration-200"
              >
                Register Your Team
              </Link>
            </div>
          </motion.div>

          {/* Stats row */}
          <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { icon: '⚽', value: '9', label: 'Sports' },
              { icon: '🏛️', value: '20+', label: 'Counties' },
              { icon: '👥', value: '200+', label: 'Teams' },
              { icon: '🏆', value: '2026', label: 'Season' },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                custom={i}
                variants={fadeUp}
                initial="hidden"
                animate="show"
                className="text-center p-4 rounded-xl bg-brand-800/50 border border-border"
              >
                <span className="text-2xl">{stat.icon}</span>
                <p className="text-2xl font-bold text-brand-50 mt-1">{stat.value}</p>
                <p className="text-xs text-brand-300">{stat.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Upcoming Fixtures ──────────────────────────────────────────────── */}
      <section className="py-20 bg-brand-800/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-brand-50">Upcoming Fixtures</h2>
              <p className="text-brand-300 text-sm mt-1">Next matches across all competitions</p>
            </div>
            <Link to="/results" className="text-accent text-sm font-medium hover:text-accent-light flex items-center gap-1">
              View All <ArrowRightIcon className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(fixtures?.results || []).map((fixture, i) => (
              <motion.div
                key={fixture.id}
                custom={i}
                variants={fadeUp}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true }}
              >
                <Card hover className="h-full">
                  <Card.Body>
                    <div className="flex items-center justify-between mb-3">
                      <Badge variant="accent" size="xs">
                        {fixture.competition_name || 'Match'}
                      </Badge>
                      <span className="text-xs text-brand-300">
                        {formatDate(fixture.match_date)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-center flex-1">
                        <p className="font-semibold text-brand-50 text-sm truncate">
                          {fixture.home_team_name || 'TBD'}
                        </p>
                      </div>
                      <span className="text-xs text-brand-400 font-bold px-2">VS</span>
                      <div className="text-center flex-1">
                        <p className="font-semibold text-brand-50 text-sm truncate">
                          {fixture.away_team_name || 'TBD'}
                        </p>
                      </div>
                    </div>
                    {fixture.venue_name && (
                      <p className="mt-2 text-xs text-brand-400 text-center">📍 {fixture.venue_name}</p>
                    )}
                  </Card.Body>
                </Card>
              </motion.div>
            ))}
            {(!fixtures?.results || fixtures.results.length === 0) && (
              <div className="col-span-full text-center py-12 text-brand-300">
                <CalendarIcon className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>No upcoming fixtures scheduled yet</p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Sports Section ─────────────────────────────────────────────────── */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-bold text-brand-50">9 Sporting Disciplines</h2>
            <p className="text-brand-300 text-sm mt-2">County-level competition across Kenya's best youth athletes</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {[
              { emoji: '⚽', name: 'Football', sub: "Men's & Women's" },
              { emoji: '🏐', name: 'Volleyball', sub: "Men's & Women's" },
              { emoji: '🏀', name: 'Basketball', sub: "Men's & Women's" },
              { emoji: '🤾', name: 'Handball', sub: "Men's & Women's" },
              { emoji: '🏐', name: 'Netball', sub: 'Open' },
            ].map((sport, i) => (
              <motion.div
                key={sport.name}
                custom={i}
                variants={fadeUp}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true }}
                className="text-center p-5 rounded-xl bg-surface-elevated border border-border hover:border-accent/30 hover:bg-accent/5 transition-all duration-300 group cursor-pointer"
              >
                <span className="text-4xl block mb-3 group-hover:scale-110 transition-transform">{sport.emoji}</span>
                <h3 className="font-semibold text-brand-50">{sport.name}</h3>
                <p className="text-xs text-brand-300 mt-1">{sport.sub}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
