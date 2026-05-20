import React, { useState, useEffect, useRef } from 'react'
import { Network, Maximize2, Loader2 } from 'lucide-react'

interface GraphNode {
  id: string
  label: string
  type: 'class' | 'function' | 'interface'
  file_id: number
}

export const GraphPage: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [loading, setLoading] = useState(true)
  const svgRef = useRef<SVGSVGElement>(null)

  const fetchGraph = async () => {
    setLoading(true)
    try {
      const [nodesRes] = await Promise.all([
        fetch('/api/graph/nodes')
      ])
      const nodesData = await nodesRes.json()
      setNodes(nodesData.nodes || [])
    } catch (e) {
      console.error('Failed to fetch graph', e)
    } finally {
      setLoading(false)
    }
  }

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'class':
        return '#10b981'
      case 'function':
        return '#a855f7'
      case 'interface':
        return '#f97316'
      default:
        return '#60a5fa'
    }
  }

  const getNodeLabel = (type: string) => {
    switch (type) {
      case 'class':
        return 'Class'
      case 'function':
        return 'Function'
      case 'interface':
        return 'Interface'
      default:
        return 'Node'
    }
  }

  const forceLayout = (nodes: GraphNode[]) => {
    const width = 800
    const height = 600
    const padding = 50
    
    const positions = nodes.map((node, i) => {
      const angle = (2 * Math.PI * i) / nodes.length
      const radius = Math.min(width, height) / 3
      return {
        x: width / 2 + radius * Math.cos(angle),
        y: height / 2 + radius * Math.sin(angle)
      }
    })
    
    return positions
  }

  useEffect(() => {
    fetchGraph()
  }, [])

  const positions = forceLayout(nodes)

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-2">
          <Network className="w-8 h-8" />
          Code Graph
        </h1>
        <p className="text-gray-400">
          Visualize your code structure as a knowledge graph
        </p>
      </div>

      <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div className="p-4 border-b border-slate-700 bg-slate-800/50 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-sm text-gray-300">Class</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-purple-500" />
              <span className="text-sm text-gray-300">Function</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-orange-500" />
              <span className="text-sm text-gray-300">Interface</span>
            </div>
          </div>
          <button
            onClick={fetchGraph}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            <Maximize2 className="w-4 h-4" />
            Refresh
          </button>
        </div>

        <div className="p-4 bg-slate-900 min-h-[600px] flex items-center justify-center">
          {loading ? (
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-sky-500 animate-spin mx-auto mb-2" />
              <p className="text-gray-400">Loading graph...</p>
            </div>
          ) : nodes.length === 0 ? (
            <div className="text-center text-gray-500">
              <p>No nodes found. Scan your project first.</p>
            </div>
          ) : (
            <svg
              ref={svgRef}
              width="100%"
              height="600"
              viewBox="0 0 800 600"
              className="max-w-full"
            >
              {nodes.map((node, i) => {
                const pos = positions[i]
                return (
                  <g key={node.id}>
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={20}
                      fill={getNodeColor(node.type)}
                      className="hover:opacity-80 transition-opacity cursor-pointer"
                    />
                    <text
                      x={pos.x}
                      y={pos.y}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="white"
                      fontSize="10"
                      fontWeight="500"
                    >
                      {node.label.substring(0, 3)}
                    </text>
                    <text
                      x={pos.x}
                      y={pos.y + 35}
                      textAnchor="middle"
                      fill="#94a3b8"
                      fontSize="11"
                    >
                      {node.label.length > 15 ? node.label.substring(0, 15) + '...' : node.label}
                    </text>
                  </g>
                )
              })}
            </svg>
          )}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        {['class', 'function', 'interface'].map((type) => {
          const count = nodes.filter((n) => n.type === type).length
          return (
            <div key={type} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
              <h3 className="text-sm font-medium text-gray-400 mb-2">
                {getNodeLabel(type)}s
              </h3>
              <p className="text-2xl font-bold text-white">{count}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
