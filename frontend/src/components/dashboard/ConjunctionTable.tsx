import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { conjunctionApi } from '../../services/api'
import { formatPc, pcColor, pcSeverity, formatTCA } from '../../services/utils'
import type { ConjunctionListItem } from '../../types'

const SEVERITY_RING: Record<string, string> = {
  critical: 'border-red-500/60 glow-red',
  warning:  'border-amber-500/40 glow-amber',
  low:      'border-blue-500/30 glow-blue',
  minimal:  'border-slate-700',
}

function PcBadge({ pc }: { pc: number }) {
  const sev = pcSeverity(pc)
  const color = pcColor(pc)
  return (
    <span
      className="font-mono text-sm font-bold px-2 py-0.5 rounded"
      style={{ color, background: color + '18' }}
    >
      {formatPc(pc)}
    </span>
  )
}

function TcaCountdown({ tca }: { tca: string }) {
  const label = formatTCA(tca)
  const hours = (new Date(tca).getTime() - Date.now()) / 3600000
  const urgent = hours > 0 && hours < 24
  return (
    <span className={`font-mono text-sm ${urgent ? 'text-red-400 animate-pulse-slow' : 'text-slate-300'}`}>
      {label}
    </span>
  )
}

export default function ConjunctionTable() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState<'pc' | 'tca_time' | 'miss_distance_km'>('pc')
  const [minPc, setMinPc] = useState<number | undefined>(undefined)

  const { data, isLoading } = useQuery({
    queryKey: ['conjunctions', page, sortBy, minPc],
    queryFn: () => conjunctionApi.list(page, 20, sortBy, minPc),
    refetchInterval: 60000,
  })

  const filterOpts = [
    { label: 'All', value: undefined },
    { label: 'High (≥1e-4)', value: 1e-4 },
    { label: 'Critical (≥1e-3)', value: 1e-3 },
  ]

  return (
    <div className="glass rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-slate-800">
        <h2 className="font-mono text-sm font-bold text-slate-200 uppercase tracking-widest">
          Conjunction Events
        </h2>
        <div className="flex items-center gap-3">
          {/* Filter by Pc */}
          <div className="flex gap-1">
            {filterOpts.map(opt => (
              <button
                key={String(opt.value)}
                onClick={() => { setMinPc(opt.value); setPage(1) }}
                className={`text-xs px-3 py-1.5 rounded font-mono transition-colors ${
                  minPc === opt.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {/* Sort */}
          <select
            value={sortBy}
            onChange={e => { setSortBy(e.target.value as typeof sortBy); setPage(1) }}
            className="text-xs bg-slate-800 text-slate-300 rounded px-2 py-1.5 font-mono border border-slate-700 focus:outline-none"
          >
            <option value="pc">Sort: Pc</option>
            <option value="tca_time">Sort: TCA</option>
            <option value="miss_distance_km">Sort: Miss Dist</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-48 text-slate-500 font-mono text-sm">
          Loading conjunction data...
        </div>
      ) : !data?.items?.length ? (
        <div className="flex flex-col items-center justify-center h-48 text-slate-500 gap-2">
          <p className="font-mono text-sm">No conjunction events found</p>
          <p className="text-xs text-slate-600">Run a screening or check back after TLE ingestion</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs font-mono text-slate-500 uppercase tracking-wider border-b border-slate-800">
                <th className="text-left px-5 py-3">Primary</th>
                <th className="text-left px-5 py-3">Secondary</th>
                <th className="text-right px-5 py-3">Pc</th>
                <th className="text-right px-5 py-3">Miss dist</th>
                <th className="text-right px-5 py-3">TCA</th>
                <th className="text-center px-5 py-3">Burn</th>
                <th className="text-center px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((ev: ConjunctionListItem, i: number) => {
                const sev = pcSeverity(ev.pc)
                return (
                  <tr
                    key={ev.id}
                    onClick={() => navigate(`/conjunction/${ev.id}`)}
                    className={`
                      border-b border-slate-800/50 cursor-pointer transition-colors
                      hover:bg-slate-800/40 animate-fade-in
                      ${sev === 'critical' ? 'bg-red-950/10' : ''}
                      ${sev === 'warning'  ? 'bg-amber-950/10' : ''}
                    `}
                    style={{ animationDelay: `${i * 30}ms` }}
                  >
                    <td className="px-5 py-3">
                      <div className="font-mono text-slate-200 text-xs truncate max-w-[140px]">
                        {ev.primary_name ?? 'Unknown'}
                      </div>
                      <div className="text-slate-600 text-xs">{ev.primary_norad}</div>
                    </td>
                    <td className="px-5 py-3">
                      <div className="font-mono text-slate-200 text-xs truncate max-w-[140px]">
                        {ev.secondary_name ?? 'Unknown'}
                      </div>
                      <div className="text-slate-600 text-xs">{ev.secondary_norad}</div>
                    </td>
                    <td className="px-5 py-3 text-right"><PcBadge pc={ev.pc} /></td>
                    <td className="px-5 py-3 text-right font-mono text-slate-300 text-xs">
                      {ev.miss_distance_km.toFixed(3)} km
                    </td>
                    <td className="px-5 py-3 text-right"><TcaCountdown tca={ev.tca_time} /></td>
                    <td className="px-5 py-3 text-center">
                      {ev.has_burn_plan ? (
                        <span className="text-xs text-green-400 font-mono">Planned</span>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded font-mono ${
                        ev.status === 'active' ? 'bg-blue-900/40 text-blue-400' : 'bg-slate-800 text-slate-500'
                      }`}>
                        {ev.status}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between px-5 py-3 border-t border-slate-800">
          <span className="text-xs text-slate-500 font-mono">{data.total} events total</span>
          <div className="flex gap-1">
            {Array.from({ length: Math.min(data.pages, 5) }, (_, i) => i + 1).map(p => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`text-xs px-3 py-1 rounded font-mono ${
                  p === page ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
