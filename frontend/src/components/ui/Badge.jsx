import { classNames } from '../../utils'

export default function Badge({ children, variant = 'default', size = 'sm', className = '' }) {
  const colors = {
    default: 'bg-brand-600 text-brand-100',
    accent: 'bg-accent/15 text-accent border border-accent/25',
    success: 'bg-success/15 text-success border border-success/25',
    warning: 'bg-warning/15 text-warning border border-warning/25',
    danger: 'bg-danger/15 text-danger border border-danger/25',
    info: 'bg-info/15 text-info border border-info/25',
  }
  const sizes = {
    xs: 'px-1.5 py-0.5 text-[10px]',
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  }
  return (
    <span className={classNames(
      'inline-flex items-center font-medium rounded-full', colors[variant], sizes[size], className
    )}>
      {children}
    </span>
  )
}
