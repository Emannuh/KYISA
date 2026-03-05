import { motion } from 'framer-motion'
import { classNames } from '../../utils'

const variants = {
  primary: 'bg-accent hover:bg-accent-light text-brand-900 font-semibold',
  secondary: 'bg-brand-600 hover:bg-brand-500 text-brand-50 border border-brand-400',
  danger: 'bg-danger/20 hover:bg-danger/30 text-danger border border-danger/30',
  success: 'bg-success/20 hover:bg-success/30 text-success border border-success/30',
  ghost: 'bg-transparent hover:bg-brand-700 text-brand-100',
  outline: 'bg-transparent hover:bg-accent/10 text-accent border border-accent/40',
}

const sizes = {
  xs: 'px-2.5 py-1 text-xs rounded-md',
  sm: 'px-3 py-1.5 text-sm rounded-lg',
  md: 'px-4 py-2 text-sm rounded-lg',
  lg: 'px-6 py-3 text-base rounded-xl',
}

export default function Button({
  children, variant = 'primary', size = 'md', loading, disabled, className = '', ...props
}) {
  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      disabled={disabled || loading}
      className={classNames(
        'inline-flex items-center justify-center gap-2 font-medium transition-all duration-200',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {loading && (
        <div className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
      )}
      {children}
    </motion.button>
  )
}
