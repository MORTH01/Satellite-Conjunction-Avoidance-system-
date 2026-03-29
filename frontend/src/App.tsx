import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Sidebar from './components/ui/Sidebar'
import AlertBanner from './components/alerts/AlertBanner'
import DashboardPage from './pages/DashboardPage'
import ConjunctionDetailPage from './pages/ConjunctionDetailPage'
import SatellitesPage from './pages/SatellitesPage'
import ScreeningPage from './pages/ScreeningPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30000, retry: 2 },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 flex flex-col min-w-0">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/conjunction/:id" element={<ConjunctionDetailPage />} />
              <Route path="/satellites" element={<SatellitesPage />} />
              <Route path="/screening" element={<ScreeningPage />} />
            </Routes>
          </main>
          <AlertBanner />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
