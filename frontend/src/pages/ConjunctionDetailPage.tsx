import { useState, lazy, Suspense } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { conjunctionApi, satelliteApi } from '../services/api'
import PcTimelineChart from '../components/dashboard/PcTimelineChart'
import { formatPc, pcColor, pcSeverity, formatDateTime, formatTCA } from '../services/utils'

const OrbitViewer = lazy(() => import('../components/orbit/OrbitViewer'))

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass rounded-2xl overflow-hidden mb-4">
      <div className="px-5 py-3 border-b border-slate-800">
        <h3 className="text-xs font-mono font-bold text-slate-400 uppercase tracking-widest">{title}</h3>
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

function DataRow({ label, value, mono = false }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-slate-800/50 last:border-0">
      <span className="text-xs text-slate-500 font-mono">{label}</span>
      <span className={`text-sm text-slate-200 ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  )
}

export default function ConjunctionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const eventId = parseInt(id!)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showOrbit, setShowOrbit] = useState(false)

  const { data: event, isLoading } = useQuery({
    queryKey: ['conjunction', eventId],
    queryFn: () => conjunctionApi.get(eventId),
    refetchInterval: 30000,
  })

  // Fetch orbit tracks lazily when orbit viewer opened
  const { data: primaryTrack } = useQuery({
    queryKey: ['track', event?.primary_norad],
    queryFn: () => satelliteApi.getTrack(event!.primary_norad!, 1.5),
    enabled: showOrbit && !!event?.primary_norad,
  })
  const { data: secondaryTrack } = useQuery({
    queryKey: ['track', event?.secondary_norad],
    queryFn: () => satelliteApi.getTrack(event!.secondary_norad!, 1.5),
    enabled: showOrbit && !!event?.secondary_norad,
  })

  const optimizeMutation = useMutation({
    mutationFn: () => conjunctionApi.optimize(eventId, [24, 48, 72]),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conjunction', eventId] }),
  })

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-slate-500 font-mono text-sm">Loading conjunction data...</p>
      </div>
    )
  }
  if (!event) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-red-400 font-mono text-sm">Event not found</p>
      </div>
    )
  }

  const sev = pcSeverity(event.pc)
  const color = pcColor(event.pc)
  const hasBurn = event.burn_delta_v_ms !== null && event.burn_delta_v_ms !== undefined

  const tcaPoint = primaryTrack?.track?.[Math.floor(primaryTrack.track.length / 2)]

  return (
    <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
      {/* Back + Header */}
      <div className="flex items-start gap-4 mb-6">
        <button
          onClick={() => navigate('/')}
          className="text-slate-500 hover:text-slate-300 font-mono text-sm mt-1 flex-shrink-0"
        >
          ← Back
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-lg font-mono font-bold text-slate-100 truncate max-w-xs">
              {event.primary_name ?? 'Unknown'}
            </h1>
            <span className="text-slate-600 font-mono">✕</span>
            <h1 className="text-lg font-mono font-bold text-slate-100 truncate max-w-xs">
              {event.secondary_name ?? 'Unknown'}
            </h1>
          </div>
          <div className="flex items-center gap-4 mt-1">
            <span
              className="text-sm font-mono font-bold px-2 py-0.5 rounded"
              style={{ color, background: color + '20' }}
            >
              Pc = {formatPc(event.pc)}
            </span>
            <span className="text-xs text-slate-500 font-mono">
              TCA: {formatTCA(event.tca_time)}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded font-mono ${
              sev === 'critical' ? 'bg-red-900/40 text-red-400' :
              sev === 'warning' ? 'bg-amber-900/40 text-amber-400' :
              'bg-slate-800 text-slate-400'
            }`}>
              {sev.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Orbit toggle */}
        <button
          onClick={() => setShowOrbit(v => !v)}
          className="flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-700 text-slate-300 text-xs font-mono hover:border-blue-500/50 hover:text-blue-300 transition-colors flex-shrink-0"
        >
          ◎ {showOrbit ? 'Hide' : 'Show'} 3D Orbit
        </button>
      </div>

      {/* 3D Orbit Viewer */}
      {showOrbit && (
        <div className="glass rounded-2xl overflow-hidden mb-4" style={{ height: 380 }}>
          <Suspense fallback={
            <div className="flex items-center justify-center h-full text-slate-500 font-mono text-sm">
              Loading 3D viewer...
            </div>
          }>
            <OrbitViewer
              primaryTrack={primaryTrack?.track ?? []}
              secondaryTrack={secondaryTrack?.track ?? []}
              primaryName={event.primary_name ?? 'Primary'}
              secondaryName={event.secondary_name ?? 'Secondary'}
              tcaPoint={tcaPoint}
            />
          </Suspense>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left column */}
        <div>
          <Section title="Pc Timeline">
            <PcTimelineChart
              pcHistory={event.pc_history ?? []}
              pcPostBurn={event.pc_post_burn}
              burnLeadTimeH={event.burn_lead_time_h}
            />
            {!event.covariance_available && (
              <p className="text-xs text-amber-500/70 font-mono mt-3">
                ⚠ No CDM covariance — using 1 km 1σ along-track estimate
              </p>
            )}
          </Section>

          <Section title="Conjunction Parameters">
            <DataRow label="Miss distance" value={`${event.miss_distance_km.toFixed(3)} km`} mono />
            <DataRow label="Relative speed" value={event.relative_speed_km_s ? `${event.relative_speed_km_s.toFixed(2)} km/s` : '—'} mono />
            <DataRow label="TCA (UTC)" value={formatDateTime(event.tca_time)} mono />
            <DataRow label="Pc method" value={event.pc_method} mono />
            <DataRow label="Covariance" value={event.covariance_available ? 'CDM available' : 'Estimated'} mono />
            <DataRow label="Status" value={event.status} mono />
          </Section>
        </div>

        {/* Right column */}
        <div>
          <Section title="Maneuver Optimization">
            {hasBurn ? (
              <div className="space-y-4">
                {/* Best burn summary */}
                <div className="rounded-xl p-4 bg-green-950/20 border border-green-500/20">
                  <p className="text-xs font-mono text-green-400 uppercase tracking-wider mb-3">Optimal Burn Plan</p>
                  <DataRow label="Lead time" value={`${event.burn_lead_time_h?.toFixed(0)}h before TCA`} mono />
                  <DataRow label="Δv magnitude" value={`${event.burn_delta_v_ms?.toFixed(4)} m/s`} mono />
                  {event.burn_rtn_ms && (
                    <DataRow
                      label="RTN components"
                      value={`[${event.burn_rtn_ms.map(v => v.toFixed(4)).join(', ')}] m/s`}
                      mono
                    />
                  )}
                  <DataRow
                    label="Pc post-burn"
                    value={
                      <span style={{ color: pcColor(event.pc_post_burn ?? 0) }} className="font-mono">
                        {formatPc(event.pc_post_burn ?? 0)}
                      </span>
                    }
                  />
                  {event.pc_post_burn !== null && event.pc_post_burn !== undefined && (
                    <DataRow
                      label="Pc reduction"
                      value={`${((1 - event.pc_post_burn / event.pc) * 100).toFixed(1)}%`}
                      mono
                    />
                  )}
                </div>

                {/* Re-run button */}
                <button
                  onClick={() => optimizeMutation.mutate()}
                  disabled={optimizeMutation.isPending}
                  className="w-full py-2.5 rounded-xl border border-blue-500/40 text-blue-300 text-sm font-mono hover:bg-blue-600/20 transition-colors disabled:opacity-50"
                >
                  {optimizeMutation.isPending ? 'Optimizing...' : '⟳ Re-run Optimizer'}
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 py-6">
                <p className="text-slate-500 text-sm font-mono text-center">
                  No burn plan computed yet.
                  <br />
                  Run the optimizer to find the minimum Δv maneuver.
                </p>
                <button
                  onClick={() => optimizeMutation.mutate()}
                  disabled={optimizeMutation.isPending}
                  className="flex items-center gap-2 px-5 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-white text-sm font-mono transition-colors disabled:opacity-50 disabled:cursor-wait"
                >
                  {optimizeMutation.isPending ? (
                    <>
                      <span className="animate-spin">⟳</span> Computing...
                    </>
                  ) : (
                    '⚡ Run Maneuver Optimizer'
                  )}
                </button>
                {optimizeMutation.isError && (
                  <p className="text-xs text-red-400 font-mono text-center">
                    Optimizer error — TLE data may be unavailable
                  </p>
                )}
              </div>
            )}
          </Section>

          <Section title="Object Info">
            <div className="mb-3">
              <p className="text-xs font-mono text-blue-400 mb-1">Primary (blue track)</p>
              <DataRow label="Name" value={event.primary_name ?? '—'} mono />
              <DataRow label="NORAD ID" value={event.primary_norad ?? '—'} mono />
            </div>
            <div>
              <p className="text-xs font-mono text-amber-400 mb-1">Secondary (amber track)</p>
              <DataRow label="Name" value={event.secondary_name ?? '—'} mono />
              <DataRow label="NORAD ID" value={event.secondary_norad ?? '—'} mono />
            </div>
          </Section>
        </div>
      </div>
    </div>
  )
}
