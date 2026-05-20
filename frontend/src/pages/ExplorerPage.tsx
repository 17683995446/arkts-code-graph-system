import React, { useState, useEffect } from 'react'
import { FolderTree, FileCode, ChevronDown, ChevronRight, Code2, Box } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'

interface FileInfo {
  id: number
  path: string
  modified: number
  last_parsed: number
}

interface FunctionInfo {
  name: string
  return_type?: string
  params?: any[]
}

interface ClassInfo {
  name: string
  extends?: string
}

export const ExplorerPage: React.FC = () => {
  const [files, setFiles] = useState<FileInfo[]>([])
  const [selectedFileData, setSelectedFileData] = useState<any>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const selectedFileId = useAppStore((state) => state.selectedFileId)
  const setSelectedFileId = useAppStore((state) => state.setSelectedFileId)

  const fetchFiles = async () => {
    try {
      const res = await fetch('/api/project/files')
      const data = await res.json()
      setFiles(data.files || [])
    } catch (e) {
      console.error('Failed to fetch files', e)
    }
  }

  const fetchFileDetails = async (fileId: number) => {
    try {
      const [fileRes, functionsRes, classesRes] = await Promise.all([
        fetch(`/api/files/${fileId}`),
        fetch(`/api/files/${fileId}/functions`),
        fetch(`/api/files/${fileId}/classes`)
      ])
      
      const file = await fileRes.json()
      const functions = await functionsRes.json()
      const classes = await classesRes.json()
      
      setSelectedFileData({ file, functions, classes })
    } catch (e) {
      console.error('Failed to fetch file details', e)
    }
  }

  const togglePath = (path: string) => {
    const newExpanded = new Set(expanded)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpanded(newExpanded)
  }

  const getFilePathParts = (fullPath: string) => {
    const parts = fullPath.split('/').filter(Boolean)
    const result = []
    
    for (let i = 0; i < parts.length; i++) {
      const path = parts.slice(0, i + 1).join('/')
      const isFolder = i < parts.length - 1 || !parts[i].includes('.')
      result.push({
        name: parts[i],
        path: path,
        isFolder: isFolder,
        isLast: i === parts.length - 1
      })
    }
    
    return result
  }

  useEffect(() => {
    fetchFiles()
  }, [])

  useEffect(() => {
    if (selectedFileId) {
      fetchFileDetails(selectedFileId)
    }
  }, [selectedFileId])

  const buildTree = () => {
    const tree: { [key: string]: any[] } = {}
    const filesByFolder: { [key: string]: FileInfo[] } = {}
    
    for (const file of files) {
      const parts = getFilePathParts(file.path)
      const folderPath = parts.slice(0, -1).map(p => p.path).join('/')
      
      if (!filesByFolder[folderPath]) {
        filesByFolder[folderPath] = []
      }
      filesByFolder[folderPath].push(file)
    }
    
    return filesByFolder
  }

  const filesByFolder = buildTree()

  return (
    <div className="flex h-full">
      <div className="w-80 bg-slate-800 border-r border-slate-700 overflow-y-auto">
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <FolderTree className="w-5 h-5" />
            File Explorer
          </h2>
        </div>
        <div className="p-4">
          {files.map((file) => (
            <button
              key={file.id}
              onClick={() => setSelectedFileId(file.id)}
              className={`w-full text-left p-3 rounded-lg mb-2 flex items-center gap-3 transition-all ${
                selectedFileId === file.id
                  ? 'bg-sky-600 text-white'
                  : 'hover:bg-slate-700 text-gray-300'
              }`}
            >
              <FileCode className="w-5 h-5 flex-shrink-0" />
              <span className="truncate text-sm">
                {file.path.split('/').pop()}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 p-6 overflow-y-auto">
        {selectedFileData ? (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">
                {selectedFileData.file.path?.split('/').pop()}
              </h2>
              <p className="text-gray-400 text-sm">{selectedFileData.file.path}</p>
            </div>

            {selectedFileData.classes?.classes?.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <Box className="w-5 h-5 text-green-400" />
                  Classes ({selectedFileData.classes.classes.length})
                </h3>
                <div className="space-y-2">
                  {selectedFileData.classes.classes.map((cls: ClassInfo, idx: number) => (
                    <div key={idx} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                      <h4 className="font-medium text-white">{cls.name}</h4>
                      {cls.extends && (
                        <p className="text-sm text-gray-400 mt-1">Extends: {cls.extends}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedFileData.functions?.functions?.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <Code2 className="w-5 h-5 text-purple-400" />
                  Functions ({selectedFileData.functions.functions.length})
                </h3>
                <div className="space-y-2">
                  {selectedFileData.functions.functions.map((func: FunctionInfo, idx: number) => (
                    <div key={idx} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                      <h4 className="font-medium text-white">
                        {func.name}()
                        {func.return_type && (
                          <span className="text-sky-400 text-sm ml-1">→ {func.return_type}</span>
                        )}
                      </h4>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!selectedFileData.classes?.classes?.length &&
             !selectedFileData.functions?.functions?.length && (
              <div className="text-center py-12 text-gray-500">
                No classes or functions found
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            Select a file to view details
          </div>
        )}
      </div>
    </div>
  )
}
