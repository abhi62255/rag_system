import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { ChevronDown, ChevronUp, FileText, AlertCircle } from 'lucide-react'

const DOC_ICONS = {
  pdf:  '📄',
  docx: '📝',
  html: '🌐',
  txt:  '📃',
}

function SourceBadge({ source }) {
  return (
    <span className="inline-flex items-center gap-1 bg-surface-800 border border-slate-700 rounded-full px-2 py-0.5 text-xs text-slate-400 font-mono">
      {DOC_ICONS[source.doc_type] || '📄'}
      <span className="text-slate-300">{source.filename}</span>
      <span className="text-slate-600">#{source.chunk_index}</span>
      <span className="text-emerald-500/80">{(source.similarity * 100).toFixed(0)}%</span>
    </span>
  )
}

function SourcesSection({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-3 border-t border-slate-700/50 pt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors group"
      >
        <FileText size={12} className="group-hover:text-brand-400 transition-colors" />
        <span>{sources.length} source{sources.length > 1 ? 's' : ''} used</span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {open && (
        <div className="mt-2 flex flex-wrap gap-1.5 animate-fade-in">
          {sources.map((s, i) => (
            <SourceBadge key={i} source={s} />
          ))}
        </div>
      )}
    </div>
  )
}

const markdownComponents = {
  code({ node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '')
    return !inline && match ? (
      <SyntaxHighlighter
        style={oneDark}
        language={match[1]}
        PreTag="div"
        customStyle={{ borderRadius: '0.5rem', fontSize: '0.8rem', margin: '0.5rem 0' }}
        {...props}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    ) : (
      <code className={className} {...props}>{children}</code>
    )
  },
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isError = message.isError

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 animate-slide-up">
        <div className="max-w-[75%] bg-brand-500 rounded-2xl rounded-tr-sm px-4 py-3 shadow-lg">
          <div className="prose-rag-user text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          </div>
          <p className="text-indigo-300/60 text-[10px] mt-1.5 text-right">
            {message.timestamp?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-4 animate-slide-up">
      <div className="flex gap-3 max-w-[85%]">
        {/* Avatar */}
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center mt-0.5">
          <span className="text-xs">✦</span>
        </div>

        <div className="flex-1">
          <div
            className={`rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm ${
              isError
                ? 'bg-red-900/30 border border-red-800/50'
                : 'bg-surface-800 border border-slate-700/50'
            }`}
          >
            {isError && (
              <div className="flex items-center gap-1.5 text-red-400 text-xs mb-2">
                <AlertCircle size={12} />
                <span>Error</span>
              </div>
            )}
            <div className="prose-rag text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {message.content}
              </ReactMarkdown>
            </div>
            <SourcesSection sources={message.sources} />
          </div>
          <p className="text-slate-600 text-[10px] mt-1 ml-1">
            {message.timestamp?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    </div>
  )
}
