import React, { useEffect } from 'react'
import { Clock, CheckCircle2, AlertCircle, Activity } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'

const LogItem: React.FC<{ log: any }> = ({ log }) => {
  const getStatusIcon = () => {
    switch (log.status) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />
      default:
        return <Activity className="w-4 h-4 text-sky-400" />
    }
  }

  const getStatusColor = () => {
    switch (log.status) {
      case 'success':
        return 'border-green-500/30 bg-green-500/5'
      case 'error':
        return 'border-red-500/30 bg-red-500/5'
      default:
        return 'border-sky-500/30 bg-sky-500/5'
    }
  }

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000)
    return date.toLocaleTimeString()
  }

  return (
    <div className={`p-4 rounded-lg border-l-4 ${getStatusColor()}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="font-medium text-white capitalize">
            {log.type} - {log.status}
          </span>
        </div>
        <span className="text-sm text-gray-400 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {formatTime(log.timestamp)}
        </span>
      </div>
      
      {log.file && (
        <p className="text-sm text-gray-300 mb-1">
          File: <span className="text-sky-400">{log.file}</span>
        </p>
      )}
      
      {log.duration !== undefined && (
        <p className="text-sm text-gray-400">
          Duration: <span className="text-purple-400">{log.duration.toFixed(4)}s</span>
        </p>
      )}
      
      {log.parsed && (
        <div className="mt-2 flex gap-4 text-xs text-gray-400">
          <span>Functions: {log.parsed.functions || 0}</span>
          <span>Classes: {log.parsed.classes || 0}</span>
          <span>Interfaces: {log.parsed.interfaces || 0}</span>
        </div>
      )}
      
      {log.error && (
        <p className="text-sm text-red-400 mt-1">
          Error: {log.error}
        </p>
      )}
    </div>
  )
}

export const LogsPage: React.FC = () => {
  const logs = useAppStore((state) => state.updateLogs)
  const addUpdateLog = useAppStore((state) => state.addUpdateLog)

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/ws`)
    
    ws.onmessage = (event) => {
      try {
        const log = JSON.parse(event.data)
        addUpdateLog(log)
      } catch (e) {
        console.error('Failed to parse log message', e)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }

    return () => ws.close()
  }, [addUpdateLog])

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch('/api/watch/logs')
        const data = await res.json()
        data.logs?.forEach((log: any) => addUpdateLog(log))
      } catch (e) {
        console.error('Failed to fetch initial logs', e)
      }
    }
    
    fetchLogs()
  }, [addUpdateLog])

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Update Logs</h1>
        <p className="text-gray-400">
          Real-time file change and parsing activity
        </p>
      </div>

      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div className="p-4 border-b border-slate-700 bg-slate-800/50">
          <div className="flex items-center justify-between">
            <h2 className="text-white font-semibold flex items-center gap-2">
              <Activity className="w-5 h-5 text-sky-400" />
              Recent Activity
            </h2>
            <span className="text-sm text-gray-400">
              {logs.length} entries
            </span>
          </div>
        </div>
        
        <div className="p-4 space-y-3 max-h-[600px] overflow-y-auto">
          {logs.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No logs yet. Start watching files to see updates here.
            </div>
          ) : (
            [...logs].reverse().map((log, idx) => (
              <LogItem key={idx} log={log} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
