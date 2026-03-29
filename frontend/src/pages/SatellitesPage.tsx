import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { satelliteApi } from '../services/api'

export default function SatellitesPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [debouncedSearch, setDebouncedSearch] = useState('')

  const handleSearch = (val: string) => {
    setSearch(val)
    clearTimeout((handleSearch as any)._t)
    ;(handleSearch as any)._t = setTimeout(() => { setDebouncedSearch(val); setPage(1) }, 350)
  }

  const { data, isLoading } = useQuery({
    queryKey: ['satellites', page, debouncedSearch],
    queryFn: () => satelliteApi.list(page, 50, debouncedSearch || undefined),
    refetchInterval: 120000,
  })

  return (
    <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-mono font-bold text-slate-100">Satellite Catalog</h1>
          <p className="text-xs text-slate-500 mt-0.5 font-mono">
            {data?.total ?? '—'} active objects tracked
          </p>
        </div>
        <input
          type="text"
          placeholder="Search name or NORAD ID..."
          value={search}
          onChange={e => handleSearch(e.target.value)}
          className="bg-slate-800/60 border border-slate-700 rounded-xl px-4 py-2 text-sm font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 w-64"
        />
      </div>

      <div className="glass rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs font-mono text-slate-500 uppercase tracking-wider border-b border-slate-800">
                <th className="text-left px-5 py-3">NORAD ID</th>
                <th className="text-left px-5 py-3">Name</th>
                <th className="text-left px-5 py-3">Type</th>
                <th className="text-left px-5 py-3">Country</th>
                <th className="text-right px-5 py-3">Updated</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-slate-500 font-mono text-sm">
                    Loading catalog...
                  </td>
                </tr>
              ) : !data?.items?.length ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-slate-600 font-mono text-sm">
                    {debouncedSearch ? 'No satellites match your search' : 'No satellites in database — run TLE ingest first'}
                  </td>
                </tr>
              ) : data.items.map((sat: any) => (
                <tr key={sat.id} className="border-b border-slate-800/40 hover:bg-slate-800/30 transition-colors">
                  <td className="px-5 py-3 font-mono text-cyan-400 text-xs">{sat.norad_id}</td>
                  <td className="px-5 py-3 font-mono text-slate-200 text-xs max-w-[200px] truncate">{sat.name}</td>
                  <td className="px-5 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-mono ${
                      sat.object_type === 'PAYLOAD' ? 'bg-blue-900/30 text-blue-400' :
                      sat.object_type === 'DEBRIS' ? 'bg-red-900/30 text-red-400' :
                      sat.object_type === 'ROCKET BODY' ? 'bg-amber-900/30 text-amber-400' :
                      'bg-slate-800 text-slate-500'
                    }`}>
                      {sat.object_type ?? '—'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-slate-400 font-mono text-xs">{sat.country ?? '—'}</td>
                  <td className="px-5 py-3 text-right text-slate-600 font-mono text-xs">
                    {new Date(sat.updated_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {data && data.pages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-slate-800">
            <span className="text-xs text-slate-500 font-mono">Page {page} of {data.pages}</span>
            <div className="flex gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="text-xs px-3 py-1 rounded font-mono bg-slate-800 text-slate-400 hover:bg-slate-700 disabled:opacity-30"
              >
                ← Prev
              </button>
              <button
                onClick={() => setPage(p => Math.min(data.pages, p + 1))}
                disabled={page === data.pages}
                className="text-xs px-3 py-1 rounded font-mono bg-slate-800 text-slate-400 hover:bg-slate-700 disabled:opacity-30"
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
