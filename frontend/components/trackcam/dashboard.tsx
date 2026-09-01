'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, AlertTriangle, ArrowRight, Bell, Camera, Check, ChevronDown, CircleDot, Clock3, Eye, FileVideo, Film, FolderOpen, Grid2X2, Image, Info, MapPin, Menu, Network, Play, Plus, Radio, RefreshCw, Route, ScanLine, Search, ShieldAlert, Signal, Siren, TrendingUp, Upload, Users, X } from 'lucide-react'
import { alerts, cameras, navItems, vehicles, type Section } from './data'
import { analyzeANPR, getDashboard, getHealth } from '@/lib/trackcam-api'
type VehicleKey = keyof typeof vehicles

const iconMap = { grid: Grid2X2, scan: ScanLine, route: Route, chart: TrendingUp, bell: Bell }

function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'critical' | 'teal' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

function Confidence({ value }: { value: number }) {
  const tone = value >= 85 ? 'good' : value >= 70 ? 'warn' : 'critical'
  return <Badge tone={tone}>{value}% {value >= 85 ? 'HIGH' : value >= 70 ? 'REVIEW' : 'UNCERTAIN'}</Badge>
}

function Card({ children, className = '', style }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) { return <section className={`panel ${className}`} style={style}>{children}</section> }

function Header({ section, onMenu, backendOnline }: { section: Section; onMenu: () => void; backendOnline: boolean }) {
  return <header className="topbar"><button className="mobile-menu" onClick={onMenu} aria-label="Open navigation"><Menu size={20} /></button><div><div className="eyebrow">CITY OPERATIONS / TRACKCAM</div><h1>{section}</h1></div><div className="top-actions"><span className="live-dot"><span /> {backendOnline ? "Backend connected" : "Backend offline"}</span><button className="icon-button" aria-label="Notifications"><Bell size={18} /><i /></button><div className="operator"><div className="avatar">OP</div><div><strong>Operations Desk</strong><small>Chennai Command</small></div><ChevronDown size={15} /></div></div></header>
}

function SideNav({ active, onSelect, open, onClose }: { active: Section; onSelect: (s: Section) => void; open: boolean; onClose: () => void }) {
  return <><aside className={`sidenav ${open ? 'open' : ''}`}><div className="brand"><div className="brand-mark"><Network size={23} /></div><div><strong>TRACKCAM</strong><small>Confidence-aware vehicle intelligence</small></div><button className="close-nav" onClick={onClose}><X size={18} /></button></div><div className="network-status"><span className="pulse" /><div><strong>Chennai network</strong><small>28 cameras online</small></div><span className="status-check"><Check size={13} /></span></div><nav>{navItems.map(item => { const Icon = iconMap[item.icon as keyof typeof iconMap]; return <button key={item.label} className={active === item.label ? 'active' : ''} onClick={() => { onSelect(item.label); onClose() }}><Icon size={18} /><span>{item.label}</span>{item.label === 'Alerts' && <b>3</b>}</button> })}</nav><div className="sidebar-note"><div className="note-icon"><ShieldAlert size={17} /></div><div><strong>Confidence-aware</strong><p>Weak observations lower confidence. They never disappear from the story.</p></div></div><div className="sidebar-footer"><div className="mini-legend"><span><i className="dot teal" /> Active</span><span><i className="dot amber" /> Review</span><span><i className="dot red" /> Alert</span></div><small>Prototype environment · v0.9</small></div></aside>{open && <div className="nav-scrim" onClick={onClose} />}</>
}

function PageIntro({ kicker, title, copy, action }: { kicker: string; title: string; copy: string; action?: React.ReactNode }) { return <div className="page-intro"><div><div className="eyebrow">{kicker}</div><h2>{title}</h2><p>{copy}</p></div>{action}</div> }

function KPI({ icon: Icon, value, label, trend, tone = 'teal' }: { icon: any; value: string; label: string; trend?: string; tone?: string }) { return <Card className="kpi"><div className={`kpi-icon ${tone}`}><Icon size={19} /></div><div><strong>{value}</strong><span>{label}</span></div>{trend && <small className="trend"><TrendingUp size={13} /> {trend}</small>}</Card> }

function CityMap({ trajectory, onCheckpoint }: { trajectory?: readonly any[]; onCheckpoint?: (e: any) => void }) {
  const points = trajectory || cameras.map((c, i) => ({ camera: c.id, place: c.name, x: [15, 38, 62, 82][i], y: [65, 32, 55, 28][i], confidence: c.confidence, state: c.confidence < 70 ? 'UNCERTAIN' : 'HIGH' }))
  return <div className="city-map"><div className="map-label">CHENNAI CAMERA NETWORK <span><Radio size={12} /> LIVE FEED</span></div><div className="map-water" /><div className="road road-a" /><div className="road road-b" /><div className="road road-c" /><div className="road road-d" /><div className="road road-e" />{points.slice(0, -1).map((p, i) => <div key={`line-${p.camera}`} className={`route-line ${p.state === 'UNCERTAIN' || points[i + 1]?.state === 'UNCERTAIN' ? 'uncertain' : ''}`} style={{ left: `${p.x}%`, top: `${p.y}%`, width: `${points[i + 1].x - p.x}%`, transform: `rotate(${Math.atan2(points[i + 1].y - p.y, points[i + 1].x - p.x) * 180 / Math.PI}deg)` }} />)}{points.map((p, i) => <button aria-label={`Select ${p.camera}`} key={p.camera} className={`map-node ${p.state === 'UNCERTAIN' ? 'uncertain' : ''}`} style={{ left: `${p.x}%`, top: `${p.y}%` }} onClick={() => onCheckpoint?.(p)}><span className="node-pulse" /><span className="node-core" /><label><strong>{p.camera}</strong><small>{p.place}</small><em>{p.confidence}%</em></label></button>)}<div className="map-scale"><span /> <small>Network activity · 10:42:18</small></div></div>
}

function Overview({ go, dashboard }: { go: (s: Section) => void; dashboard: any }) { const liveCameras = dashboard?.cameras ?? cameras; const liveAlerts = dashboard?.alerts ?? alerts; const network = dashboard?.network; return <><PageIntro kicker="01 / CITY-WIDE VIEW" title="Good morning, Operations Desk" copy="A confidence-aware view of movement across the Chennai camera network." action={<button className="outline-button" onClick={() => go('ANPR Monitor')}><ScanLine size={16} /> Open camera monitor</button>} /><div className="kpi-grid"><KPI icon={Camera} value={`${network?.active_cameras ?? 28} / ${network?.total_cameras ?? 32}`} label="Active cameras" trend="Live from API" /><KPI icon={Activity} value={(network?.vehicles_observed ?? 12846).toLocaleString()} label="Vehicles observed" trend="Live from API" /><KPI icon={Bell} value={String(network?.active_alerts ?? 3)} label="Active alerts" tone="red" /><KPI icon={Signal} value={`${network?.avg_confidence ?? 91.8}%`} label="Avg. observation confidence" tone="amber" /></div><div className="overview-grid"><Card className="map-card"><div className="card-head"><div><h3>Live camera network</h3><p>Observation activity in the last 15 minutes</p></div><div className="map-legend"><span><i className="dot teal" /> Active</span><span><i className="dot amber" /> Moderate</span><span><i className="dot red" /> Congested</span></div></div><CityMap trajectory={liveCameras.map((c: any, i: number) => ({ ...c, place: c.name, x: [15, 38, 62, 82][i], y: [65, 32, 55, 28][i], state: c.confidence < 70 ? "UNCERTAIN" : "HIGH" }))} onCheckpoint={p => go('Vehicle Tracking')} /></Card><Card className="alerts-preview"><div className="card-head"><div><h3>Recent alerts</h3><p>Events requiring attention</p></div><button className="text-button" onClick={() => go('Alerts')}>View all <ArrowRight size={14} /></button></div>{liveAlerts.slice(0, 3).map((a: any) => <div className="alert-row" key={a.plate + a.time}><div className={`alert-symbol ${a.tone}`}><AlertTriangle size={15} /></div><div><strong>{a.type === 'WATCHLIST MATCH' ? 'Watchlist match' : 'Potential route anomaly'}</strong><span>{a.plate} · {a.camera}</span></div><Confidence value={a.confidence} /></div>)}</Card></div><div className="bottom-grid"><Card><div className="card-head"><div><h3>Traffic status</h3><p>Current density across key corridors</p></div><button className="text-button" onClick={() => go('Traffic Analytics')}>Analytics <ArrowRight size={14} /></button></div><div className="traffic-list">{[['Anna Salai','High','68%', 'red'], ['Rajaji Salai','Moderate','44%', 'amber'], ['GST Road','Low','21%', 'teal']].map(([name, status, width, tone]) => <div className="traffic-item" key={name}><div><strong>{name}</strong><span>{status}</span></div><div className="bar"><i className={tone} style={{ width }} /></div><small>{width}</small></div>)}</div></Card><Card><div className="card-head"><div><h3>Vehicle activity</h3><p>Most observed plates, last hour</p></div><button className="text-button" onClick={() => go('Vehicle Tracking')}>Explore <ArrowRight size={14} /></button></div><div className="activity-list">{[['TN01AB1234','4 cameras','88%'], ['TN01XX9999','3 cameras','93%'], ['KA03YY1111','2 cameras','86%']].map(([plate, cams, conf]) => <button key={plate} onClick={() => go('Vehicle Tracking')}><div className="plate-mini">{plate}</div><span>{cams}</span><Confidence value={Number.parseInt(conf)} /><ArrowRight size={15} /></button>)}</div></Card></div></> }

interface CustomUploadedFile {
  name: string
  type: 'image' | 'video'
  previewUrl?: string
  plate: string
  confidence: number
  quality: string
  location: string
  time: string
  frames: [string, string, string, string, string?][]
}

const sampleLocalFiles: CustomUploadedFile[] = [
  {
    name: 'Dashcam_AnnaSalai_Highway.mp4',
    type: 'video',
    plate: 'TN01AB1234',
    confidence: 94,
    quality: 'Good',
    location: 'Local Drive / Anna Salai Footage',
    time: '10:45:00',
    frames: [
      ['01', 'TN01AB1234', '95%', 'good'],
      ['02', 'TN01AB1234', '94%', 'good'],
      ['03', 'TN01AB1234', '92%', 'good'],
    ]
  },
  {
    name: 'Night_Gate_Scan_042.jpg',
    type: 'image',
    plate: 'TN01XX9999',
    confidence: 91,
    quality: 'Good',
    location: 'Local Drive / Gate Snapshot',
    time: '10:48:12',
    frames: [
      ['01', 'TN01XX9999', '93%', 'good'],
      ['02', 'TN01XX9999', '91%', 'good'],
      ['03', 'TN01XX9990', '71%', 'warn', 'lighting glare'],
    ]
  },
  {
    name: 'Toll_Plaza_HeavyRain.mp4',
    type: 'video',
    plate: 'KA03YY1111',
    confidence: 76,
    quality: 'Degraded',
    location: 'Local Drive / Toll Video',
    time: '10:50:33',
    frames: [
      ['01', 'KA03YY1111', '78%', 'good'],
      ['02', 'KA03YY1111', '76%', 'warn', 'rain drops'],
      ['03', 'KA03YY1117', '62%', 'warn', 'blur'],
    ]
  }
]

function ANPR({ camera, setCamera, cameraData }: { camera: number; setCamera: (n: number) => void; cameraData: any[] }) {
  const c = cameraData[camera] ?? cameras[camera]
  const [feedMode, setFeedMode] = useState<'live' | 'upload'>('live')
  const [uploadedFile, setUploadedFile] = useState<CustomUploadedFile | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsAnalyzing(true)
    const isVideo = file.type.startsWith('video/')
    const previewUrl = URL.createObjectURL(file)

    try {
      const result = await analyzeANPR(file)
      const firstPlate = result.detections?.find((d: any) => d.plate)?.plate || 'NO PLATE DETECTED'
      const firstConfidence = result.detections?.find((d: any) => d.plate)?.confidence
      setUploadedFile({
        name: file.name,
        type: isVideo ? 'video' : 'image',
        previewUrl,
        plate: firstPlate,
        confidence: typeof firstConfidence === 'number' ? Math.round(firstConfidence * 100) : 0,
        quality: result.status === 'model_ready' ? 'Analyzed' : 'Model not loaded',
        location: `Backend upload · ${file.name}`,
        time: new Date().toLocaleTimeString('en-US', { hour12: false }),
        frames: [
          ['01', firstPlate, firstConfidence ? `${Math.round(firstConfidence * 100)}%` : '—', result.status === 'model_ready' ? 'good' : 'warn'],
        ],
      })
    } catch (error) {
      console.error('ANPR upload failed', error)
      setUploadedFile({
        name: file.name,
        type: isVideo ? 'video' : 'image',
        previewUrl,
        plate: 'BACKEND ERROR',
        confidence: 0,
        quality: 'Unavailable',
        location: `Upload failed · ${file.name}`,
        time: new Date().toLocaleTimeString('en-US', { hour12: false }),
        frames: [['01', 'BACKEND ERROR', '—', 'warn']],
      })
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleSelectSample = (sample: CustomUploadedFile) => {
    setIsAnalyzing(true)
    setTimeout(() => {
      setUploadedFile(sample)
      setIsAnalyzing(false)
    }, 500)
  }

  const activePlate = feedMode === 'live' ? c.plate : (uploadedFile?.plate || 'TN01AB1234')
  const activeConfidence = feedMode === 'live' ? c.confidence : (uploadedFile?.confidence || 94)
  const activeQuality = feedMode === 'live' ? c.quality : (uploadedFile?.quality || 'Good')
  const activeFrames = feedMode === 'live'
    ? [['01','TN01AB1234','94%','good'],['02','TN01AB1234','91%','good'],['03','TN01A81234','68%','warn']]
    : (uploadedFile?.frames || sampleLocalFiles[0].frames)

  return (
    <>
      <PageIntro
        kicker="02 / EVIDENCE STREAM & REVIEW"
        title="ANPR monitor & review"
        copy="Review live camera feeds or import local drive images and videos for offline ANPR analysis."
        action={
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ display: 'flex', background: '#e9ecef', borderRadius: '8px', padding: '3px' }}>
              <button
                onClick={() => setFeedMode('live')}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: 'none',
                  background: feedMode === 'live' ? '#2d3f46' : 'transparent',
                  color: feedMode === 'live' ? '#fff' : '#495057',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Camera size={14} /> Live Stream
              </button>
              <button
                onClick={() => setFeedMode('upload')}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: 'none',
                  background: feedMode === 'upload' ? '#2d3f46' : 'transparent',
                  color: feedMode === 'upload' ? '#fff' : '#495057',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Upload size={14} /> Local Files
              </button>
            </div>

            {feedMode === 'live' ? (
              <div className="camera-select">
                <Camera size={16} />
                <select value={camera} onChange={e => setCamera(Number(e.target.value))}>
                  {cameraData.map((cam, i) => (
                    <option value={i} key={cam.id}>{cam.id} · {cam.name}</option>
                  ))}
                </select>
                <ChevronDown size={15} />
              </div>
            ) : (
              <button
                className="dark-button"
                onClick={() => fileInputRef.current?.click()}
                style={{ padding: '6px 14px', fontSize: '12px' }}
              >
                <FolderOpen size={15} /> Select Drive File
              </button>
            )}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept="image/*,video/*"
              style={{ display: 'none' }}
            />
          </div>
        }
      />

      {feedMode === 'upload' && (
        <Card style={{ marginBottom: '16px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 600 }}>Local File ANPR Ingestion</h4>
              <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--muted-foreground)' }}>
                Upload dashcam footage, gate snapshot images, or highway CCTV recordings from your local drive.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                className="outline-button"
                onClick={() => fileInputRef.current?.click()}
                style={{ fontSize: '11px', padding: '5px 10px' }}
              >
                <Plus size={13} /> Add Image / Video
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--muted-foreground)', fontWeight: 500 }}>Quick sample files:</span>
            {sampleLocalFiles.map((s, idx) => (
              <button
                key={idx}
                onClick={() => handleSelectSample(s)}
                style={{
                  fontSize: '11px',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: '1px solid #dcdfe1',
                  background: uploadedFile?.name === s.name ? '#e8f4f1' : '#fff',
                  color: uploadedFile?.name === s.name ? '#173b3b' : '#495057',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                {s.type === 'video' ? <FileVideo size={12} /> : <Image size={12} />}
                {s.name}
              </button>
            ))}
          </div>
        </Card>
      )}

      <div className="monitor-grid">
        <Card className="feed-card">
          <div className="feed-top">
            <span className="live-tag" style={{ color: feedMode === 'upload' ? '#3b789f' : '#3b8d80' }}>
              <span style={{ background: feedMode === 'upload' ? '#3b789f' : '#3b9f8e' }} />
              {feedMode === 'live' ? 'LIVE SIMULATION' : 'LOCAL DRIVE FILE REVIEW'}
            </span>
            <span>
              {feedMode === 'live' ? `${c.time} · ${c.id}` : (uploadedFile?.name || 'Local_File_Ingest.mp4')}
            </span>
          </div>

          <div className="feed-visual">
            <div className="feed-grid" />
            {isAnalyzing && (
              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'rgba(23, 59, 59, 0.85)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                zIndex: 10
              }}>
                <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite' }} />
                <span style={{ marginTop: '10px', fontSize: '13px', fontWeight: 600 }}>Analyzing Local Media...</span>
                <small style={{ fontSize: '10px', color: '#71c9b8', marginTop: '4px' }}>Running Multi-Frame OCR & Plate Detection</small>
              </div>
            )}

            {feedMode === 'upload' && uploadedFile?.previewUrl ? (
              uploadedFile.type === 'video' ? (
                <video
                  src={uploadedFile.previewUrl}
                  controls
                  autoPlay
                  loop
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : (
                <img
                  src={uploadedFile.previewUrl}
                  alt="Uploaded local file"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              )
            ) : null}

            {/* Bounding box simulation */}
            <div className="vehicle-box"><span>VEHICLE · 0.97</span></div>
            <div className="plate-box"><span>PLATE · {activeConfidence}%</span></div>

            <div className="feed-caption">
              <strong>{feedMode === 'live' ? c.location : (uploadedFile?.location || 'Local Drive Media Import')}</strong>
              <small>
                {feedMode === 'live' ? 'Frame 1248 · 1920 × 1080' : `Source: ${uploadedFile?.name || 'Local Drive'} · Processed`}
              </small>
            </div>
          </div>

          <div className="feed-meta">
            <div>
              <small>Detected plate</small>
              <strong>{activePlate}</strong>
            </div>
            <div>
              <small>Observation confidence</small>
              <Confidence value={activeConfidence} />
            </div>
            <div>
              <small>Quality</small>
              <Badge tone={activeQuality === 'Good' ? 'good' : 'warn'}>
                {activeQuality} {activeQuality !== 'Good' && '· glare/rain'}
              </Badge>
            </div>
          </div>
        </Card>

        <div className="evidence-col">
          <Card>
            <div className="card-head">
              <div>
                <h3>Multi-frame OCR evidence</h3>
                <p>{feedMode === 'live' ? 'Three frames, one fused observation' : 'Extracted frames from local drive file'}</p>
              </div>
              <Info size={17} className="muted" />
            </div>
            <div className="frame-list">
              {activeFrames.map(([frame, plate, conf, tone, note]) => (
                <div className="frame-row" key={frame}>
                  <span className="frame-no">FRAME {frame}</span>
                  <strong>{plate}</strong>
                  <Badge tone={tone as any}>{conf}</Badge>
                  {note && <small>{note}</small>}
                </div>
              ))}
            </div>
            <div className="fused-result">
              <div className="fused-icon"><Check size={19} /></div>
              <div>
                <small>FUSED RESULT</small>
                <strong>{activePlate}</strong>
                <span><span className="tiny-dot" /> High confidence · {activeConfidence}%</span>
              </div>
              <Badge tone="good">ACCEPTED</Badge>
            </div>
          </Card>

          <Card className="quality-card">
            <div className="card-head">
              <div>
                <h3>Observation quality</h3>
                <p>Signals that shape confidence</p>
              </div>
              <Badge tone={activeQuality === 'Good' ? 'good' : 'warn'}>{activeQuality}</Badge>
            </div>
            <div className="quality-signals">
              <span><Check size={14} /> Sharpness <b>0.92</b></span>
              <span><Check size={14} /> Visibility <b>0.88</b></span>
              <span><Check size={14} /> Plate angle <b>0.95</b></span>
            </div>
            <div className="quality-note">
              <Eye size={16} />
              <p>
                {feedMode === 'live'
                  ? 'TrackCam uses evidence across frames instead of trusting one OCR read.'
                  : 'Local drive files undergo frame extraction and temporal fusion prior to network logging.'}
              </p>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}

function Tracking({ selected, setSelected, vehicleData }: { selected: VehicleKey; setSelected: (v: VehicleKey) => void; vehicleData: Record<string, any> }) { const v = vehicleData[selected] ?? vehicles[selected]; const [checkpoint, setCheckpoint] = useState<any>(null); return <><PageIntro kicker="03 / VEHICLE EVENT" title="Vehicle tracking" copy="Follow a vehicle across the network, with uncertainty kept visible." action={<div className="search-box"><Search size={17} /><input aria-label="Search license plate" value={selected} onChange={e => { const val = e.target.value.toUpperCase() as VehicleKey; if (val in vehicles) setSelected(val) }} placeholder="Search license plate…" /><ChevronDown size={14} /></div>} /><div className="plate-chips">{Object.keys(vehicles).map(p => <button className={p === selected ? 'selected' : ''} onClick={() => setSelected(p as VehicleKey)} key={p}>{p}</button>)}</div><div className="tracking-grid"><Card className="trajectory-card"><div className="card-head"><div><h3>Confidence-aware trajectory</h3><p>{selected} · {v.events.length} observations connected</p></div><Badge tone="teal"><Route size={13} /> CONNECTED VIEW</Badge></div><CityMap trajectory={v.events} onCheckpoint={setCheckpoint} />{checkpoint && <div className="checkpoint-detail"><div><MapPin size={16} /><strong>{checkpoint.camera}</strong><span>{checkpoint.place} · {checkpoint.time}</span></div><Confidence value={checkpoint.confidence} /><button onClick={() => setCheckpoint(null)} aria-label="Close checkpoint"><X size={15} /></button></div>}</Card><Card className="summary-card"><div className="card-head"><div><h3>Journey summary</h3><p>Aggregated from camera evidence</p></div></div><div className="summary-stats"><div><small>First seen</small><strong>{v.first}</strong></div><div><small>Last seen</small><strong>{v.last}</strong></div><div><small>Cameras visited</small><strong>{v.events.length}</strong></div><div><small>Route duration</small><strong>{v.duration}</strong></div></div><div className="overall-confidence"><div><span>Overall confidence</span><strong>{v.overall}%</strong></div><div className="confidence-meter"><i style={{ width: `${v.overall}%` }} /></div><small>Weighted by plate, appearance, time, location and motion</small></div><div className="logic-flow"><span>PLATE</span><ArrowRight size={13} /><span>RE-ID</span><ArrowRight size={13} /><span>TIME</span><ArrowRight size={13} /><span>LOCATION</span></div></Card></div><div className="timeline-grid"><Card><div className="card-head"><div><h3>Chronological evidence</h3><p>Every checkpoint contributes to the story</p></div></div><div className="timeline">{v.events.map((e, i) => <div className={`timeline-event ${e.state === 'UNCERTAIN' ? 'uncertain' : ''}`} key={e.camera}><div className="timeline-marker"><span>{i + 1}</span></div><div className="timeline-content"><div><strong>{e.camera}</strong><Badge tone={e.state === 'UNCERTAIN' ? 'warn' : 'good'}>{e.state}</Badge></div><span>{e.place}</span><small><Clock3 size={13} /> {e.time}</small></div><Confidence value={e.confidence} /></div>)}</div></Card><Card className="uncertain-card"><div className="uncertain-mark"><AlertTriangle size={19} /></div><div><h3>Uncertain ≠ discarded</h3><p>CAM014 returned a weaker read due to glare. TrackCam lowers confidence for that window, then keeps the trajectory open for later evidence.</p><button className="text-button">How association works <ArrowRight size={14} /></button></div></Card></div></> }

function Analytics() { const bars = [42, 55, 46, 68, 63, 82, 76, 91, 72, 86, 78, 94]; return <><PageIntro kicker="04 / NETWORK INTELLIGENCE" title="Traffic analytics" copy="Aggregated vehicle events reveal density, congestion, and route flow." action={<button className="outline-button"><Clock3 size={15} /> Last 60 minutes <ChevronDown size={14} /></button>} /><div className="analytics-grid"><Card><div className="card-head"><div><h3>Traffic volume</h3><p>Vehicles observed per 5-minute interval</p></div><Badge tone="teal">LIVE</Badge></div><div className="chart"><div className="chart-y"><span>500</span><span>250</span><span>0</span></div><div className="bars">{bars.map((h, i) => <div key={i} className="bar-col"><i style={{ height: `${h}%` }} /><small>{i % 3 === 0 ? `${9 + Math.floor(i / 3)}:${i % 2 ? '15' : '00'}` : ''}</small></div>)}</div></div></Card><Card className="density-card"><div className="card-head"><div><h3>Road density</h3><p>Current corridor load</p></div></div>{[['Road A · Anna Salai','High','68%','red'],['Road B · Rajaji Salai','Medium','44%','amber'],['Road C · GST Road','Low','21%','teal']].map(([n,s,w,t]) => <div className="density-row" key={n}><div><strong>{n}</strong><Badge tone={t as any}>{s}</Badge></div><div className="bar"><i className={t} style={{ width: w }} /></div></div>)}</Card><Card className="heat-card"><div className="card-head"><div><h3>City traffic heatmap</h3><p>Relative activity by network zone</p></div><div className="heat-legend"><span>Low</span><i /><span>High</span></div></div><div className="heatmap">{Array.from({ length: 36 }).map((_, i) => <i key={i} className={`heat-${(i * 7 + 2) % 5}`} />)}<div className="heat-road one" /><div className="heat-road two" /><div className="heat-label l1">CENTRAL</div><div className="heat-label l2">HARBOUR</div><div className="heat-label l3">AIRPORT</div></div></Card><Card className="flow-card"><div className="card-head"><div><h3>Origin → destination flow</h3><p>Connected events in the last hour</p></div></div><div className="flow-map"><div className="flow-line f1" /><div className="flow-line f2" /><div className="flow-line f3" /><span className="flow-node n1">CAM001</span><span className="flow-node n2">CAM008</span><span className="flow-node n3">CAM014</span><span className="flow-node n4">CAM023</span></div><div className="flow-rows"><span><b>CAM001</b><ArrowRight size={13} /><b>CAM014</b><em>284 vehicles</em></span><span><b>CAM008</b><ArrowRight size={13} /><b>CAM023</b><em>196 vehicles</em></span></div></Card></div></> }

function Alerts({ go, goVehicle, alertData }: { go: (s: Section) => void; goVehicle: (plate: VehicleKey) => void; alertData: any[] }) { return <><PageIntro kicker="05 / HUMAN REVIEW QUEUE" title="Alerts" copy="Prioritized events from the network. An alert is a lead, never a verdict." action={<div className="alert-count"><span className="dot red" /> 3 active events</div>} /><div className="alert-tabs"><button className="active">All alerts <b>3</b></button><button>Watchlist matches <b>2</b></button><button>Potential route anomalies <b>1</b></button></div><div className="alert-cards">{alertData.map((a: any, i) => <Card className={`full-alert ${a.tone}`} key={a.plate + a.time}><div className={`big-alert-icon ${a.tone}`}>{a.tone === 'critical' ? <Siren size={20} /> : <AlertTriangle size={20} />}</div><div className="alert-main"><div className="alert-title"><Badge tone={a.tone === 'critical' ? 'critical' : 'warn'}>{a.type}</Badge><span>{a.time} · {a.camera}</span></div><h3>{a.plate}</h3><p>{a.detail || `${a.place} · Watchlist identity observed with high confidence.`}</p><div className="alert-meta"><span><MapPin size={14} /> {a.place}</span><span><Clock3 size={14} /> {a.time}</span><Confidence value={a.confidence} /></div></div><button className="dark-button" onClick={() => goVehicle(a.plate as VehicleKey)}>{a.tone === 'critical' ? 'View trajectory' : 'Review trajectory'} <ArrowRight size={15} /></button></Card>)}</div><div className="review-note"><Info size={17} /><div><strong>Human review stays in the loop</strong><p>Route anomalies flag spatial-temporal inconsistencies for an operator to investigate. They do not indicate criminal activity on their own.</p></div></div></> }

export default function Dashboard() {
  const [active, setActive] = useState<Section>('Overview')
  const [camera, setCamera] = useState(0)
  const [selected, setSelected] = useState<VehicleKey>('TN01AB1234')
  const [navOpen, setNavOpen] = useState(false)
  const [dashboard, setDashboard] = useState<any>({
    cameras,
    vehicles,
    alerts,
    traffic: [],
    network: { total_cameras: 32, active_cameras: 28, vehicles_observed: 12846, active_alerts: alerts.length, avg_confidence: 91.8 },
  })
  const [backendOnline, setBackendOnline] = useState(false)

  const go = (s: Section) => setActive(s)
  const goVehicle = (plate: VehicleKey) => {
    setSelected(plate)
    setActive('Vehicle Tracking')
  }

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [health, data] = await Promise.all([getHealth(), getDashboard()])
        if (!cancelled) {
          setBackendOnline(health.status === 'ok' || health.status === 'degraded')
          setDashboard(data)
        }
      } catch (error) {
        console.warn('TrackCam backend unavailable; using local demo data.', error)
        if (!cancelled) setBackendOnline(false)
      }
    }
    load()
    const timer = window.setInterval(load, 15000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const cameraData = dashboard.cameras?.length ? dashboard.cameras : cameras
  const vehicleData = dashboard.vehicles ?? vehicles
  const alertData = dashboard.alerts?.length ? dashboard.alerts : alerts

  return (
    <div className="app-shell">
      <SideNav active={active} onSelect={go} open={navOpen} onClose={() => setNavOpen(false)} />
      <main className="main">
        <Header section={active} onMenu={() => setNavOpen(true)} backendOnline={backendOnline} />
        <div className="content">
          {active === 'Overview' && <Overview go={go} dashboard={dashboard} />}
          {active === 'ANPR Monitor' && <ANPR camera={camera} setCamera={setCamera} cameraData={cameraData} />}
          {active === 'Vehicle Tracking' && <Tracking selected={selected} setSelected={setSelected} vehicleData={vehicleData} />}
          {active === 'Traffic Analytics' && <Analytics />}
          {active === 'Alerts' && <Alerts go={go} goVehicle={goVehicle} alertData={alertData} />}
        </div>
        <footer className="footer">
          <span><span className="tiny-dot" /> {backendOnline ? 'Backend API connected' : 'Demo mode · backend offline'}</span>
          <span>TrackCam frontend · Smart India Hackathon 2026</span>
        </footer>
      </main>
    </div>
  )
}
