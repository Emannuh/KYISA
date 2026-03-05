import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { PlusIcon, TrophyIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Button, Spinner, Input, Select } from '../../components/ui'
import { useFetch, useDebounce } from '../../hooks'
import { useAuth } from '../../contexts/AuthContext'
import { competitionsAPI } from '../../api/endpoints'
import { formatDate, SPORT_TYPES } from '../../utils'

export default function CompetitionsManagePage() {
  const { isAdmin } = useAuth()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const debouncedSearch = useDebounce(search, 400)

  const { data, loading } = useFetch(
    () => competitionsAPI.list({
      search: debouncedSearch || undefined,
      status: statusFilter || undefined,
      page_size: 50,
    }),
    [debouncedSearch, statusFilter]
  )

  const competitions = data?.results || []

  return (
    <>
      <Helmet><title>Competitions — KYISA Portal</title></Helmet>

      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-brand-50">Competitions</h1>
            <p className="text-sm text-brand-300">Manage tournaments, fixtures & scheduling</p>
          </div>
          {isAdmin && (
            <Link to="/portal/competitions/create">
              <Button variant="primary" size="sm"><PlusIcon className="h-4 w-4 mr-1" /> New Competition</Button>
            </Link>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-3 max-w-lg">
          <Input placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All Status</option>
            <option value="registration">Registration</option>
            <option value="scheduling">Scheduling</option>
            <option value="ongoing">Ongoing</option>
            <option value="completed">Completed</option>
          </Select>
        </div>

        {loading ? (
          <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
        ) : competitions.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {competitions.map((comp, i) => (
              <motion.div key={comp.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
                <Link to={`/portal/competitions/${comp.id}`}>
                  <Card hover className="h-full">
                    <Card.Body>
                      <div className="flex items-start justify-between mb-2">
                        <Badge variant={comp.status === 'ongoing' ? 'danger' : comp.status === 'completed' ? 'success' : 'accent'} size="xs">
                          {comp.status}
                        </Badge>
                        <span className="text-xs text-brand-400">{formatDate(comp.start_date)}</span>
                      </div>
                      <h3 className="font-semibold text-brand-50 mb-1">{comp.name}</h3>
                      <p className="text-sm text-brand-300">{SPORT_TYPES[comp.sport_type] || comp.sport_type}</p>
                      {comp.teams_count != null && (
                        <p className="text-xs text-brand-400 mt-2">{comp.teams_count} teams registered</p>
                      )}
                    </Card.Body>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 text-brand-300">
            <TrophyIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
            <p>{search || statusFilter ? 'No competitions match your filters' : 'No competitions yet'}</p>
          </div>
        )}
      </div>
    </>
  )
}
