import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export async function sendMessage(message, sessionId) {
  const { data } = await api.post('/chat', { message, session_id: sessionId })
  return data // { answer, sources, session_id }
}

export async function fetchDocuments() {
  const { data } = await api.get('/admin/documents')
  return data
}

export async function fetchStats() {
  const { data } = await api.get('/admin/stats')
  return data
}

export async function triggerSync() {
  const { data } = await api.post('/admin/ingest/trigger')
  return data
}

export async function uploadFile(file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/admin/ingest/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

export async function deleteDocument(docId) {
  const { data } = await api.delete(`/admin/documents/${docId}`)
  return data
}
