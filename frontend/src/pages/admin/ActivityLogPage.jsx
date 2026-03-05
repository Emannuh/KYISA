import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { ClipboardDocumentListIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Spinner } from '../../components/ui'
import { useFetch } from '../../hooks'
import { portalAPI } from '../../api/endpoints'
import { formatDate } from '../../utils'

export default function ActivityLogPage() {
  const { data, loading } = useFetch(() => portalAPI.getActivityLogs({ page_size: 100 }), [])
  const logs = data?.results || data || []

  return (
    <>
      <Helmet><title>Activity Logs — KYISA Admin</title></Helmet>

      <div className="space-y-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-brand-50">Activity Logs</h1>
          <p className="text-sm text-brand-300">Audit trail of all system actions</p>
        </motion.div>

        {loading ? (
          <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
        ) : logs.length > 0 ? (
          <Card>
            <Card.Body className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-brand-300 text-xs uppercase tracking-wider">
                      <th className="px-4 py-3 text-left">Timestamp</th>
                      <th className="px-4 py-3 text-left">User</th>
                      <th className="px-4 py-3 text-left">Action</th>
                      <th className="px-4 py-3 text-left">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-brand-800/30 transition-colors">
                        <td className="px-4 py-2.5 text-brand-300 text-xs whitespace-nowrap">{formatDate(log.timestamp || log.created_at, true)}</td>
                        <td className="px-4 py-2.5 text-brand-50">{log.user_display || log.username || '—'}</td>
                        <td className="px-4 py-2.5">
                          <Badge variant="accent" size="xs">{log.action || log.action_type}</Badge>
                        </td>
                        <td className="px-4 py-2.5 text-brand-200 truncate max-w-xs">{log.description || log.details || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card.Body>
          </Card>
        ) : (
          <div className="text-center py-16 text-brand-300">
            <ClipboardDocumentListIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
            <p>No activity logs found</p>
          </div>
        )}
      </div>
    </>
  )
}
