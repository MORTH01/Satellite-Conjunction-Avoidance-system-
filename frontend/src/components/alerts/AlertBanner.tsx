import { useState, useCallback } from 'react'
import { useWebSocket } from '../../hooks/useWebSocket'
import { formatPc } from '../../services/utils'
import type { AlertMessage } from '../../types'

export default function AlertBanner() {
  const [alerts, setAlerts] = useState<AlertMessage[]>([])
  const [connected, setConnected] = useState(false)

  const onMessage = useCallback((msg: AlertMessage) => {
    if (msg.type === 'connected') { setConnected(true); return }
    if (msg.type === 'pong') return
    setAlerts(prev => [msg, ...prev].slice(0, 5))
  }, [])

  const { connected: wsConnected } = useWebSocket(onMessage)

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-80">
      {/* Connection indicator */}
      <div className="flex items-center gap-2 justify-end pr-1">
        <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-green-400 animate-pulse-slow' : 'bg-slate-600'}`} />
        <span className="text-xs text-slate-500 font-mono">{wsConnected ? 'live' : 'connecting'}</span>
      </div>

      {/* Alert cards */}
      {alerts.map((alert, i) => (
        <div
          key={i}
          className={`glass rounded-xl px-4 py-3 animate-fade-in border ${
            alert.type === 'new_conjunction' ? 'border-red-500/40 glow-red' :
            alert.type === 'optimizer_done' ? 'border-green-500/30' :
            'border-slate-700'
          }`}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              {alert.type === 'new_conjunction' && (
                <>
                  <p className="text-xs font-mono font-bold text-red-400 uppercase tracking-wider mb-1">
                    High-Pc Alert
                  </p>
                  <p className="text-xs text-slate-300 truncate">
                    {alert.primary_name} / {alert.secondary_name}
                  </p>
                  <p className="text-xs font-mono text-red-300 mt-0.5">
                    Pc = {alert.pc !== undefined ? formatPc(alert.pc) : '?'}
                  </p>
                </>
              )}
              {alert.type === 'optimizer_done' && (
                <>
                  <p className="text-xs font-mono font-bold text-green-400 uppercase tracking-wider mb-1">
                    Burn Plan Ready
                  </p>
                  <p className="text-xs text-slate-300">
                    Δv = {alert.delta_v_ms?.toFixed(3)} m/s
                  </p>
                  <p className="text-xs font-mono text-green-300 mt-0.5">
                    Pc post-burn: {alert.pc_post_burn !== undefined ? formatPc(alert.pc_post_burn) : '?'}
                  </p>
                </>
              )}
              {alert.type === 'screening_complete' && (
                <p className="text-xs text-slate-300 font-mono">{alert.message}</p>
              )}
            </div>
            <button
              onClick={() => setAlerts(prev => prev.filter((_, j) => j !== i))}
              className="text-slate-600 hover:text-slate-400 text-xs mt-0.5 flex-shrink-0"
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
