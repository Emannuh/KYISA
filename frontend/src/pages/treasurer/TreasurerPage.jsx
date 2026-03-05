import { useState } from 'react'
import { Helmet } from 'react-helmet-async'
import { motion } from 'framer-motion'
import { BanknotesIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'
import { Card, Badge, Button, Spinner, Select, StatCard } from '../../components/ui'
import { useFetch, useMutation } from '../../hooks'
import { portalAPI } from '../../api/endpoints'
import { formatDate, formatCurrency } from '../../utils'

export default function TreasurerPage() {
  const [statusFilter, setStatusFilter] = useState('pending')
  const { data, loading, refetch } = useFetch(
    () => portalAPI.getTreasurerPayments({ status: statusFilter || undefined, page_size: 50 }),
    [statusFilter]
  )

  const payments = data?.results || data || []

  const verifyMutation = useMutation(
    (id) => portalAPI.verifyPayment(id),
    { successMsg: 'Payment verified', onSuccess: refetch }
  )
  const rejectMutation = useMutation(
    (id) => portalAPI.rejectPayment(id),
    { successMsg: 'Payment rejected', onSuccess: refetch }
  )

  return (
    <>
      <Helmet><title>Treasurer — KYISA Portal</title></Helmet>

      <div className="space-y-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-brand-50">Treasurer — Payments</h1>
          <p className="text-sm text-brand-300">Verify and manage team registration payments</p>
        </motion.div>

        <div className="max-w-xs">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="verified">Verified</option>
            <option value="rejected">Rejected</option>
          </Select>
        </div>

        {loading ? (
          <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
        ) : payments.length > 0 ? (
          <Card>
            <Card.Body className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-brand-300 text-xs uppercase tracking-wider">
                      <th className="px-4 py-3 text-left">Team</th>
                      <th className="px-4 py-3 text-left">Reference</th>
                      <th className="px-4 py-3 text-right">Amount</th>
                      <th className="px-4 py-3 text-center">Date</th>
                      <th className="px-4 py-3 text-center">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {payments.map((p) => (
                      <tr key={p.id} className="hover:bg-brand-800/30 transition-colors">
                        <td className="px-4 py-2.5 font-medium text-brand-50">{p.team_name || '—'}</td>
                        <td className="px-4 py-2.5 text-brand-200">{p.reference || p.transaction_code || '—'}</td>
                        <td className="px-4 py-2.5 text-right text-accent font-semibold">{formatCurrency(p.amount)}</td>
                        <td className="px-4 py-2.5 text-center text-brand-300 text-xs">{formatDate(p.created_at || p.payment_date)}</td>
                        <td className="px-4 py-2.5 text-center">
                          <Badge variant={p.status === 'verified' ? 'success' : p.status === 'rejected' ? 'danger' : 'warning'} size="xs">
                            {p.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          {p.status === 'pending' && (
                            <div className="flex items-center justify-end gap-1">
                              <button onClick={() => verifyMutation.mutate(p.id)} className="p-1 rounded hover:bg-green-900/30 text-green-400">
                                <CheckCircleIcon className="h-5 w-5" />
                              </button>
                              <button onClick={() => rejectMutation.mutate(p.id)} className="p-1 rounded hover:bg-red-900/30 text-red-400">
                                <XCircleIcon className="h-5 w-5" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card.Body>
          </Card>
        ) : (
          <div className="text-center py-16 text-brand-300">
            <BanknotesIcon className="h-14 w-14 mx-auto mb-4 opacity-30" />
            <p>{statusFilter ? `No ${statusFilter} payments` : 'No payment records'}</p>
          </div>
        )}
      </div>
    </>
  )
}
