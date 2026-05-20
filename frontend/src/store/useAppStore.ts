import { create } from 'zustand'

interface AppState {
  currentPage: 'dashboard' | 'explorer' | 'graph' | 'search' | 'logs'
  setCurrentPage: (page: AppState['currentPage']) => void
  selectedFileId: number | null
  setSelectedFileId: (id: number | null) => void
  isWatching: boolean
  setIsWatching: (watching: boolean) => void
  updateLogs: Array<{
    timestamp: number
    type: string
    status: string
    file?: string
    duration?: number
    error?: string
  }>
  addUpdateLog: (log: any) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentPage: 'dashboard',
  setCurrentPage: (page) => set({ currentPage: page }),
  selectedFileId: null,
  setSelectedFileId: (id) => set({ selectedFileId: id }),
  isWatching: false,
  setIsWatching: (watching) => set({ isWatching: watching }),
  updateLogs: [],
  addUpdateLog: (log) => set((state) => ({
    updateLogs: [...state.updateLogs.slice(-99), log]
  }))
}))
