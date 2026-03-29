import { formatDistanceToNow, format, differenceInHours } from 'date-fns'

export function formatPc(pc: number): string {
  if (pc === 0) return '< 1e-10'
  if (pc >= 0.01) return (pc * 100).toFixed(2) + '%'
  const exp = Math.floor(Math.log10(pc))
  const mantissa = pc / Math.pow(10, exp)
  return `${mantissa.toFixed(2)}e${exp}`
}

export function pcSeverity(pc: number): 'critical' | 'warning' | 'low' | 'minimal' {
  if (pc >= 1e-3) return 'critical'
  if (pc >= 1e-4) return 'warning'
  if (pc >= 1e-5) return 'low'
  return 'minimal'
}

export function pcColor(pc: number): string {
  const s = pcSeverity(pc)
  if (s === 'critical') return '#ef4444'
  if (s === 'warning')  return '#f59e0b'
  if (s === 'low')      return '#3b82f6'
  return '#6b7280'
}

export function formatTCA(tcaTime: string): string {
  const date = new Date(tcaTime)
  const hours = differenceInHours(date, new Date())
  if (hours < 0) return 'Passed'
  if (hours < 24) return `T-${hours.toFixed(1)}h`
  return `T-${(hours / 24).toFixed(1)}d`
}

export function formatDateTime(dt: string): string {
  return format(new Date(dt), 'yyyy-MM-dd HH:mm:ss') + ' UTC'
}

export function formatRelative(dt: string): string {
  return formatDistanceToNow(new Date(dt), { addSuffix: true })
}

export function clsx(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(' ')
}
