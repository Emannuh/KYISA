import { motion } from 'framer-motion'
import { classNames } from '../../utils'

export default function StatCard({ icon, label, value, sub, color = 'accent', trend, className = '' }) {
  const colors = {
    accent: 'from-accent/15 to-transparent border-accent/20 text-accent',
    success: 'from-success/15 to-transparent border-success/20 text-success',
    warning: 'from-warning/15 to-transparent border-warning/20 text-warning',
    danger: 'from-danger/15 to-transparent border-danger/20 text-danger',
    info: 'from-info/15 to-transparent border-info/20 text-info',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      className={classNames(
        'bg-gradient-to-br border rounded-xl p-5 transition-all duration-300',
        colors[color],
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-brand-200 text-sm font-medium mb-1">{label}</p>
          <p className="text-3xl font-bold text-brand-50">{value}</p>
          {sub && <p className="text-brand-300 text-xs mt-1">{sub}</p>}
        </div>
        {icon && <span className="text-2xl opacity-60">{icon}</span>}
      </div>
      {trend !== undefined && (
        <p className={classNames('text-xs mt-2 font-medium', trend >= 0 ? 'text-success' : 'text-danger')}>
          {trend >= 0 ? '↗' : '↘'} {Math.abs(trend)}% from last week
        </p>
      )}
    </motion.div>
  )
}
