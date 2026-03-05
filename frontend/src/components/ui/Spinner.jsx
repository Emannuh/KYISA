import { motion } from 'framer-motion'

const sizes = {
  xs: 'h-4 w-4 border-2',
  sm: 'h-6 w-6 border-2',
  md: 'h-8 w-8 border-[3px]',
  lg: 'h-12 w-12 border-[3px]',
}

export default function Spinner({ size = 'md', className = '' }) {
  return (
    <motion.div
      className={`rounded-full border-brand-400 border-t-accent animate-spin ${sizes[size]} ${className}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    />
  )
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <Spinner size="lg" className="mx-auto mb-4" />
        <p className="text-brand-200 text-sm">Loading...</p>
      </div>
    </div>
  )
}
