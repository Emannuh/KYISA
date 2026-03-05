import { motion } from 'framer-motion'
import { classNames } from '../../utils'

export default function Card({ children, className = '', hover = false, glow = false, ...props }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={classNames(
        'bg-surface-elevated border border-border rounded-xl overflow-hidden',
        hover && 'hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5 transition-all duration-300',
        glow && 'glow-accent',
        className,
      )}
      {...props}
    >
      {children}
    </motion.div>
  )
}

Card.Header = function CardHeader({ children, className = '' }) {
  return (
    <div className={classNames('px-5 py-4 border-b border-border', className)}>
      {children}
    </div>
  )
}

Card.Body = function CardBody({ children, className = '' }) {
  return (
    <div className={classNames('px-5 py-4', className)}>
      {children}
    </div>
  )
}
