import { useState, useCallback, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { sendMessage } from '../api/chat'

const SESSION_KEY = 'rag_session_id'

function getOrCreateSessionId() {
  let id = sessionStorage.getItem(SESSION_KEY)
  if (!id) {
    id = uuidv4()
    sessionStorage.setItem(SESSION_KEY, id)
  }
  return id
}

export function useChat() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const sessionId = useRef(getOrCreateSessionId())

  const send = useCallback(async (text) => {
    if (!text.trim() || isLoading) return

    const userMsg = {
      id: uuidv4(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)
    setError(null)

    try {
      const response = await sendMessage(text, sessionId.current)
      const assistantMsg = {
        id: uuidv4(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources || [],
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const errText = err.response?.data?.detail || err.message || 'Unknown error'
      setError(errText)
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          role: 'assistant',
          content: `Error: ${errText}`,
          sources: [],
          isError: true,
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [isLoading])

  const clearHistory = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY)
    sessionId.current = getOrCreateSessionId()
    setMessages([])
    setError(null)
  }, [])

  return { messages, isLoading, error, send, clearHistory, sessionId: sessionId.current }
}
