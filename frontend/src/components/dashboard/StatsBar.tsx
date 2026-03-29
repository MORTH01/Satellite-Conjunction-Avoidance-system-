import { useQuery } from '@tanstack/react-query'
import { conjunctionApi } from '../../services/api'
import { formatRelative } from '../../services/utils'

export default function StatsBar() {
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: conjunctionApi.stats,
    refetchInterval: 30000,
  })

  const cards = [
    {
      label: 'Active Conjunctions',
      value: stats?.active_conjunctions ?? '—',
      color: 'text-blue-400',
    },
    {
      label: 'High-Pc Events',
      value: stats?.high_pc_count ?? '—',
      color: 'text-red-400',
    },
    {
      label: 'Satellites Tracked',
      value: stats?.satellites_tracked ?? '—',
      color: 'text-cyan-400',
    },
    {
      label: 'Last Screen',
      value: stats?.last_screen_at ? formatRelative(stats.last_screen_at) : '—',
      color: stats?.last_screen_status === 'completed' ? 'text-green-400' : 'text-amber-400',
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
      {cards.map(c => (
        <div key={c.label} className="glass rounded-xl p-4">
          <p className="text-xs text-slate-500 font-mono uppercase tracking-widest mb-1">{c.label}</p>
          <p className={`text-2xl font-mono font-bold ${c.color}`}>{c.value}</p>
        </div>
      ))}
    </div>
  )
}
