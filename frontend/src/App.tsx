import React from 'react'
import { Sidebar } from './components/Sidebar'
import { DashboardPage } from './pages/DashboardPage'
import { ExplorerPage } from './pages/ExplorerPage'
import { GraphPage } from './pages/GraphPage'
import { SearchPage } from './pages/SearchPage'
import { LogsPage } from './pages/LogsPage'
import { useAppStore } from './store/useAppStore'

const PageContent: React.FC = () => {
  const currentPage = useAppStore((state) => state.currentPage)

  switch (currentPage) {
    case 'dashboard':
      return <DashboardPage />
    case 'explorer':
      return <ExplorerPage />
    case 'graph':
      return <GraphPage />
    case 'search':
      return <SearchPage />
    case 'logs':
      return <LogsPage />
    default:
      return <DashboardPage />
  }
}

export default function App() {
  return (
    <div className="flex h-screen bg-slate-950">
      <Sidebar />
      <div className="flex-1 overflow-hidden">
        <PageContent />
      </div>
    </div>
  )
}
