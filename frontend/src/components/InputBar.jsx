import React, { useState, useRef, useEffect } from 'react'
import { Send, Square } from 'lucide-react'

export default function InputBar({ onSend, isLoading, disabled }) {
  const [text, setText] = useState('')
  const textareaRef = useRef(null)

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [isLoading])

  // Auto-grow textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
  }, [text])

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    onSend(trimmed)
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="px-4 pb-4 pt-2">
      <div className="flex items-end gap-2 bg-surface-800 border border-slate-700/60 focus-within:border-brand-500/50 rounded-2xl px-4 py-3 transition-colors shadow-lg">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your documents… (Shift+Enter for newline)"
          rows={1}
          disabled={disabled}
          className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 text-sm resize-none outline-none leading-relaxed min-h-[22px] max-h-[160px] disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={!text.trim() || isLoading}
          className="flex-shrink-0 w-8 h-8 rounded-xl bg-brand-500 hover:bg-brand-400 disabled:bg-slate-700 disabled:text-slate-500 text-white flex items-center justify-center transition-all disabled:cursor-not-allowed mb-0.5 shadow-md"
          title="Send (Enter)"
        >
          {isLoading
            ? <Square size={13} className="text-slate-400 fill-current" />
            : <Send size={13} />
          }
        </button>
      </div>
      <p className="text-center text-slate-700 text-[10px] mt-1.5">
        Answers are grounded in your documents · Enter to send · Shift+Enter for newline
      </p>
    </div>
  )
}
