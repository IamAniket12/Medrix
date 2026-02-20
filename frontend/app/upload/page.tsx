'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DocumentPlusIcon, CloudArrowUpIcon } from '@heroicons/react/24/outline'

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<any>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setUploadResult(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()
      
      if (data.success) {
        setUploadResult(data)
        setFile(null)
        // Reset file input
        const fileInput = document.getElementById('file-upload') as HTMLInputElement
        if (fileInput) fileInput.value = ''
      } else {
        alert('Upload failed: ' + data.error)
      }
    } catch (error) {
      console.error('Upload error:', error)
      alert('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Upload Medical Documents</h1>
        <p className="text-gray-600">
          Upload any medical document (lab reports, prescriptions, X-rays, discharge summaries)
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Document Upload</CardTitle>
          <CardDescription>
            Supported formats: JPG, PNG (Max size: 10MB)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="file-upload">Select File</Label>
            <div className="flex items-center gap-4">
              <Input
                id="file-upload"
                type="file"
                accept=".jpg,.jpeg,.png"
                onChange={handleFileChange}
                disabled={uploading}
              />
            </div>
            {file && (
              <p className="text-sm text-gray-600">
                Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
          </div>

          <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
            <DocumentPlusIcon className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-sm text-gray-600 mb-4">
              Drag and drop files here, or click to select
            </p>
            <Button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="gap-2"
            >
              <CloudArrowUpIcon className="h-5 w-5" />
              {uploading ? 'Uploading...' : 'Upload Document'}
            </Button>
          </div>

          {uploadResult && uploadResult.success && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="font-semibold text-green-900 mb-2">✅ Upload Successful!</h3>
              <div className="text-sm text-green-800">
                <p><strong>File:</strong> {uploadResult.file_info?.original_filename}</p>
                <p><strong>Type:</strong> {uploadResult.file_info?.file_type}</p>
                <p><strong>Size:</strong> {uploadResult.file_info?.file_size}</p>
                {uploadResult.extracted_data && (
                  <div className="mt-3 pt-3 border-t border-green-300">
                    <p><strong>Summary:</strong></p>
                    <p className="text-xs mt-1">{uploadResult.extracted_data.summary || 'Processing...'}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">📄 Lab Reports</h3>
            <p className="text-sm text-gray-600">
              Blood tests, urine tests, imaging results
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">💊 Prescriptions</h3>
            <p className="text-sm text-gray-600">
              Medication lists, dosage instructions
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">🏥 Hospital Records</h3>
            <p className="text-sm text-gray-600">
              Discharge summaries, visit notes
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
