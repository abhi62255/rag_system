import React, { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4 animate-fade-in">
      <div className="flex gap-3 max-w-[85%]">
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
          <span className="text-xs">✦</span>
        </div>
        <div className="bg-surface-800 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3">
          <div className="flex gap-1 items-center h-4">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse-dot"
                style={{ animationDelay: `${i * 0.16}s` }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 select-none">
      <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-4 text-3xl">
        ✦
      </div>
      <h2 className="text-lg font-semibold text-slate-300 mb-2">Knowledge Assistant</h2>
      <p className="text-slate-500 text-sm max-w-xs leading-relaxed">
        Ask anything about the documents in your knowledge base. I'll find relevant information and cite my sources.
      </p>
      <div className="mt-6 grid grid-cols-1 gap-2 w-full max-w-sm">
        {[
          'Summarize the key points from the latest report',
          'What does the documentation say about authentication?',
          'Compare the findings across all uploaded documents',
        ].map((q) => (
          <button
            key={q}
            className="text-left text-xs text-slate-400 bg-surface-800/60 hover:bg-surface-800 border border-slate-700/50 hover:border-slate-600 rounded-xl px-3 py-2.5 transition-all cursor-default"
          >
            "{q}"
          </button>
        ))}
      </div>
    </div>
  )
}

export default function ChatWindow({ messages, isLoading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  if (messages.length === 0 && !isLoading) {
    return <EmptyState />
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-1">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {isLoading && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  )
}
