'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { DocumentPlusIcon, CheckCircleIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline'

interface UploadResult {
  success: boolean
  job_id?: string
  file_info?: {
    original_filename: string
    file_type: string
    file_size: string
  }
  extracted_data?: {
    summary?: string
  }
  error?: string
}

interface ProgressStage {
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  message: string
}

interface Progress {
  job_id: string
  current_stage: 'validating' | 'extracting' | 'summarizing' | 'mapping' | 'completed'
  overall_status: 'in_progress' | 'completed' | 'failed'
  stages: {
    validating: ProgressStage
    extracting: ProgressStage
    summarizing: ProgressStage
    mapping: ProgressStage
  }
  error?: string
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [progress, setProgress] = useState<Progress | null>(null)
  const [user, setUser] = useState<{ id: string; name: string; email: string } | null | undefined>(undefined)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const router = useRouter()

  useEffect(() => {
    const raw = localStorage.getItem('medrix_user')
    setUser(raw ? JSON.parse(raw) : null)
  }, [])

  // Cleanup progress polling on unmount
  useEffect(() => {
    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current)
      }
    }
  }, [])

  // Poll progress API
  const pollProgress = async (jobId: string) => {
    try {
      console.log(`[Progress] Polling for job: ${jobId}`)
      const response = await fetch(`http://localhost:8000/api/v1/clinical/documents/progress/${jobId}`)
      if (response.ok) {
        const progressData = await response.json()
        console.log('[Progress] Received update:', progressData)
        setProgress(progressData)

        // Stop polling if completed or failed
        if (progressData.overall_status === 'completed' || progressData.overall_status === 'failed') {
          console.log('[Progress] Processing finished, stopping poll')
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current)
            progressIntervalRef.current = null
          }
        }
      } else {
        console.log('[Progress] Poll failed:', response.status)
      }
    } catch (error) {
      console.error('[Progress] Polling error:', error)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setUploadResult(null)
      setProgress(null)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
      setUploadResult(null)
      setProgress(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return

    console.log('[Upload] Starting upload...')
    setUploading(true)
    setUploadResult(null)
    
    // Initialize progress state immediately to show progress bar
    setProgress({
      job_id: 'pending',
      current_stage: 'validating',
      overall_status: 'in_progress',
      stages: {
        validating: { status: 'in_progress', message: 'Starting document validation...' },
        extracting: { status: 'pending', message: '' },
        summarizing: { status: 'pending', message: '' },
        mapping: { status: 'pending', message: '' },
      }
    })

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', user?.id || 'demo_user_001')

      console.log('[Upload] Sending request...')
      const response = await fetch('http://localhost:8000/api/v1/clinical/documents/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()
      console.log('[Upload] Response received:', data)

      if (response.ok && data.job_id) {
        console.log('[Upload] Success! Job ID:', data.job_id)
        // Start polling for progress
        pollProgress(data.job_id)
        progressIntervalRef.current = setInterval(() => {
          pollProgress(data.job_id)
        }, 1000) // Poll every second

        setUploadResult({ success: true, ...data })
        setFile(null)
      } else {
        console.log('[Upload] Failed:', data)
        setUploadResult({ success: false, error: data.detail || 'Upload failed' })
        setProgress(null)
      }
    } catch (error) {
      console.error('[Upload] Network error:', error)
      setUploadResult({ success: false, error: 'Network error occurred' })
      setProgress(null)
    } finally {
      setUploading(false)
      console.log('[Upload] Upload phase complete')
    }
  }

  // Auth check
  if (user === undefined) {
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
          <div style={{ fontSize: '64px', marginBottom: '20px' }}>📤</div>
          <h2 style={{ fontSize: '26px', fontWeight: 800, color: '#1c1917', marginBottom: '10px' }}>Sign in to upload documents</h2>
          <p style={{ fontSize: '15px', color: '#78716c', marginBottom: '32px', lineHeight: 1.6 }}>Create an account or sign in to start uploading your medical records.</p>
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
        top: '10%',
        right: '5%',
        width: '400px',
        height: '400px',
        background: 'radial-gradient(circle, rgba(249,115,22,0.12) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(60px)',
        pointerEvents: 'none',
      }}></div>
      <div style={{
        position: 'absolute',
        bottom: '10%',
        left: '5%',
        width: '500px',
        height: '500px',
        background: 'radial-gradient(circle, rgba(251,113,133,0.09) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(80px)',
        pointerEvents: 'none',
      }}></div>

      <div style={{
        maxWidth: '900px',
        margin: '0 auto',
        padding: '60px 24px',
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px' }}>
            <ArrowUpTrayIcon style={{ width: '40px', height: '40px', color: '#f97316', marginRight: '12px' }} />
            <h1 style={{
              fontSize: '48px',
              fontWeight: '900',
              background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              letterSpacing: '-0.02em',
              margin: 0,
            }}>
              Upload Documents
            </h1>
          </div>
          <p style={{
            fontSize: '18px',
            color: '#78716c',
            maxWidth: '600px',
            margin: '0 auto',
            lineHeight: '1.6',
          }}>
            Upload your medical records, lab reports, or prescriptions. Our AI extracts and organizes information instantly.
          </p>
        </div>

        {/* Upload Section */}
        {(!uploadResult?.success || (progress && progress.overall_status === 'in_progress')) ? (
          <div style={{
            background: '#ffffff',
            borderRadius: '24px',
            border: '1.5px solid rgba(0,0,0,0.06)',
            padding: '48px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.05)',
          }}>
            {/* Drag & Drop Zone */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: dragActive ? '3px dashed #f97316' : '3px dashed rgba(0,0,0,0.12)',
                borderRadius: '20px',
                padding: '64px 32px',
                textAlign: 'center',
                cursor: 'pointer',
                background: dragActive ? 'rgba(249,115,22,0.07)' : 'rgba(249,115,22,0.02)',
                transition: 'all 0.3s ease',
                marginBottom: '32px',
              }}
            >
              <DocumentPlusIcon style={{
                width: '80px',
                height: '80px',
                margin: '0 auto 24px',
                color: dragActive ? '#f97316' : '#d4c9c0',
                transition: 'all 0.3s ease',
              }} />
              <h3 style={{
                fontSize: '24px',
                fontWeight: '700',
                color: '#1c1917',
                marginBottom: '12px',
              }}>
                {dragActive ? 'Drop your file here' : 'Drag & drop your file'}
              </h3>
              <p style={{
                fontSize: '16px',
                color: '#78716c',
                marginBottom: '16px',
              }}>
                or <span style={{ color: '#f97316', fontWeight: '600' }}>click to browse</span>
              </p>
              <p style={{
                fontSize: '14px',
                color: '#a8a29e',
              }}>
                PDF, PNG, JPG • Max 10MB
              </p>
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: 'none' }}
                onChange={handleFileChange}
                accept=".pdf,.png,.jpg,.jpeg"
              />
            </div>

            {/* Selected File Preview */}
            {file && (
              <div style={{
                background: 'rgba(249,115,22,0.08)',
                border: '1.5px solid rgba(249,115,22,0.2)',
                borderRadius: '16px',
                padding: '24px',
                marginBottom: '24px',
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
              }}>
                <div style={{
                  width: '56px',
                  height: '56px',
                  background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <DocumentPlusIcon style={{ width: '28px', height: '28px', color: '#fff' }} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{
                    fontSize: '16px',
                    fontWeight: '600',
                    color: '#1c1917',
                    marginBottom: '4px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {file.name}
                  </p>
                  <p style={{
                    fontSize: '14px',
                    color: '#78716c',
                  }}>
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setFile(null)
                  }}
                  style={{
                    padding: '8px 12px',
                    background: 'rgba(0,0,0,0.05)',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#78716c',
                    fontSize: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(0,0,0,0.09)'
                    e.currentTarget.style.color = '#1c1917'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(0,0,0,0.05)'
                    e.currentTarget.style.color = '#78716c'
                  }}
                >
                  Remove
                </button>
              </div>
            )}

            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              style={{
                width: '100%',
                padding: '18px 32px',
                background: file && !uploading 
                  ? 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)'
                  : 'rgba(0,0,0,0.07)',
                border: 'none',
                borderRadius: '14px',
                color: '#fff',
                fontSize: '18px',
                fontWeight: '700',
                cursor: file && !uploading ? 'pointer' : 'not-allowed',
                transition: 'all 0.3s ease',
                boxShadow: file && !uploading 
                  ? '0 8px 24px rgba(249,115,22,0.35)'
                  : 'none',
                opacity: file && !uploading ? 1 : 0.5,
                position: 'relative',
                overflow: 'hidden',
              }}
              onMouseEnter={(e) => {
                if (file && !uploading) {
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 12px 32px rgba(249,115,22,0.45)'
                }
              }}
              onMouseLeave={(e) => {
                if (file && !uploading) {
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = '0 8px 24px rgba(249,115,22,0.35)'
                }
              }}
            >
              {uploading ? (
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
                  <div style={{
                    width: '20px',
                    height: '20px',
                    border: '3px solid rgba(255, 255, 255, 0.3)',
                    borderTopColor: '#fff',
                    borderRadius: '50%',
                    animation: 'spin 0.8s linear infinite',
                  }}></div>
                  Uploading & Processing...
                </span>
              ) : (
                'Upload Document'
              )}
            </button>

            {/* Progress Bar */}
            {progress && (
              <div style={{
                marginTop: '32px',
                padding: '24px',
                background: 'rgba(249,115,22,0.04)',
                borderRadius: '16px',
                border: '1.5px solid rgba(249,115,22,0.12)',
              }}>
                <h3 style={{
                  fontSize: '18px',
                  fontWeight: '700',
                  color: '#1c1917',
                  marginBottom: '20px',
                  textAlign: 'center',
                }}>
                  Processing Document...
                </h3>
                
                {/* Progress Steps */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {/* Step 1: Validating */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                  }}>
                    <div style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: progress.stages.validating.status === 'completed' 
                        ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                        : progress.stages.validating.status === 'in_progress'
                        ? 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)'
                        : progress.stages.validating.status === 'failed'
                        ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                        : 'rgba(0,0,0,0.08)',
                      border: progress.stages.validating.status === 'pending' ? '2px solid rgba(0,0,0,0.12)' : 'none',
                    }}>
                      {progress.stages.validating.status === 'completed' ? '✓' : 
                       progress.stages.validating.status === 'in_progress' ? (
                        <div style={{
                          width: '16px',
                          height: '16px',
                          border: '2px solid rgba(255, 255, 255, 0.3)',
                          borderTopColor: '#fff',
                          borderRadius: '50%',
                          animation: 'spin 0.8s linear infinite',
                        }}></div>
                       ) : progress.stages.validating.status === 'failed' ? '✗' : '1'}
                    </div>
                    <div style={{ flex: 1 }}>
                      <p style={{
                        fontSize: '16px',
                        fontWeight: '600',
                        color: progress.stages.validating.status === 'pending' ? '#a8a29e' : '#1c1917',
                        marginBottom: '4px',
                      }}>
                        Agent 1: Document Validation
                      </p>
                      <p style={{
                        fontSize: '14px',
                        color: '#78716c',
                      }}>
                        {progress.stages.validating.message || 'Checking document quality...'}
                      </p>
                    </div>
                  </div>

                  {/* Step 2: Extracting */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                  }}>
                    <div style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: progress.stages.extracting.status === 'completed' 
                        ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                        : progress.stages.extracting.status === 'in_progress'
                        ? 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)'
                        : progress.stages.extracting.status === 'failed'
                        ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                        : 'rgba(0,0,0,0.08)',
                      border: progress.stages.extracting.status === 'pending' ? '2px solid rgba(0,0,0,0.12)' : 'none',
                    }}>
                      {progress.stages.extracting.status === 'completed' ? '✓' : 
                       progress.stages.extracting.status === 'in_progress' ? (
                        <div style={{
                          width: '16px',
                          height: '16px',
                          border: '2px solid rgba(255, 255, 255, 0.3)',
                          borderTopColor: '#fff',
                          borderRadius: '50%',
                          animation: 'spin 0.8s linear infinite',
                        }}></div>
                       ) : progress.stages.extracting.status === 'failed' ? '✗' : '2'}
                    </div>
                    <div style={{ flex: 1 }}>
                      <p style={{
                        fontSize: '16px',
                        fontWeight: '600',
                        color: progress.stages.extracting.status === 'pending' ? '#a8a29e' : '#1c1917',
                        marginBottom: '4px',
                      }}>
                        Agent 2: Clinical Extraction
                      </p>
                      <p style={{
                        fontSize: '14px',
                        color: '#78716c',
                      }}>
                        {progress.stages.extracting.message || 'Extracting medical data...'}
                      </p>
                    </div>
                  </div>

                  {/* Step 3: Summarizing */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                  }}>
                    <div style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: progress.stages.summarizing.status === 'completed' 
                        ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                        : progress.stages.summarizing.status === 'in_progress'
                        ? 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)'
                        : progress.stages.summarizing.status === 'failed'
                        ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                        : 'rgba(0,0,0,0.08)',
                      border: progress.stages.summarizing.status === 'pending' ? '2px solid rgba(0,0,0,0.12)' : 'none',
                    }}>
                      {progress.stages.summarizing.status === 'completed' ? '✓' : 
                       progress.stages.summarizing.status === 'in_progress' ? (
                        <div style={{
                          width: '16px',
                          height: '16px',
                          border: '2px solid rgba(255, 255, 255, 0.3)',
                          borderTopColor: '#fff',
                          borderRadius: '50%',
                          animation: 'spin 0.8s linear infinite',
                        }}></div>
                       ) : progress.stages.summarizing.status === 'failed' ? '✗' : '3'}
                    </div>
                    <div style={{ flex: 1 }}>
                      <p style={{
                        fontSize: '16px',
                        fontWeight: '600',
                        color: progress.stages.summarizing.status === 'pending' ? '#a8a29e' : '#1c1917',
                        marginBottom: '4px',
                      }}>
                        Agent 3: Intelligent Summary
                      </p>
                      <p style={{
                        fontSize: '14px',
                        color: '#78716c',
                      }}>
                        {progress.stages.summarizing.message || 'Creating summaries...'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Overall Progress Message */}
                {progress.overall_status === 'completed' && (
                  <div style={{
                    marginTop: '20px',
                    padding: '12px',
                    background: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    borderRadius: '12px',
                    textAlign: 'center',
                    color: '#10b981',
                    fontSize: '14px',
                    fontWeight: '600',
                  }}>
                    ✓ All agents completed successfully!
                  </div>
                )}

                {progress.error && (
                  <div style={{
                    marginTop: '20px',
                    padding: '12px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '12px',
                    textAlign: 'center',
                    color: '#ef4444',
                    fontSize: '14px',
                  }}>
                    ⚠️ {progress.error}
                  </div>
                )}
              </div>
            )}

            {/* Error Message */}
            {uploadResult && !uploadResult.success && (
              <div style={{
                marginTop: '24px',
                padding: '16px',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '12px',
                color: '#ef4444',
                fontSize: '14px',
              }}>
                ⚠️ {uploadResult.error}
              </div>
            )}
          </div>
        ) : (
          /* Success State */
          <div style={{
            background: 'rgba(16,185,129,0.07)',
            
            borderRadius: '24px',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            padding: '48px',
            textAlign: 'center',
            boxShadow: '0 8px 32px rgba(16, 185, 129, 0.2)',
          }}>
            <div style={{
              width: '80px',
              height: '80px',
              margin: '0 auto 24px',
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              animation: 'scaleIn 0.5s ease',
            }}>
              <CheckCircleIcon style={{ width: '48px', height: '48px', color: '#fff' }} />
            </div>
            <h2 style={{
              fontSize: '32px',
              fontWeight: '800',
              color: '#10b981',
              marginBottom: '16px',
            }}>
              Upload Successful!
            </h2>
            <div style={{
              textAlign: 'left',
              background: 'rgba(0,0,0,0.03)',
              borderRadius: '16px',
              padding: '24px',
              marginBottom: '24px',
            }}>
              <div style={{ marginBottom: '12px' }}>
                <span style={{ color: '#78716c', fontSize: '14px' }}>File:</span>
                <p style={{ color: '#1c1917', fontSize: '16px', fontWeight: '600', margin: '4px 0 0' }}>
                  {uploadResult.file_info?.original_filename}
                </p>
              </div>
              <div style={{ marginBottom: '12px' }}>
                <span style={{ color: '#78716c', fontSize: '14px' }}>Type:</span>
                <p style={{ color: '#1c1917', fontSize: '16px', margin: '4px 0 0' }}>
                  {uploadResult.file_info?.file_type}
                </p>
              </div>
              <div style={{ marginBottom: '12px' }}>
                <span style={{ color: '#78716c', fontSize: '14px' }}>Size:</span>
                <p style={{ color: '#1c1917', fontSize: '16px', margin: '4px 0 0' }}>
                  {uploadResult.file_info?.file_size}
                </p>
              </div>
              {uploadResult.extracted_data?.summary && (
                <div style={{
                  marginTop: '20px',
                  paddingTop: '20px',
                  borderTop: '1px solid rgba(0,0,0,0.08)',
                }}>
                  <span style={{ color: '#78716c', fontSize: '14px' }}>AI Summary:</span>
                  <p style={{ color: '#1c1917', fontSize: '15px', lineHeight: '1.6', margin: '8px 0 0' }}>
                    {uploadResult.extracted_data.summary}
                  </p>
                </div>
              )}
            </div>
            <button
              onClick={() => {
                setUploadResult(null)
                setFile(null)
              }}
              style={{
                width: '100%',
                padding: '16px 32px',
                background: 'linear-gradient(135deg, #f97316 0%, #fb7185 100%)',
                border: 'none',
                borderRadius: '14px',
                color: '#fff',
                fontSize: '16px',
                fontWeight: '700',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                boxShadow: '0 8px 24px rgba(59, 130, 246, 0.4)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 12px 32px rgba(249,115,22,0.45)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(249,115,22,0.35)'
              }}
            >
              Upload Another Document
            </button>
          </div>
        )}

        {/* Supported Document Types */}
        <div style={{
          marginTop: '48px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '24px',
        }}>
          {[
            { icon: '🧪', title: 'Lab Reports', desc: 'Blood tests, urine tests, imaging results' },
            { icon: '💊', title: 'Prescriptions', desc: 'Medication lists, dosage instructions' },
            { icon: '🏥', title: 'Hospital Records', desc: 'Discharge summaries, visit notes' },
          ].map((item, idx) => (
            <div
              key={idx}
              style={{
                background: '#ffffff',
                border: '1.5px solid rgba(0,0,0,0.06)',
                borderRadius: '16px',
                padding: '24px',
                transition: 'all 0.3s ease',
                cursor: 'default',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)'
                e.currentTarget.style.borderColor = 'rgba(249,115,22,0.3)'
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(249,115,22,0.12)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <div style={{ fontSize: '36px', marginBottom: '12px' }}>{item.icon}</div>
              <h3 style={{
                fontSize: '18px',
                fontWeight: '700',
                color: '#1c1917',
                marginBottom: '8px',
              }}>
                {item.title}
              </h3>
              <p style={{
                fontSize: '14px',
                color: '#78716c',
                lineHeight: '1.5',
              }}>
                {item.desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      <style jsx>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes scaleIn {
          from {
            transform: scale(0);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  )
}
