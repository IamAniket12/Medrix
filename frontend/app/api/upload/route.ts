import { NextRequest, NextResponse } from 'next/server'

const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Upload API Route - Proxies to FastAPI backend
 * 
 * Following API-First Architecture:
 * Frontend → Backend API → Database
 * 
 * This route simply forwards the file to the FastAPI backend,
 * which handles storage, database operations, and MedGemma extraction.
 */
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get('file') as File

    if (!file) {
      return NextResponse.json(
        { success: false, error: 'No file provided' },
        { status: 400 }
      )
    }

    // Forward the file to FastAPI backend
    const backendFormData = new FormData()
    backendFormData.append('file', file)
    
    // Add user_id when authentication is implemented (Phase 2)
    backendFormData.append('user_id', 'demo-user')

    const response = await fetch(`${BACKEND_API_URL}/api/v1/documents/upload`, {
      method: 'POST',
      body: backendFormData,
    })

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json(
        { success: false, error: error.detail || 'Upload failed' },
        { status: response.status }
      )
    }

    const data = await response.json()
    
    return NextResponse.json({
      success: true,
      ...data,
    })
  } catch (error) {
    console.error('Upload error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to connect to backend. Make sure FastAPI is running at ' + BACKEND_API_URL 
      },
      { status: 500 }
    )
  }
}
