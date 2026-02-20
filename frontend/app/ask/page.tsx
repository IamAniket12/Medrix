'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  PaperAirplaneIcon, 
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'
import { CheckCircleIcon } from '@heroicons/react/24/solid'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  citations?: Citation[]
}

interface Citation {
  source_id: string
  type: string
  title?: string
  date?: string
  document_type?: string
  event_type?: string
  similarity_score: number
  metadata?: {
    document_id?: string
    filename?: string
    original_name?: string
    document_date?: string
    document_type?: string
  }
}

interface ChatResponse {
  answer: string
  citations: Citation[]
  context_used: any[]
  confidence: number
  timestamp: string
  disclaimer: string
}

export default function AskAIPage() {
  const router = useRouter()
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [previewDoc, setPreviewDoc] = useState<{ id: string; name: string; url: string } | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Handle document preview
  const openDocumentPreview = async (docId: string, docName: string) => {
    setLoadingPreview(true)
    setShowPreview(true)
    setPreviewDoc({ id: docId, name: docName, url: '' })

    try {
      // Fetch document details to get file path
      const detailsRes = await fetch(`http://localhost:8000/api/v1/clinical/documents/demo_user_001/${docId}`)
      if (!detailsRes.ok) throw new Error('Failed to fetch document details')
      
      const docDetails = await detailsRes.json()
      const filePath = docDetails.document.file_path

      // Get signed URL for the file
      const urlRes = await fetch(`http://localhost:8000/api/v1/files/view/${encodeURIComponent(filePath)}`)
      if (!urlRes.ok) throw new Error('Failed to fetch file URL')
      
      const urlData = await urlRes.json()
      setPreviewDoc({ id: docId, name: docName, url: urlData.url })
    } catch (error) {
      console.error('Error loading document preview:', error)
      setPreviewDoc(prev => prev ? { ...prev, url: 'error' } : null)
    } finally {
      setLoadingPreview(false)
    }
  }

  const closePreview = () => {
    setShowPreview(false)
    setPreviewDoc(null)
    setLoadingPreview(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    }

    // Add user message immediately
    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setError(null)

    try {
      // Call backend RAG endpoint
      const response = await fetch('http://localhost:8000/api/v1/chat/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: 'demo_user_001',
          question: inputValue,
          conversation_history: messages.slice(-5), // Last 5 messages for context
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: ChatResponse = await response.json()

      // Add AI response
      const aiMessage: Message = {
        role: 'assistant',
        content: data.answer,
        timestamp: new Date(data.timestamp),
        citations: data.citations,
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (err) {
      console.error('Error:', err)
      setError('Failed to get response. Please try again.')
      
      // Add error message
      const errorMessage: Message = {
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your question. Please try again or rephrase your question.',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      hour12: true,
    }).format(date)
  }

  const getCitationIcon = (type: string) => {
    switch (type) {
      case 'document':
        return <DocumentTextIcon className="h-4 w-4" />
      case 'timeline_event':
        return <ClockIcon className="h-4 w-4" />
      default:
        return <CheckCircleIcon className="h-4 w-4" />
    }
  }

  const formatCitationDate = (dateStr?: string) => {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      }).format(date)
    } catch {
      return dateStr
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-cyan-50">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="flex items-center justify-center mb-4">
            <SparklesIcon className="h-10 w-10 text-blue-600 mr-3" />
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
              Ask AI
            </h1>
          </div>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Ask questions about your medical history. I'll search through your records and provide accurate answers with citations.
          </p>
          
          {/* Medical Disclaimer Banner */}
          <div className="mt-6 bg-amber-50 border-l-4 border-amber-400 p-4 rounded-r-lg max-w-3xl mx-auto">
            <div className="flex items-start">
              <ExclamationTriangleIcon className="h-5 w-5 text-amber-400 mt-0.5 mr-3 flex-shrink-0" />
              <div className="text-left">
                <p className="text-sm text-amber-800 font-medium">Medical Information Disclaimer</p>
                <p className="text-xs text-amber-700 mt-1">
                  This AI assistant provides information based on your medical records only. 
                  It does not provide diagnoses or medical advice. Always consult your healthcare provider for medical decisions.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Container */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
          {/* Messages Area */}
          <div className="h-[600px] overflow-y-auto p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <SparklesIcon className="h-16 w-16 text-gray-300 mb-4" />
                <h3 className="text-xl font-semibold text-gray-700 mb-2">
                  Start a Conversation
                </h3>
                <p className="text-gray-500 max-w-md mb-6">
                  Ask me anything about your medical history, medications, conditions, or test results.
                </p>
                
                {/* Example Questions */}
                <div className="space-y-2 max-w-lg w-full">
                  <p className="text-sm text-gray-600 font-medium mb-3">Example questions:</p>
                  {[
                    'What medications am I currently taking?',
                    'Show me my recent lab results',
                    'What is my blood pressure history?',
                    'Do I have any allergies on record?',
                  ].map((example, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInputValue(example)}
                      className="w-full text-left px-4 py-3 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm transition-colors"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((message, idx) => (
                  <div
                    key={idx}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] ${
                        message.role === 'user'
                          ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      } rounded-2xl px-5 py-4 shadow-sm`}
                    >
                      {/* Message Content */}
                      <div className="whitespace-pre-wrap break-words">
                        {message.content}
                      </div>

                      {/* Citations */}
                      {message.citations && message.citations.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-gray-300 space-y-2">
                          <p className="text-xs font-semibold text-gray-700 mb-2">
                            📚 Sources Referenced:
                          </p>
                          {message.citations.map((citation, citIdx) => {
                            // Only show document citations (clickable)
                            if (citation.type === 'document') {
                              const docId = citation.metadata?.document_id || citation.source_id
                              const docName = citation.metadata?.original_name || citation.metadata?.filename || 'Medical Document'
                              
                              return (
                                <button
                                  key={citIdx}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    openDocumentPreview(docId, docName)
                                  }}
                                  className="w-full bg-white rounded-lg p-3 text-xs border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-all text-left group"
                                >
                                  <div className="flex items-start">
                                    <div className="text-blue-600 mr-2 mt-0.5 group-hover:scale-110 transition-transform">
                                      <DocumentTextIcon className="h-4 w-4" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                      <p className="font-semibold text-gray-900 group-hover:text-blue-700 truncate">
                                        {docName}
                                      </p>
                                      <div className="flex items-center gap-2 mt-1 text-gray-600 flex-wrap">
                                        {citation.metadata?.document_date && (
                                          <span className="text-xs">
                                            📅 {formatCitationDate(citation.metadata.document_date)}
                                          </span>
                                        )}
                                        {citation.metadata?.document_type && (
                                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded capitalize">
                                            {citation.metadata.document_type.replace(/_/g, ' ')}
                                          </span>
                                        )}
                                      </div>
                                      <div className="mt-1 text-xs text-gray-500 group-hover:text-blue-600">
                                        Click to preview document →
                                      </div>
                                    </div>
                                  </div>
                                </button>
                              )
                            }
                            // Skip non-document citations (they're internal/structured data)
                            return null
                          })}
                        </div>
                      )}

                      {/* Timestamp */}
                      <div
                        className={`text-xs mt-2 ${
                          message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                        }`}
                      >
                        {formatTime(message.timestamp)}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Loading Indicator */}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-2xl px-5 py-4 shadow-sm">
                      <div className="flex items-center space-x-2">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                        <span className="text-sm text-gray-600">Searching your records...</span>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 bg-gray-50 p-4">
            <form onSubmit={handleSubmit} className="flex items-end gap-3">
              <div className="flex-1">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about your medical history..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={2}
                  disabled={isLoading}
                />
                <p className="text-xs text-gray-500 mt-1 px-1">
                  Press Enter to send, Shift+Enter for new line
                </p>
              </div>
              <button
                type="submit"
                disabled={!inputValue.trim() || isLoading}
                className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white p-4 rounded-xl hover:from-blue-700 hover:to-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl"
              >
                <PaperAirplaneIcon className="h-5 w-5" />
              </button>
            </form>

            {error && (
              <div className="mt-3 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* Footer Safety Notice */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            🔒 Your medical information is private and secure. This AI assistant only accesses your uploaded medical records.
          </p>
          <p className="text-xs text-gray-500 mt-1">
            ⚠️ Always verify important medical information with your healthcare provider.
          </p>
        </div>
      </div>

      {/* Document Preview Modal */}
      {showPreview && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={closePreview}
        >
          <div 
            className="bg-white rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <DocumentTextIcon className="h-6 w-6 text-blue-600" />
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {previewDoc?.name || 'Document Preview'}
                  </h3>
                  <p className="text-sm text-gray-500">Medical Document</p>
                </div>
              </div>
              <button
                onClick={closePreview}
                className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-lg transition-colors"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-auto p-6 bg-gray-50">
              {loadingPreview ? (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mb-4"></div>
                    <p className="text-gray-600">Loading document...</p>
                  </div>
                </div>
              ) : previewDoc?.url === 'error' ? (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
                    <p className="text-gray-900 font-semibold mb-2">Failed to load document</p>
                    <p className="text-gray-600 text-sm">Please try again later</p>
                  </div>
                </div>
              ) : previewDoc?.url ? (
                <div className="flex justify-center">
                  <img
                    src={previewDoc.url}
                    alt={previewDoc.name}
                    className="max-w-full h-auto rounded-lg shadow-lg"
                    style={{ maxHeight: 'calc(90vh - 200px)' }}
                  />
                </div>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-white">
              <button
                onClick={closePreview}
                className="px-6 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => router.push(`/documents/${previewDoc?.id}`)}
                className="px-6 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white rounded-lg font-medium transition-all shadow-lg hover:shadow-xl flex items-center gap-2"
              >
                <span>View Full Details</span>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
