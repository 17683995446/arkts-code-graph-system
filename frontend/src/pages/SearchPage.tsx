import React, { useState, useEffect, useCallback } from 'react'
import { Search, FileCode, FunctionSquare, Boxes, Layers } from 'lucide-react'

const debounce = (func: Function, wait: number) => {
  let timeout: number
  const debounced = (...args: any[]) => {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = window.setTimeout(later, wait)
  }
  debounced.cancel = () => {
    clearTimeout(timeout)
  }
  return debounced
}

export const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any>({ functions: [], classes: [], interfaces: [] })
  const [loading, setLoading] = useState(false)

  const performSearch = useCallback(
    debounce((searchQuery: string) => {
      if (!searchQuery.trim()) {
        setResults({ functions: [], classes: [], interfaces: [] })
        return
      }
      
      const fetchData = async () => {
        setLoading(true)
        try {
          const res = await fetch(`/api/search?q=${encodeURIComponent(searchQuery)}`)
          const data = await res.json()
          setResults(data)
        } catch (e) {
          console.error('Failed to search', e)
        } finally {
          setLoading(false)
        }
      }
      fetchData()
    }, 300),
    []
  )

  useEffect(() => {
    performSearch(query)
    return () => (performSearch as any).cancel?.()
  }, [query, performSearch])

  const hasResults = 
    results.functions?.length > 0 || 
    results.classes?.length > 0 || 
    results.interfaces?.length > 0

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Search</h1>
        <p className="text-gray-400">
          Find functions, classes, and interfaces in your codebase
        </p>
      </div>

      <div className="max-w-2xl mb-8">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for functions, classes, interfaces..."
            className="w-full pl-12 pr-4 py-4 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-sky-500 transition-all"
          />
          {loading && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2">
              <div className="w-5 h-5 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
      </div>

      {query && !hasResults && !loading && (
        <div className="text-center py-12 text-gray-500">
          No results found for "{query}"
        </div>
      )}

      <div className="space-y-8">
        {results.functions?.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <FunctionSquare className="w-5 h-5 text-purple-400" />
              Functions ({results.functions.length})
            </h2>
            <div className="grid gap-3">
              {results.functions.map((func: any, idx: number) => (
                <div key={idx} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-white">{func.name}</h3>
                    <span className="text-sm text-gray-400">
                      {func.file_path?.split('/').pop()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {results.classes?.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Boxes className="w-5 h-5 text-green-400" />
              Classes ({results.classes.length})
            </h2>
            <div className="grid gap-3">
              {results.classes.map((cls: any, idx: number) => (
                <div key={idx} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-white">{cls.name}</h3>
                    <span className="text-sm text-gray-400">
                      {cls.file_path?.split('/').pop()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {results.interfaces?.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Layers className="w-5 h-5 text-orange-400" />
              Interfaces ({results.interfaces.length})
            </h2>
            <div className="grid gap-3">
              {results.interfaces.map((iface: any, idx: number) => (
                <div key={idx} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-white">{iface.name}</h3>
                    <span className="text-sm text-gray-400">
                      {iface.file_path?.split('/').pop()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
