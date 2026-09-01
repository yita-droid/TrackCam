export type Section = 'Overview' | 'ANPR Monitor' | 'Vehicle Tracking' | 'Traffic Analytics' | 'Alerts'

export const cameras = [
  { id: 'CAM001', name: 'North Gate', location: 'Anna Salai / Gemini Flyover', status: 'active', traffic: 'Moderate', count: 284, health: '98%', plate: 'TN01AB1234', confidence: 96, quality: 'Good', time: '10:42:18' },
  { id: 'CAM008', name: 'Harbour Link', location: 'Rajaji Salai / Gate 2', status: 'active', traffic: 'High', count: 412, health: '94%', plate: 'TN01AB1234', confidence: 91, quality: 'Good', time: '10:39:44' },
  { id: 'CAM014', name: 'Central Junction', location: 'Mount Road / Cathedral', status: 'moderate', traffic: 'Severe', count: 631, health: '89%', plate: 'TN01A81234', confidence: 62, quality: 'Degraded', time: '10:36:02' },
  { id: 'CAM023', name: 'Airport Corridor', location: 'GST Road / Meenambakkam', status: 'congested', traffic: 'Severe', count: 718, health: '96%', plate: 'TN01AB1234', confidence: 94, quality: 'Good', time: '10:31:27' },
]

export const vehicles = {
  TN01AB1234: { first: '09:18:04', last: '10:42:18', duration: '1h 24m', overall: 88, events: [
    { camera: 'CAM001', place: 'North Gate', time: '09:18:04', confidence: 96, state: 'HIGH', x: 16, y: 68 },
    { camera: 'CAM008', place: 'Harbour Link', time: '09:42:31', confidence: 91, state: 'HIGH', x: 39, y: 35 },
    { camera: 'CAM014', place: 'Central Junction', time: '10:16:48', confidence: 62, state: 'UNCERTAIN', x: 61, y: 54 },
    { camera: 'CAM023', place: 'Airport Corridor', time: '10:42:18', confidence: 94, state: 'HIGH', x: 83, y: 29 },
  ] },
  TN01XX9999: { first: '08:54:22', last: '10:42:18', duration: '1h 48m', overall: 93, events: [
    { camera: 'CAM008', place: 'Harbour Link', time: '08:54:22', confidence: 95, state: 'HIGH', x: 24, y: 56 },
    { camera: 'CAM014', place: 'Central Junction', time: '09:37:16', confidence: 89, state: 'HIGH', x: 50, y: 42 },
    { camera: 'CAM023', place: 'Airport Corridor', time: '10:42:18', confidence: 97, state: 'HIGH', x: 78, y: 68 },
  ] },
  KA03YY1111: { first: '07:12:09', last: '08:08:41', duration: '56m', overall: 86, events: [
    { camera: 'CAM001', place: 'North Gate', time: '07:12:09', confidence: 86, state: 'HIGH', x: 18, y: 30 },
    { camera: 'CAM014', place: 'Central Junction', time: '08:08:41', confidence: 86, state: 'HIGH', x: 59, y: 65 },
  ] },
  DL04CD5678: { first: '11:08:12', last: '11:52:05', duration: '44m', overall: 79, events: [
    { camera: 'CAM008', place: 'Harbour Link', time: '11:08:12', confidence: 79, state: 'UNCERTAIN', x: 27, y: 72 },
    { camera: 'CAM023', place: 'Airport Corridor', time: '11:52:05', confidence: 88, state: 'HIGH', x: 80, y: 35 },
  ] },
} as const

export const alerts = [
  { type: 'WATCHLIST MATCH', plate: 'TN01XX9999', camera: 'CAM023', place: 'Central Junction', time: '10:42:18', confidence: 97, tone: 'critical' },
  { type: 'POTENTIAL ROUTE ANOMALY', plate: 'DL04CD5678', camera: 'CAM014', place: 'Mount Road / Cathedral', time: '10:18:07', confidence: 68, tone: 'warning', detail: 'Spatial-temporal inconsistency · Requires human review' },
  { type: 'WATCHLIST MATCH', plate: 'KA03YY1111', camera: 'CAM008', place: 'Harbour Link', time: '09:37:16', confidence: 91, tone: 'critical' },
]

export const navItems: { label: Section; icon: string; hint: string }[] = [
  { label: 'Overview', icon: 'grid', hint: 'City-wide command view' },
  { label: 'ANPR Monitor', icon: 'scan', hint: 'Live camera evidence' },
  { label: 'Vehicle Tracking', icon: 'route', hint: 'Confidence-aware trajectories' },
  { label: 'Traffic Analytics', icon: 'chart', hint: 'Density and movement' },
  { label: 'Alerts', icon: 'bell', hint: 'Review priority events' },
]
