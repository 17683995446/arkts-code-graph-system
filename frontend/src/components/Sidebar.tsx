import React from 'react'
import { 
  Home, 
  FolderTree, 
  Network, 
  Search, 
  Clock 
} from 'lucide-react'
import { useAppStore } from '../store/useAppStore'

const NavItem: React.FC<{
  icon: React.ReactNode
  label: string
  page: 'dashboard' | 'explorer' | 'graph' | 'search' | 'logs'
}> = ({ icon, label, page }) => {
  const currentPage = useAppStore((state) => state.currentPage)
  const setCurrentPage = useAppStore((state) => state.setCurrentPage)
  const isActive = currentPage === page
  
  return (
    <button
      onClick={() => setCurrentPage(page)}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
        isActive
          ? 'bg-sky-600 text-white shadow-lg'
          : 'text-gray-300 hover:bg-slate-800 hover:text-white'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  )
}

export const Sidebar: React.FC = () => {
  return (
    <div className="w-64 bg-slate-900 h-screen border-r border-slate-800 flex flex-col">
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Network className="w-6 h-6 text-sky-500" />
          CodeGraph
        </h1>
        <p className="text-xs text-gray-400 mt-1">ArkTS Knowledge Graph</p>
      </div>
      
      <div className="flex-1 p-4 space-y-2">
        <NavItem 
          icon={<Home className="w-5 h-5" />} 
          label="Dashboard" 
          page="dashboard"
        />
        <NavItem 
          icon={<FolderTree className="w-5 h-5" />} 
          label="Explorer" 
          page="explorer"
        />
        <NavItem 
          icon={<Network className="w-5 h-5" />} 
          label="Graph" 
          page="graph"
        />
        <NavItem 
          icon={<Search className="w-5 h-5" />} 
          label="Search" 
          page="search"
        />
        <NavItem 
          icon={<Clock className="w-5 h-5" />} 
          label="Logs" 
          page="logs"
        />
      </div>
    </div>
  )
}
