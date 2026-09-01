export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') || 'http://localhost:8000'

export interface TrackCamDashboard {
  timestamp: string
  network: {
    total_cameras: number
    active_cameras: number
    vehicles_observed: number
    active_alerts: number
    avg_confidence: number
  }
  cameras: any[]
  vehicles: Record<string, any>
  alerts: any[]
  traffic: any[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { Accept: 'application/json', ...(init?.headers || {}) },
    cache: 'no-store',
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `TrackCam API returned ${response.status}`)
  }
  return response.json()
}

export function getDashboard() {
  return request<TrackCamDashboard>('/api/dashboard')
}

export function getHealth() {
  return request<{ status: string; database: { connected: boolean } }>('/health')
}

export async function analyzeANPR(file: File) {
  const form = new FormData()
  form.append('file', file)
  return request<{
    status: string
    filename: string
    size_bytes: number
    media_type?: string
    models: { vehicle_detector: boolean; plate_detector: boolean; ocr: boolean }
    detections: any[]
    message: string
  }>('/api/anpr/analyze', { method: 'POST', headers: {}, body: form })
}

export function getLiveWebSocketUrl() {
  const url = new URL(API_BASE_URL)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/ws/live'
  return url.toString()
}
