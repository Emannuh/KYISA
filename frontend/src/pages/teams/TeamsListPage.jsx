import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { PlusIcon, MagnifyingGlassIcon, UsersIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Spinner, Input, Button } from '../../components/ui'
import { useFetch, useDebounce } from '../../hooks'
import { useAuth } from '../../contexts/AuthContext'
import { teamsAPI } from '../../api/endpoints'
import { SPORT_TYPES } from '../../utils'

export default function TeamsListPage() {
  const { isAdmin } = useAuth()
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 400)
  const { data, loading, refetch } = useFetch(
    () => teamsAPI.list({ search: debouncedSearch || undefined, page_size: 50 }),
    [debouncedSearch]
  )

  const teams = data?.results || []

  return (
    <>
      <Helmet><title>Teams — KYISA Portal</title></Helmet>

      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-brand-50">Teams</h1>
            <p className="text-sm text-brand-300">Manage registered teams and players</p>
          </div>
          <Link to="/register/team">
            <Button variant="primary" size="sm">
              <PlusIcon className="h-4 w-4 mr-1" /> Register Team
            </Button>
          </Link>
        </div>

        {/* Search */}
        <div className="max-w-sm">
          <Input
            placeholder="Search teams..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            icon={<MagnifyingGlassIcon className="h-4 w-4 text-brand-400" />}
          />
        </div>

        {loading ? (
          <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
        ) : teams.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {teams.map((team, i) => (
              <motion.div
                key={team.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <Link to={`/portal/teams/${team.id}`}>
                  <Card hover className="h-full">
                    <Card.Body>
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold text-brand-50 flex-1">{team.name}</h3>
                        <Badge
                          variant={team.is_approved ? 'success' : 'warning'}
                          size="xs"
                        >
                          {team.is_approved ? 'Approved' : 'Pending'}
                        </Badge>
                      </div>
                      <p className="text-sm text-brand-300">{team.county}</p>
                      <div className="flex items-center gap-3 mt-3 text-xs text-brand-400">
                        <span className="flex items-center gap-1">
                          <UsersIcon className="h-3.5 w-3.5" /> {team.players_count ?? 0} players
                        </span>
                        <span>{SPORT_TYPES[team.sport_type] || team.sport_type}</span>
                        {team.gender && <Badge variant="default" size="xs">{team.gender}</Badge>}
                      </div>
                    </Card.Body>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 text-brand-300">
            <UsersIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
            <p className="text-lg">{search ? 'No teams match your search' : 'No teams registered yet'}</p>
          </div>
        )}
      </div>
    </>
  )
}
