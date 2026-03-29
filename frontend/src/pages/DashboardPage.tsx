import { useQueryClient } from '@tanstack/react-query'
import { conjunctionApi } from '../services/api'
import StatsBar from '../components/dashboard/StatsBar'
import ConjunctionTable from '../components/dashboard/ConjunctionTable'

export default function DashboardPage() {
  const qc = useQueryClient()

  const handleScreen = async () => {
    try {
      await conjunctionApi.triggerScreen()
      setTimeout(() => qc.invalidateQueries({ queryKey: ['stats'] }), 2000)
    } catch {
      alert('Failed to trigger screening — is the backend running?')
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-mono font-bold text-slate-100">Mission Overview</h1>
          <p className="text-xs text-slate-500 mt-0.5 font-mono">
            Autonomous conjunction detection · Foster Pc · SGP4 propagation
          </p>
        </div>
        <button
          onClick={handleScreen}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600/20 border border-blue-500/40 rounded-xl text-blue-300 text-sm font-mono hover:bg-blue-600/30 transition-colors"
        >
          <span className="text-base">⟳</span>
          Run Screen
        </button>
      </div>

      <StatsBar />
      <ConjunctionTable />
    </div>
  )
}
