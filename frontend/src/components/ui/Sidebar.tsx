import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/',            label: 'Dashboard',    icon: '⬡' },
  { to: '/satellites',  label: 'Satellites',   icon: '◉' },
  { to: '/screening',   label: 'Screening',    icon: '⟳' },
]

export default function Sidebar() {
  return (
    <aside className="w-16 lg:w-56 flex-shrink-0 flex flex-col glass border-r border-slate-800/60 min-h-screen">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center flex-shrink-0">
            <span className="text-blue-400 text-sm font-bold font-mono">CA</span>
          </div>
          <div className="hidden lg:block">
            <p className="text-xs font-mono font-bold text-slate-200 leading-tight">Conjunction</p>
            <p className="text-xs font-mono text-slate-500 leading-tight">Avoidance System</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 flex flex-col gap-1">
        {NAV.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-mono ${
                isActive
                  ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/60'
              }`
            }
          >
            <span className="text-base leading-none flex-shrink-0">{item.icon}</span>
            <span className="hidden lg:block">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-slate-800/60 hidden lg:block">
        <p className="text-xs text-slate-600 font-mono">v1.0.0</p>
        <p className="text-xs text-slate-700 font-mono mt-0.5">Foster Pc · SGP4</p>
      </div>
    </aside>
  )
}
