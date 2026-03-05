import { forwardRef } from 'react'
import { classNames } from '../../utils'

const Input = forwardRef(({ label, error, className = '', ...props }, ref) => (
  <div className="space-y-1">
    {label && <label className="block text-sm font-medium text-brand-100">{label}</label>}
    <input
      ref={ref}
      className={classNames(
        'w-full px-3 py-2.5 bg-brand-700 border rounded-lg text-brand-50 placeholder-brand-300',
        'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all duration-200',
        error ? 'border-danger' : 'border-border',
        className,
      )}
      {...props}
    />
    {error && <p className="text-xs text-danger mt-1">{error}</p>}
  </div>
))
Input.displayName = 'Input'
export default Input

export const Select = forwardRef(({ label, error, children, className = '', ...props }, ref) => (
  <div className="space-y-1">
    {label && <label className="block text-sm font-medium text-brand-100">{label}</label>}
    <select
      ref={ref}
      className={classNames(
        'w-full px-3 py-2.5 bg-brand-700 border rounded-lg text-brand-50',
        'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all duration-200',
        error ? 'border-danger' : 'border-border',
        className,
      )}
      {...props}
    >
      {children}
    </select>
    {error && <p className="text-xs text-danger mt-1">{error}</p>}
  </div>
))
Select.displayName = 'Select'

export const TextArea = forwardRef(({ label, error, className = '', ...props }, ref) => (
  <div className="space-y-1">
    {label && <label className="block text-sm font-medium text-brand-100">{label}</label>}
    <textarea
      ref={ref}
      className={classNames(
        'w-full px-3 py-2.5 bg-brand-700 border rounded-lg text-brand-50 placeholder-brand-300',
        'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all duration-200',
        error ? 'border-danger' : 'border-border',
        className,
      )}
      {...props}
    />
    {error && <p className="text-xs text-danger mt-1">{error}</p>}
  </div>
))
TextArea.displayName = 'TextArea'
