import React, { useState, useEffect } from 'react'
import { FileCode, FunctionSquare, Boxes, Layers, Play, Square, RefreshCw, Database } from 'lucide-react'

interface Stats {
  files: number
  functions: number
  classes: number
  interfaces: number
  last_parsed: number | null
  watching: boolean
}

const StatCard: React.FC<{
  title: string
  value: number
  icon: React.ReactNode
  color: string
}> = ({ title, value, icon, color }) => {
  return (
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 hover:border-sky-500/50 transition-all">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg ${color}`}>
          {icon}
        </div>
      </div>
      <p className="text-3xl font-bold text-white mb-1">{value}</p>
      <p className="text-sm text-gray-400">{title}</p>
    </div>
  )
}

const ActionCard: React.FC<{
  title: string
  description: string
  icon: React.ReactNode
  onClick: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary'
}> = ({ title, description, icon, onClick, disabled = false, variant = 'primary' }) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`w-full text-left p-6 rounded-xl border transition-all ${
        variant === 'primary'
          ? 'bg-gradient-to-br from-sky-600 to-sky-700 border-sky-500 hover:from-sky-500 hover:to-sky-600'
          : 'bg-slate-800 border-slate-700 hover:border-slate-600'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <div className="flex items-start gap-4">
        <div className={variant === 'primary' ? 'text-white' : 'text-sky-400'}>
          {icon}
        </div>
        <div>
          <h3 className={`font-semibold ${variant === 'primary' ? 'text-white' : 'text-white'}`}>
            {title}
          </h3>
          <p className={`text-sm mt-1 ${variant === 'primary' ? 'text-sky-100' : 'text-gray-400'}`}>
            {description}
          </p>
        </div>
      </div>
    </button>
  )
}

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(false)
  const [isWatching, setIsWatching] = useState(false)

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/project/stats')
      const data = await res.json()
      setStats(data)
      setIsWatching(data.watching)
    } catch (e) {
      console.error('Failed to fetch stats', e)
    }
  }

  const handleScan = async () => {
    setLoading(true)
    try {
      await fetch('/api/project/scan?root_dir=/workspace/test-arkts-project', { method: 'POST' })
      await fetchStats()
    } catch (e) {
      console.error('Failed to scan', e)
    } finally {
      setLoading(false)
    }
  }

  const handleWatchStart = async () => {
    try {
      await fetch('/api/watch/start?root_dir=/workspace/test-arkts-project', { method: 'POST' })
      await fetchStats()
    } catch (e) {
      console.error('Failed to start watch', e)
    }
  }

  const handleWatchStop = async () => {
    try {
      await fetch('/api/watch/stop', { method: 'POST' })
      await fetchStats()
    } catch (e) {
      console.error('Failed to stop watch', e)
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-gray-400">
          Overview of your ArkTS code knowledge graph
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Files"
          value={stats?.files || 0}
          icon={<FileCode className="w-6 h-6 text-blue-400" />}
          color="bg-blue-600/20"
        />
        <StatCard
          title="Functions"
          value={stats?.functions || 0}
          icon={<FunctionSquare className="w-6 h-6 text-purple-400" />}
          color="bg-purple-600/20"
        />
        <StatCard
          title="Classes"
          value={stats?.classes || 0}
          icon={<Boxes className="w-6 h-6 text-green-400" />}
          color="bg-green-600/20"
        />
        <StatCard
          title="Interfaces"
          value={stats?.interfaces || 0}
          icon={<Layers className="w-6 h-6 text-orange-400" />}
          color="bg-orange-600/20"
        />
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-semibold text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ActionCard
            title="Full Scan"
            description="Scan all files and rebuild the knowledge graph"
            icon={<Database className="w-8 h-8" />}
            onClick={handleScan}
            disabled={loading}
          />
          {!isWatching ? (
            <ActionCard
              title="Start Watching"
              description="Start listening for file changes"
              icon={<Play className="w-8 h-8" />}
              onClick={handleWatchStart}
              variant="secondary"
            />
          ) : (
            <ActionCard
              title="Stop Watching"
              description="Stop listening for file changes"
              icon={<Square className="w-8 h-8" />}
              onClick={handleWatchStop}
              variant="secondary"
            />
          )}
          <ActionCard
            title="Refresh Stats"
            description="Refresh the dashboard statistics"
            icon={<RefreshCw className={`w-8 h-8 ${loading ? 'animate-spin' : ''}`} />}
            onClick={fetchStats}
            variant="secondary"
            disabled={loading}
          />
        </div>
      </div>

      {stats?.last_parsed && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h3 className="text-sm font-medium text-gray-400 mb-2">Last Updated</h3>
          <p className="text-white">
            {new Date(stats.last_parsed * 1000).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  )
}
