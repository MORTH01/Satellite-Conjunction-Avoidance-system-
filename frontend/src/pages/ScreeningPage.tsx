import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { conjunctionApi } from '../services/api'
import { formatDateTime, formatRelative } from '../services/utils'

export default function ScreeningPage() {
  const qc = useQueryClient()

  const { data: runs, isLoading } = useQuery({
    queryKey: ['screening-runs'],
    queryFn: conjunctionApi.screeningHistory,
    refetchInterval: 15000,
  })

  const triggerMutation = useMutation({
    mutationFn: conjunctionApi.triggerScreen,
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ['screening-runs'] }), 3000)
    },
  })

  return (
    <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-mono font-bold text-slate-100">Screening History</h1>
          <p className="text-xs text-slate-500 mt-0.5 font-mono">
            Automated runs every 6h · Manual trigger available
          </p>
        </div>
        <button
          onClick={() => triggerMutation.mutate()}
          disabled={triggerMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600/20 border border-blue-500/40 rounded-xl text-blue-300 text-sm font-mono hover:bg-blue-600/30 transition-colors disabled:opacity-50"
        >
          <span className={triggerMutation.isPending ? 'animate-spin' : ''}>⟳</span>
          {triggerMutation.isPending ? 'Queued...' : 'Trigger Now'}
        </button>
      </div>

      <div className="glass rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-40 text-slate-500 font-mono text-sm">
            Loading screening history...
          </div>
        ) : !runs?.length ? (
          <div className="flex flex-col items-center justify-center h-40 text-slate-600 gap-2">
            <p className="font-mono text-sm">No screening runs yet</p>
            <p className="text-xs">Trigger one manually or wait for the scheduled run</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs font-mono text-slate-500 uppercase tracking-wider border-b border-slate-800">
                  <th className="text-left px-5 py-3">Started</th>
                  <th className="text-right px-5 py-3">Satellites</th>
                  <th className="text-right px-5 py-3">Pairs eval.</th>
                  <th className="text-right px-5 py-3">Events found</th>
                  <th className="text-right px-5 py-3">High-Pc</th>
                  <th className="text-center px-5 py-3">Status</th>
                  <th className="text-right px-5 py-3">Duration</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run: any) => {
                  const duration = run.completed_at
                    ? Math.round((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000)
                    : null
                  return (
                    <tr key={run.id} className="border-b border-slate-800/40 hover:bg-slate-800/20">
                      <td className="px-5 py-3">
                        <div className="font-mono text-slate-300 text-xs">{formatRelative(run.started_at)}</div>
                        <div className="text-slate-600 text-xs">{formatDateTime(run.started_at)}</div>
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-300 text-xs">{run.satellites_screened}</td>
                      <td className="px-5 py-3 text-right font-mono text-slate-300 text-xs">{run.pairs_evaluated}</td>
                      <td className="px-5 py-3 text-right font-mono text-cyan-400 text-xs">{run.events_found}</td>
                      <td className="px-5 py-3 text-right font-mono text-xs">
                        <span className={run.high_pc_events > 0 ? 'text-red-400' : 'text-slate-500'}>
                          {run.high_pc_events}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded font-mono ${
                          run.status === 'completed' ? 'bg-green-900/30 text-green-400' :
                          run.status === 'running'   ? 'bg-blue-900/30 text-blue-400' :
                          'bg-red-900/30 text-red-400'
                        }`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-500 text-xs">
                        {duration !== null ? `${duration}s` : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pipeline explanation */}
      <div className="mt-4 glass rounded-2xl p-5">
        <h3 className="text-xs font-mono font-bold text-slate-400 uppercase tracking-widest mb-3">Pipeline</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { step: '01', label: 'TLE Ingest', desc: 'Space-Track GP catalog → PostgreSQL' },
            { step: '02', label: 'Filter Pairs', desc: 'Perigee/apogee orbit overlap check' },
            { step: '03', label: 'SGP4 Screen', desc: '60s timestep coarse miss distance' },
            { step: '04', label: 'Pc + Store', desc: 'Foster Pc · write conjunction events' },
          ].map(s => (
            <div key={s.step} className="bg-slate-800/30 rounded-xl p-3">
              <span className="text-xs font-mono text-blue-500">{s.step}</span>
              <p className="text-xs font-mono font-bold text-slate-300 mt-1">{s.label}</p>
              <p className="text-xs text-slate-600 mt-0.5">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
