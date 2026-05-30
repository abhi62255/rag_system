import React from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import { useChat } from './hooks/useChat'

export default function App() {
  const { messages, isLoading, send, clearHistory } = useChat()

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-900">
      {/* Left Sidebar */}
      <Sidebar onClearHistory={clearHistory} />

      {/* Main Chat Area */}
      <main className="flex flex-col flex-1 min-w-0 h-full">
        {/* Top bar */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-surface-900 shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">Knowledge Chat</h2>
            <p className="text-[10px] text-slate-600">Stateful · Gemini 1.5-flash · Semantic retrieval</p>
          </div>
          {messages.length > 0 && (
            <span className="text-[10px] text-slate-600 bg-surface-800 border border-slate-700 rounded-full px-2 py-0.5">
              {messages.length} message{messages.length > 1 ? 's' : ''}
            </span>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <ChatWindow messages={messages} isLoading={isLoading} />
        </div>

        {/* Input */}
        <InputBar onSend={send} isLoading={isLoading} />
      </main>
    </div>
  )
}
