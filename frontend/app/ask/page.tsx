'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'

const API_BASE_URL = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1`
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
  const [user, setUser] = useState<{ id: string; name: string; email: string } | null>(null)
  const [authChecked, setAuthChecked] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auth check
  useEffect(() => {
    const raw = localStorage.getItem('medrix_user')
    setUser(raw ? JSON.parse(raw) : null)
    setAuthChecked(true)
  }, [])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-focus input on mount
  useEffect(() => {
    if (authChecked && user) inputRef.current?.focus()
  }, [authChecked, user])

  // Handle document preview
  const openDocumentPreview = async (docId: string, docName: string) => {
    setLoadingPreview(true)
    setShowPreview(true)
    setPreviewDoc({ id: docId, name: docName, url: '' })

    try {
      // Fetch document details to get file path
      const detailsRes = await fetch(`${API_BASE_URL}/clinical/documents/${user?.id || 'demo_user_001'}/${docId}`)
      if (!detailsRes.ok) throw new Error('Failed to fetch document details')
      
      const docDetails = await detailsRes.json()
      const filePath = docDetails.document.file_path

      // Use the file view URL directly (backend returns 302 redirect to signed URL)
      const viewUrl = `${API_BASE_URL}/files/view/${encodeURIComponent(filePath)}`
      setPreviewDoc({ id: docId, name: docName, url: viewUrl })
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
      const response = await fetch(`${API_BASE_URL}/chat/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user?.id || 'demo_user_001',
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

  if (!authChecked) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: '40px', height: '40px', border: '3px solid rgba(249,115,22,0.2)', borderTop: '3px solid #f97316', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        <style jsx>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  if (!user) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
        <div style={{ maxWidth: '440px', width: '100%', background: '#ffffff', border: '1.5px solid rgba(0,0,0,0.06)', borderRadius: '24px', padding: '48px 40px', textAlign: 'center', boxShadow: '0 8px 40px rgba(0,0,0,0.07)' }}>
          <div style={{ fontSize: '64px', marginBottom: '20px' }}>🤖</div>
          <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#1c1917', marginBottom: '10px' }}>Sign in to use MediBot</h2>
          <p style={{ fontSize: '15px', color: '#78716c', marginBottom: '32px', lineHeight: 1.6 }}>MediBot uses your personal medical history to answer questions. Please sign in to continue.</p>
          <button onClick={() => router.push('/signin')} style={{ padding: '13px 32px', background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)', border: 'none', borderRadius: '12px', color: 'white', fontSize: '15px', fontWeight: 700, cursor: 'pointer', boxShadow: '0 4px 16px rgba(249,115,22,0.3)', width: '100%' }}>
            Sign In
          </button>
          <p style={{ marginTop: '16px', fontSize: '13px', color: '#a8a29e' }}>Don&apos;t have an account? <button onClick={() => router.push('/signin')} style={{ background: 'none', border: 'none', color: '#f97316', fontWeight: 700, cursor: 'pointer', fontSize: '13px', padding: 0 }}>Create one</button></p>
        </div>
      </div>
    )
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #fffbf7 0%, #fef3ec 40%, #fff6f0 70%, #fffbf7 100%)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background Decorations */}
      <div style={{
        position: 'absolute',
        top: '15%',
        right: '5%',
        width: '450px',
        height: '450px',
        background: 'radial-gradient(circle, rgba(167,139,250,0.14) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(70px)',
        pointerEvents: 'none',
      }}></div>
      <div style={{
        position: 'absolute',
        bottom: '15%',
        left: '5%',
        width: '400px',
        height: '400px',
        background: 'radial-gradient(circle, rgba(249,115,22,0.1) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(60px)',
        pointerEvents: 'none',
      }}></div>

      <div style={{
        maxWidth: '1100px',
        margin: '0 auto',
        padding: '40px 24px',
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px' }}>
            <SparklesIcon style={{ width: '36px', height: '36px', color: '#8b5cf6', marginRight: '12px' }} />
            <h1 style={{
              fontSize: '42px',
              fontWeight: '900',
              background: 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              letterSpacing: '-0.02em',
              margin: 0,
            }}>
              MediBot
            </h1>
          </div>
          <p style={{
            fontSize: '16px',
            color: '#78716c',
            maxWidth: '650px',
            margin: '0 auto 20px',
            lineHeight: '1.6',
          }}>
            Your intelligent medical assistant. Ask questions about your health records, and I'll provide accurate answers with source citations.
          </p>
          
          {/* Medical Disclaimer Banner */}
          <div style={{
            background: 'rgba(251, 191, 36, 0.1)',
            border: '1px solid rgba(251, 191, 36, 0.3)',
            borderRadius: '12px',
            padding: '14px 18px',
            maxWidth: '700px',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'flex-start',
            textAlign: 'left',
          }}>
            <ExclamationTriangleIcon style={{ width: '20px', height: '20px', color: '#fbbf24', marginRight: '12px', flexShrink: 0, marginTop: '2px' }} />
            <div>
              <p style={{ fontSize: '13px', color: '#fbbf24', fontWeight: '600', margin: 0 }}>Medical Information Disclaimer</p>
              <p style={{ fontSize: '12px', color: 'rgba(251, 191, 36, 0.9)', margin: '4px 0 0' }}>
                This AI provides information based on your records only. It does not provide diagnoses or medical advice. Always consult your healthcare provider.
              </p>
            </div>
          </div>
        </div>

        {/* Chat Container */}
        <div style={{
          background: '#ffffff',
          borderRadius: '24px',
          border: '1.5px solid rgba(0,0,0,0.06)',
          overflow: 'hidden',
          boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
        }}>
          {/* Messages Area */}
          <div style={{
            height: '600px',
            overflowY: 'auto',
            padding: '32px',
            display: 'flex',
            flexDirection: 'column',
            gap: '24px',
          }}>
            {messages.length === 0 ? (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                textAlign: 'center',
              }}>
                <SparklesIcon style={{ width: '64px', height: '64px', color: 'rgba(167,139,250,0.4)', marginBottom: '20px' }} />
                <h3 style={{
                  fontSize: '24px',
                  fontWeight: '700',
                  color: '#1c1917',
                  marginBottom: '12px',
                }}>
                  Start a Conversation
                </h3>
                <p style={{
                  fontSize: '15px',
                  color: '#78716c',
                  maxWidth: '500px',
                  marginBottom: '32px',
                }}>
                  Ask me anything about your medical history, medications, conditions, or test results.
                </p>
                
                {/* Example Questions */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '550px', width: '100%' }}>
                  <p style={{ fontSize: '13px', color: '#a8a29e', fontWeight: '600', marginBottom: '8px' }}>
                    Example questions:
                  </p>
                  {[
                    'What medications am I currently taking?',
                    'Show me my recent lab results',
                    'What is my blood pressure history?',
                    'Do I have any allergies on record?',
                  ].map((example, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInputValue(example)}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '14px 18px',
                        background: '#fdfbf8',
                        border: '1.5px solid rgba(167,139,250,0.25)',
                        borderRadius: '12px',
                        color: '#1c1917',
                        fontSize: '14px',
                        cursor: 'pointer',
                        transition: 'all 0.3s ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(167,139,250,0.1)'
                        e.currentTarget.style.borderColor = 'rgba(167,139,250,0.5)'
                        e.currentTarget.style.transform = 'translateX(4px)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = '#fdfbf8'
                        e.currentTarget.style.borderColor = 'rgba(167,139,250,0.25)'
                        e.currentTarget.style.transform = 'translateX(0)'
                      }}
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
                    style={{
                      display: 'flex',
                      justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    <div
                      style={{
                        maxWidth: '75%',
                        background: message.role === 'user'
                          ? 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)'
                          : '#f9f5ff',
                        backdropFilter: 'none',
                        border: message.role === 'assistant' ? '1.5px solid rgba(167,139,250,0.15)' : 'none',
                        borderRadius: '18px',
                        padding: '18px 22px',
                        boxShadow: message.role === 'user' 
                          ? '0 4px 16px rgba(139, 92, 246, 0.3)'
                          : '0 2px 12px rgba(167,139,250,0.08)',
                      }}
                    >
                      {/* Message Content */}
                      <div style={{
                        color: message.role === 'user' ? '#fff' : '#1c1917',
                        fontSize: '15px',
                        lineHeight: '1.6',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}>
                        {message.content}
                      </div>

                      {/* Citations */}
                      {message.citations && message.citations.length > 0 && (
                        <div style={{
                          marginTop: '18px',
                          paddingTop: '18px',
                          borderTop: '1px solid rgba(167,139,250,0.2)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px',
                        }}>
                          <p style={{
                            fontSize: '12px',
                            fontWeight: '600',
                            color: '#78716c',
                            margin: 0,
                          }}>
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
                                  style={{
                                    background: '#ffffff',
                                    border: '1.5px solid rgba(167,139,250,0.2)',
                                    borderRadius: '10px',
                                    padding: '12px',
                                    fontSize: '12px',
                                    textAlign: 'left',
                                    cursor: 'pointer',
                                    transition: 'all 0.3s ease',
                                  }}
                                  onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'rgba(167,139,250,0.08)'
                                    e.currentTarget.style.borderColor = 'rgba(167,139,250,0.5)'
                                    e.currentTarget.style.transform = 'translateY(-2px)'
                                  }}
                                  onMouseLeave={(e) => {
                                    e.currentTarget.style.background = '#ffffff'
                                    e.currentTarget.style.borderColor = 'rgba(167,139,250,0.2)'
                                    e.currentTarget.style.transform = 'translateY(0)'
                                  }}
                                >
                                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                                    <DocumentTextIcon style={{ width: '16px', height: '16px', color: '#8b5cf6', flexShrink: 0, marginTop: '2px' }} />
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                      <p style={{
                                        fontWeight: '600',
                                        color: '#1c1917',
                                        margin: '0 0 4px',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap',
                                      }}>
                                        {docName}
                                      </p>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                        {citation.metadata?.document_date && (
                                          <span style={{ fontSize: '11px', color: '#78716c' }}>
                                            📅 {formatCitationDate(citation.metadata.document_date)}
                                          </span>
                                        )}
                                        {citation.metadata?.document_type && (
                                          <span style={{
                                            fontSize: '10px',
                                            background: 'rgba(139, 92, 246, 0.3)',
                                            color: '#c4b5fd',
                                            padding: '3px 8px',
                                            borderRadius: '6px',
                                            textTransform: 'capitalize',
                                          }}>
                                            {citation.metadata.document_type.replace(/_/g, ' ')}
                                          </span>
                                        )}
                                      </div>
                                      <div style={{
                                        marginTop: '6px',
                                        fontSize: '11px',
                                        color: '#8b5cf6',
                                      }}>
                                        Click to preview document →
                                      </div>
                                    </div>
                                  </div>
                                </button>
                              )
                            }
                            // Skip non-document citations
                            return null
                          })}
                        </div>
                      )}

                      {/* Timestamp */}
                      <div style={{
                        fontSize: '11px',
                        color: 'rgba(100,92,88,0.6)',
                        marginTop: '10px',
                      }}>
                        {formatTime(message.timestamp)}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Loading Indicator */}
                {isLoading && (
                  <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                    <div style={{
                      background: '#f9f5ff',
                      border: '1.5px solid rgba(167,139,250,0.15)',
                      borderRadius: '18px',
                      padding: '18px 22px',
                      boxShadow: '0 2px 12px rgba(167,139,250,0.08)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            background: '#8b5cf6',
                            borderRadius: '50%',
                            animation: 'bounce 1.4s infinite ease-in-out both',
                            animationDelay: '0s',
                          }}></div>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            background: '#8b5cf6',
                            borderRadius: '50%',
                            animation: 'bounce 1.4s infinite ease-in-out both',
                            animationDelay: '0.2s',
                          }}></div>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            background: '#8b5cf6',
                            borderRadius: '50%',
                            animation: 'bounce 1.4s infinite ease-in-out both',
                            animationDelay: '0.4s',
                          }}></div>
                        </div>
                        <span style={{ fontSize: '14px', color: '#78716c' }}>
                          MediBot is analyzing your records...
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div style={{
            borderTop: '1px solid rgba(0,0,0,0.06)',
            background: 'rgba(249,115,22,0.02)',
            padding: '20px 24px',
          }}>
            <form onSubmit={handleSubmit} style={{ display: 'flex', alignItems: 'flex-end', gap: '12px' }}>
              <div style={{ flex: 1 }}>
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about your medical history..."
                  disabled={isLoading}
                  style={{
                    width: '100%',
                    padding: '14px 18px',
                    background: '#fdfaf8',
                    border: '1.5px solid rgba(0,0,0,0.1)',
                    borderRadius: '12px',
                    color: '#1c1917',
                    fontSize: '15px',
                    resize: 'none',
                    outline: 'none',
                    transition: 'all 0.3s ease',
                    fontFamily: 'inherit',
                  }}
                  rows={2}
                  onFocus={(e) => {
                    e.currentTarget.style.background = '#ffffff'
                    e.currentTarget.style.borderColor = 'rgba(167,139,250,0.5)'
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.background = '#fdfaf8'
                    e.currentTarget.style.borderColor = 'rgba(0,0,0,0.1)'
                  }}
                />
                <p style={{
                  fontSize: '11px',
                  color: '#a8a29e',
                  marginTop: '8px',
                  marginLeft: '4px',
                }}>
                  Press Enter to send, Shift+Enter for new line
                </p>
              </div>
              <button
                type="submit"
                disabled={!inputValue.trim() || isLoading}
                style={{
                  background: inputValue.trim() && !isLoading
                    ? 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)'
                    : 'rgba(0,0,0,0.08)',
                  border: 'none',
                  borderRadius: '12px',
                  padding: '16px',
                  cursor: inputValue.trim() && !isLoading ? 'pointer' : 'not-allowed',
                  transition: 'all 0.3s ease',
                  boxShadow: inputValue.trim() && !isLoading
                    ? '0 8px 24px rgba(139, 92, 246, 0.4)'
                    : 'none',
                  opacity: inputValue.trim() && !isLoading ? 1 : 0.4,
                }}
                onMouseEnter={(e) => {
                  if (inputValue.trim() && !isLoading) {
                    e.currentTarget.style.transform = 'translateY(-2px)'
                    e.currentTarget.style.boxShadow = '0 12px 32px rgba(139, 92, 246, 0.5)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (inputValue.trim() && !isLoading) {
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = '0 8px 24px rgba(139, 92, 246, 0.4)'
                  }
                }}
              >
                <PaperAirplaneIcon style={{ width: '20px', height: '20px', color: '#fff' }} />
              </button>
            </form>

            {error && (
              <div style={{
                marginTop: '12px',
                padding: '12px 16px',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '10px',
                color: '#ef4444',
                fontSize: '13px',
              }}>
                {error}
              </div>
            )}
          </div>
        </div>

        {/* Footer Safety Notice */}
        <div style={{ marginTop: '24px', textAlign: 'center' }}>
          <p style={{ fontSize: '12px', color: '#a8a29e', marginBottom: '8px' }}>
            🔒 Your medical information is private and secure. This AI assistant only accesses your uploaded medical records.
          </p>
          <p style={{ fontSize: '12px', color: '#a8a29e' }}>
            ⚠️ Always verify important medical information with your healthcare provider.
          </p>
        </div>
      </div>

      {/* Document Preview Modal */}
      {showPreview && (
        <div 
          onClick={closePreview}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
            padding: '32px',
          }}
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'linear-gradient(135deg, #1a2942 0%, #0d1f3c 100%)',
              borderRadius: '20px',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
              maxWidth: '1000px',
              width: '100%',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Modal Header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '24px 32px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <DocumentTextIcon style={{ width: '24px', height: '24px', color: '#8b5cf6' }} />
                <div>
                  <h3 style={{
                    fontSize: '18px',
                    fontWeight: '700',
                    color: '#fff',
                    margin: 0,
                  }}>
                    {previewDoc?.name || 'Document Preview'}
                  </h3>
                  <p style={{
                    fontSize: '13px',
                    color: 'rgba(255, 255, 255, 0.5)',
                    margin: '4px 0 0',
                  }}>
                    Medical Document
                  </p>
                </div>
              </div>
              <button
                onClick={closePreview}
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '10px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                }}
              >
                <svg style={{ width: '24px', height: '24px', color: 'rgba(255, 255, 255, 0.8)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div style={{
              flex: 1,
              overflow: 'auto',
              padding: '32px',
              background: 'rgba(0, 0, 0, 0.2)',
            }}>
              {loadingPreview ? (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  minHeight: '400px',
                }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{
                      width: '48px',
                      height: '48px',
                      border: '4px solid rgba(139, 92, 246, 0.2)',
                      borderTopColor: '#8b5cf6',
                      borderRadius: '50%',
                      animation: 'spin 0.8s linear infinite',
                      margin: '0 auto 16px',
                    }}></div>
                    <p style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '15px' }}>Loading document...</p>
                  </div>
                </div>
              ) : previewDoc?.url === 'error' ? (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  minHeight: '400px',
                }}>
                  <div style={{ textAlign: 'center' }}>
                    <ExclamationTriangleIcon style={{ width: '48px', height: '48px', color: '#ef4444', margin: '0 auto 16px' }} />
                    <p style={{ fontSize: '16px', fontWeight: '600', color: '#fff', marginBottom: '8px' }}>Failed to load document</p>
                    <p style={{ fontSize: '14px', color: 'rgba(255, 255, 255, 0.6)' }}>Please try again later</p>
                  </div>
                </div>
              ) : previewDoc?.url ? (
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <img
                    src={previewDoc.url}
                    alt={previewDoc.name}
                    style={{
                      maxWidth: '100%',
                      height: 'auto',
                      borderRadius: '12px',
                      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)',
                      maxHeight: 'calc(90vh - 200px)',
                    }}
                  />
                </div>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '20px 32px',
              borderTop: '1px solid rgba(255, 255, 255, 0.1)',
              background: 'rgba(255, 255, 255, 0.02)',
            }}>
              <button
                onClick={closePreview}
                style={{
                  padding: '12px 24px',
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: 'none',
                  borderRadius: '10px',
                  color: '#fff',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                }}
              >
                Close
              </button>
              <button
                onClick={() => router.push(`/documents/${previewDoc?.id}`)}
                style={{
                  padding: '12px 24px',
                  background: 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)',
                  border: 'none',
                  borderRadius: '10px',
                  color: '#fff',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  boxShadow: '0 8px 24px rgba(139, 92, 246, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 12px 32px rgba(139, 92, 246, 0.5)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = '0 8px 24px rgba(139, 92, 246, 0.4)'
                }}
              >
                <span>View Full Details</span>
                <svg style={{ width: '16px', height: '16px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes bounce {
          0%, 100% {
            transform: translateY(0);
            animation-timing-function: cubic-bezier(0.8, 0, 1, 1);
          }
          50% {
            transform: translateY(-25%);
            animation-timing-function: cubic-bezier(0, 0, 0.2, 1);
          }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
