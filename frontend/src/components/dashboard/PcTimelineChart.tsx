import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts'
import type { PcHistoryPoint } from '../../types'
import { formatPc } from '../../services/utils'

interface Props {
  pcHistory: PcHistoryPoint[]
  pcPostBurn?: number | null
  burnLeadTimeH?: number | null
}

const ALERT_THRESHOLD = 1e-4

function formatPcAxis(v: number) {
  if (v === 0) return '0'
  const exp = Math.floor(Math.log10(v))
  return `1e${exp}`
}

export default function PcTimelineChart({ pcHistory, pcPostBurn, burnLeadTimeH }: Props) {
  if (!pcHistory || pcHistory.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500 text-sm font-mono">
        No Pc history available
      </div>
    )
  }

  // Build chart data — reverse so x-axis goes left=earliest → right=TCA
  const data = [...pcHistory].reverse().map(p => ({
    hours: parseFloat(p.hours_to_tca.toFixed(1)),
    pc: p.pc,
    label: `T-${p.hours_to_tca.toFixed(1)}h`,
  }))

  // Add post-burn overlay if available
  const hasBurnPlan = pcPostBurn !== null && pcPostBurn !== undefined
  const burnData = hasBurnPlan ? data.map(d => ({
    ...d,
    pc_post_burn: burnLeadTimeH && d.hours <= burnLeadTimeH ? pcPostBurn : undefined,
  })) : data

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null
    return (
      <div className="glass rounded-lg px-3 py-2 text-xs font-mono">
        <p className="text-slate-400 mb-1">T-{payload[0]?.payload?.hours}h</p>
        {payload.map((p: any) => (
          <p key={p.dataKey} style={{ color: p.color }}>
            {p.name}: {formatPc(p.value)}
          </p>
        ))}
      </div>
    )
  }

  const maxPc = Math.max(...data.map(d => d.pc), ALERT_THRESHOLD * 2)
  const minPc = Math.min(...data.map(d => d.pc)) * 0.1

  return (
    <div className="w-full h-56">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={burnData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="hours"
            reversed
            tickFormatter={v => `T-${v}h`}
            tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            label={{ value: 'Hours to TCA', position: 'insideBottom', offset: -4, fill: '#475569', fontSize: 10 }}
          />
          <YAxis
            scale="log"
            domain={[minPc, maxPc]}
            tickFormatter={formatPcAxis}
            tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={ALERT_THRESHOLD}
            stroke="#f59e0b"
            strokeDasharray="6 3"
            label={{ value: '1e-4 threshold', position: 'left', fill: '#f59e0b', fontSize: 9 }}
          />
          <Line
            type="monotone"
            dataKey="pc"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            name="Pc (pre-burn)"
          />
          {hasBurnPlan && (
            <Line
              type="monotone"
              dataKey="pc_post_burn"
              stroke="#22c55e"
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={false}
              name="Pc (post-burn)"
              connectNulls={false}
            />
          )}
          {hasBurnPlan && <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: '#94a3b8' }} />}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
