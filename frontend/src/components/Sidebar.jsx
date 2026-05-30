import React, { useState, useCallback, useRef } from 'react'
import {
  RefreshCw, Upload, Trash2, FileText, Globe, File,
  CheckCircle, XCircle, AlertCircle, Database, ChevronRight,
} from 'lucide-react'
import { fetchDocuments, fetchStats, triggerSync, uploadFile, deleteDocument } from '../api/chat'

const STATUS_STYLES = {
  active:  { icon: CheckCircle,  color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  deleted: { icon: XCircle,      color: 'text-slate-600',   bg: 'bg-slate-800' },
  failed:  { icon: AlertCircle,  color: 'text-red-500',     bg: 'bg-red-500/10' },
}

const DOC_TYPE_ICON = {
  pdf:  { icon: FileText, color: 'text-red-400' },
  docx: { icon: FileText, color: 'text-blue-400' },
  html: { icon: Globe,    color: 'text-green-400' },
  txt:  { icon: File,     color: 'text-slate-400' },
}

function DocRow({ doc, onDelete }) {
  const [confirming, setConfirming] = useState(false)
  const statusCfg = STATUS_STYLES[doc.status] || STATUS_STYLES.active
  const StatusIcon = statusCfg.icon
  const typeCfg = DOC_TYPE_ICON[doc.doc_type] || DOC_TYPE_ICON.txt
  const TypeIcon = typeCfg.icon

  const handleDelete = async () => {
    if (!confirming) { setConfirming(true); return }
    await onDelete(doc.id)
    setConfirming(false)
  }

  return (
    <div className="flex items-center gap-2 group px-3 py-2 rounded-lg hover:bg-surface-850 transition-colors">
      <TypeIcon size={14} className={`flex-shrink-0 ${typeCfg.color}`} />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-slate-300 truncate font-medium">{doc.filename}</p>
        <p className="text-[10px] text-slate-600">v{doc.version} · {doc.chunk_count} chunks</p>
      </div>
      <StatusIcon size={11} className={`flex-shrink-0 ${statusCfg.color}`} />
      {doc.status !== 'deleted' && (
        <button
          onClick={handleDelete}
          className={`flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-500/10 ${
            confirming ? 'opacity-100 text-red-400' : 'text-slate-600 hover:text-red-400'
          }`}
          title={confirming ? 'Click again to confirm' : 'Delete document'}
        >
          <Trash2 size={11} />
        </button>
      )}
    </div>
  )
}

export default function Sidebar({ onClearHistory }) {
  const [docs, setDocs] = useState([])
  const [stats, setStats] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [lastSync, setLastSync] = useState(null)
  const [collapsed, setCollapsed] = useState(false)
  const fileInputRef = useRef(null)

  const loadData = useCallback(async () => {
    try {
      const [docsData, statsData] = await Promise.all([fetchDocuments(), fetchStats()])
      setDocs(docsData)
      setStats(statsData)
    } catch (e) {
      console.error('Failed to load sidebar data:', e)
    }
  }, [])

  React.useEffect(() => { loadData() }, [loadData])

  const handleSync = async () => {
    setSyncing(true)
    try {
      const result = await triggerSync()
      setLastSync(result)
      await loadData()
    } catch (e) {
      console.error('Sync failed:', e)
    } finally {
      setSyncing(false)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadProgress(0)
    try {
      await uploadFile(file, setUploadProgress)
      await loadData()
    } catch (e) {
      console.error('Upload failed:', e)
    } finally {
      setUploading(false)
      setUploadProgress(0)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDelete = async (docId) => {
    try {
      await deleteDocument(docId)
      await loadData()
    } catch (e) {
      console.error('Delete failed:', e)
    }
  }

  const activeDocs = docs.filter((d) => d.status === 'active')
  const failedDocs = docs.filter((d) => d.status === 'failed')

  if (collapsed) {
    return (
      <div className="w-12 flex flex-col items-center bg-surface-850 border-r border-slate-800 py-4 gap-3">
        <button onClick={() => setCollapsed(false)} className="text-slate-500 hover:text-slate-300 p-2 rounded-lg hover:bg-surface-800 transition-colors" title="Expand sidebar">
          <ChevronRight size={16} />
        </button>
        <div className="text-xs writing-mode-vertical text-slate-600 mt-4">Documents</div>
      </div>
    )
  }

  return (
    <aside className="w-72 flex flex-col bg-surface-850 border-r border-slate-800 shrink-0">
      {/* Header */}
      <div className="px-4 pt-5 pb-4 border-b border-slate-800">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-brand-500 flex items-center justify-center text-[10px] font-bold text-white">R</div>
            <h1 className="text-sm font-semibold text-slate-200">RAG Assistant</h1>
          </div>
          <button
            onClick={() => setCollapsed(true)}
            className="text-slate-600 hover:text-slate-400 p-1 rounded transition-colors"
            title="Collapse sidebar"
          >
            <ChevronRight size={14} className="rotate-180" />
          </button>
        </div>
        <p className="text-[10px] text-slate-600 ml-8">Powered by Gemini + ChromaDB</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="px-4 py-3 border-b border-slate-800 grid grid-cols-3 gap-2">
          {[
            { label: 'Docs', value: stats.active_documents },
            { label: 'Chunks', value: stats.total_chunks },
            { label: 'Failed', value: stats.active_documents - stats.active_documents + (docs.filter(d => d.status === 'failed').length) },
          ].map(({ label, value }) => (
            <div key={label} className="bg-surface-900 rounded-lg px-2 py-1.5 text-center">
              <p className="text-base font-semibold text-slate-200">{value}</p>
              <p className="text-[10px] text-slate-600">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="px-4 py-3 border-b border-slate-800 flex gap-2">
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex-1 flex items-center justify-center gap-1.5 text-xs bg-surface-900 hover:bg-slate-800 border border-slate-700 hover:border-slate-600 text-slate-300 rounded-lg px-3 py-2 transition-all disabled:opacity-60"
        >
          <RefreshCw size={12} className={syncing ? 'animate-spin' : ''} />
          {syncing ? 'Syncing…' : 'Sync Now'}
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="flex-1 flex items-center justify-center gap-1.5 text-xs bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/30 hover:border-brand-500/50 text-brand-400 rounded-lg px-3 py-2 transition-all disabled:opacity-60"
        >
          <Upload size={12} />
          {uploading ? `${uploadProgress}%` : 'Upload'}
        </button>
        <input ref={fileInputRef} type="file" accept=".pdf,.docx,.doc,.html,.htm,.txt,.md" className="hidden" onChange={handleUpload} />
      </div>

      {/* Last sync info */}
      {lastSync && (
        <div className="px-4 py-2 border-b border-slate-800 text-[10px] text-slate-600 space-y-0.5">
          <p>Last sync: +{lastSync.new} new · ~{lastSync.modified} updated · -{lastSync.deleted} removed</p>
        </div>
      )}

      {/* Document list */}
      <div className="flex-1 overflow-y-auto py-2">
        <p className="px-4 py-1 text-[10px] font-medium text-slate-600 uppercase tracking-wider">
          Active Documents ({activeDocs.length})
        </p>
        {activeDocs.length === 0 ? (
          <div className="px-4 py-6 text-center">
            <Database size={20} className="text-slate-700 mx-auto mb-2" />
            <p className="text-xs text-slate-600">No documents ingested yet.<br />Upload a file or drop one in the watch folder.</p>
          </div>
        ) : (
          activeDocs.map((doc) => (
            <DocRow key={doc.id} doc={doc} onDelete={handleDelete} />
          ))
        )}

        {failedDocs.length > 0 && (
          <>
            <p className="px-4 pt-3 pb-1 text-[10px] font-medium text-red-700 uppercase tracking-wider">
              Failed ({failedDocs.length})
            </p>
            {failedDocs.map((doc) => (
              <DocRow key={doc.id} doc={doc} onDelete={handleDelete} />
            ))}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-800">
        <button
          onClick={onClearHistory}
          className="w-full text-xs text-slate-600 hover:text-slate-400 transition-colors py-1"
        >
          Clear conversation history
        </button>
      </div>
    </aside>
  )
}
