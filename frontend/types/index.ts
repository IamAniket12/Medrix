export interface Document {
  id: string
  userId: string
  filename: string
  originalName: string
  mimeType: string
  fileSize: number
  filePath: string
  uploadedAt: Date
  documentType?: string
  documentDate?: Date
  extractionStatus: 'pending' | 'processing' | 'completed' | 'failed'
  extractedData?: any
}

export interface MedicalRecord {
  id: string
  userId: string
  documentId: string
  recordType: 'diagnosis' | 'procedure' | 'visit' | 'test' | 'vitals'
  recordDate: Date
  title: string
  description?: string
  provider?: string
  data: any
  createdAt: Date
  updatedAt: Date
}

export interface Medication {
  id: string
  userId: string
  name: string
  dosage?: string
  frequency?: string
  startDate: Date
  endDate?: Date
  prescribedBy?: string
  isActive: boolean
  notes?: string
}

export interface Allergy {
  id: string
  userId: string
  allergen: string
  reaction?: string
  severity?: 'mild' | 'moderate' | 'severe'
  diagnosedAt?: Date
  notes?: string
}

export interface Condition {
  id: string
  userId: string
  name: string
  diagnosedAt?: Date
  status: 'active' | 'resolved' | 'under_observation'
  notes?: string
}

export interface UploadResponse {
  success: boolean
  document?: Document
  error?: string
}

export interface TimelineEvent {
  id: string
  event_date: string // ISO datetime
  event_type: 'diagnosis' | 'medication_started' | 'medication_stopped' | 'lab_result' | 'procedure' | 'visit' | 'hospitalization' | 'other'
  event_title: string
  event_description?: string
  importance: 'high' | 'medium' | 'low'
  provider?: string
  facility?: string
  document?: {
    id: string
    filename: string
    document_type: string
  }
  related_ids?: {
    condition?: string
    medication?: string
    procedure?: string
    lab_result?: string
  }
  created_at?: string
}

export interface TimelineStats {
  total_events: number
  recent_events_30d: number
  by_type: Record<string, number>
  by_importance: Record<string, number>
}

export interface TimelineResponse {
  success: boolean
  total: number
  count: number
  limit: number
  offset: number
  events: TimelineEvent[]
}
