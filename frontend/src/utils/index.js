import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns'

/**
 * Format a date string. Pass `true` as 2nd arg to include time, or a date-fns format string.
 */
export const formatDate = (dateStr, fmtOrTime = 'dd MMM yyyy') => {
  if (!dateStr) return '—'
  const fmt = fmtOrTime === true ? 'dd MMM yyyy HH:mm' : fmtOrTime
  const d = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr
  return isValid(d) ? format(d, fmt) : '—'
}

export const formatDateTime = (dateStr) => formatDate(dateStr, true)

export const timeAgo = (dateStr) => {
  if (!dateStr) return '—'
  const d = parseISO(dateStr)
  return isValid(d) ? formatDistanceToNow(d, { addSuffix: true }) : '—'
}

export const formatCurrency = (amount, currency = 'KES') => {
  if (amount == null) return '—'
  return `${currency} ${Number(amount).toLocaleString('en-KE', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

export const ROLE_LABELS = {
  admin: 'Administrator',
  fkf_admin: 'FKF Admin',
  competition_manager: 'Competition Manager',
  team_manager: 'Team Manager',
  treasurer: 'Treasurer',
  referee_manager: 'Referee Manager',
  referee: 'Referee',
  jury_chair: 'Jury Chair',
}

/** Lookup object — SPORT_TYPES['football_men'] → "Football Men's" */
export const SPORT_TYPES = {
  football_men: "Football Men's",
  football_women: "Football Women's",
  volleyball_men: "Volleyball Men's",
  volleyball_women: "Volleyball Women's",
  basketball_men: "Basketball Men's",
  basketball_women: "Basketball Women's",
  handball_men: "Handball Men's",
  handball_women: "Handball Women's",
  netball: 'Netball',
}

/** Array form for <Select> dropdowns */
export const SPORT_TYPE_OPTIONS = Object.entries(SPORT_TYPES).map(([value, label]) => ({ value, label }))

export const STATUS_COLORS = {
  pending: 'text-warning',
  verified: 'text-success',
  rejected: 'text-danger',
  eligible: 'text-success',
  ineligible: 'text-danger',
  registered: 'text-info',
  suspended: 'text-danger',
  clear: 'text-success',
  flagged: 'text-danger',
  not_checked: 'text-brand-200',
  failed: 'text-danger',
}

export const classNames = (...classes) => classes.filter(Boolean).join(' ')
