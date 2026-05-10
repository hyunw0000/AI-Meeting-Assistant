import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, MessageSquare, Upload, Calendar, Mic, Square, Play, PenLine } from 'lucide-react'
import { useMeetings } from '../context/MeetingContext'
import '../App.css'

type Tab = 'record' | 'memo' | 'summary' | 'script'

export default function MeetingDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { meetings } = useMeetings()

  const meeting = meetings.find(m => m.id === id)

  const [activeTab, setActiveTab] = useState<Tab>('record')
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioURL, setAudioURL] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analyzed, setAnalyzed] = useState(false)
  const [memo, setMemo] = useState('')

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0')
    const s = (sec % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []
      mediaRecorder.ondataavailable = e => chunksRef.current.push(e.data)
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setAudioURL(URL.createObjectURL(blob))
        stream.getTracks().forEach(t => t.stop())
      }
      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)
      timerRef.current = setInterval(() => setRecordingTime(t => t + 1), 1000)
    } catch {
      alert('마이크 접근 권한이 필요합니다.')
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setIsRecording(false)
    if (timerRef.current) clearInterval(timerRef.current)
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadedFile(file)
  }

  const handleAnalyze = () => {
    if (!uploadedFile && !audioURL) return
    setIsAnalyzing(true)
    setTimeout(() => {
      setIsAnalyzing(false)
      setAnalyzed(true)
      setActiveTab('summary')
    }, 2500)
  }

  if (!meeting) {
    return (
      <div className="dashboard">
        <div className="empty-state" style={{ marginTop: 80 }}>
          <p>회의를 찾을 수 없습니다.</p>
          <button className="upload-btn" style={{ marginTop: 16 }} onClick={() => navigate('/')}>
            <ArrowLeft size={16} /> 캘린더로 돌아가기
          </button>
        </div>
      </div>
    )
  }

  const tabs = [
    { key: 'record' as Tab, label: '녹음 · 업로드', icon: <Mic size={15} /> },
    { key: 'memo' as Tab, label: '메모', icon: <PenLine size={15} /> },
    { key: 'summary' as Tab, label: '회의 요약', icon: <FileText size={15} /> },
    { key: 'script' as Tab, label: '전체 스크립트', icon: <MessageSquare size={15} /> },
  ]

  return (
    <div className="dashboard" style={{ paddingTop: 40 }}>

      {/* 제목 + 날짜 */}
      <div className="detail-top">
        <button className="back-btn" onClick={() => navigate('/')}>
          <ArrowLeft size={20} />
        </button>
        <div className="detail-title-area">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="color-badge" style={{ backgroundColor: meeting.color, width: 14, height: 14 }} />
            <h1 className="detail-title">{meeting.title}</h1>
          </div>
          <div className="detail-date">
            <Calendar size={14} />
            {meeting.date.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}
          </div>
        </div>
      </div>

      {/* 탭 */}
      <div className="detail-tabs">
        {tabs.map(tab => (
          <button
            key={tab.key}
            className={`detail-tab${activeTab === tab.key ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* 탭 콘텐츠 */}
      <div className="detail-tab-content">

        {/* 녹음 · 업로드 */}
        {activeTab === 'record' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>

            <div className="card detail-page-card">
              <div className="block-title">
                <Mic size={18} />
                <h3>실시간 녹음</h3>
              </div>
              <div className="record-area record-center">
                {isRecording && (
                  <div className="recording-indicator">
                    <span className="rec-dot" />
                    <span className="rec-time">{formatTime(recordingTime)}</span>
                    <span style={{ fontSize: 13, color: '#e53935' }}>녹음 중...</span>
                  </div>
                )}
                {!isRecording && audioURL && (
                  <div className="audio-preview">
                    <Play size={14} />
                    <audio controls src={audioURL} style={{ height: 32, flex: 1 }} />
                  </div>
                )}
                <button
                  className={`record-circle-btn${isRecording ? ' recording' : ''}`}
                  onClick={isRecording ? stopRecording : startRecording}
                >
                  {isRecording ? <Square size={22} /> : <Mic size={22} />}
                </button>
                <span className="record-circle-label">
                  {isRecording ? '탭하여 중지' : '탭하여 녹음'}
                </span>
                {audioURL && !isRecording && (
                  <button className="analyze-btn" onClick={handleAnalyze} disabled={isAnalyzing}>
                    {isAnalyzing ? '분석 중...' : 'AI 분석'}
                  </button>
                )}
              </div>
            </div>

            <div className="card detail-page-card">
              <div className="block-title">
                <Upload size={18} />
                <h3>녹음 파일 업로드</h3>
              </div>
              <div className="upload-zone" style={{ padding: 32, flex: 1 }}>
                {uploadedFile ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <p style={{ margin: 0, fontSize: 14, fontWeight: 500, color: '#1a1a1a' }}>
                      📎 {uploadedFile.name}
                    </p>
                    <p style={{ margin: 0, fontSize: 12, color: '#999' }}>
                      {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <>
                    <Upload size={32} className="upload-icon" />
                    <p style={{ margin: 0, fontSize: 14 }}>파일을 드래그하거나 클릭해서 선택</p>
                    <p className="hint">MP3, MP4, WAV, M4A 지원</p>
                  </>
                )}
                <input type="file" className="file-input" accept="audio/*" onChange={handleFileUpload} />
              </div>
              {uploadedFile && (
                <button
                  className="analyze-btn"
                  onClick={handleAnalyze}
                  disabled={isAnalyzing}
                  style={{ alignSelf: 'flex-end' }}
                >
                  {isAnalyzing ? '분석 중...' : 'AI 분석 시작'}
                </button>
              )}
            </div>

          </div>
        )}

        {/* 메모 */}
        {activeTab === 'memo' && (
          <div className="card detail-page-card">
            <div className="block-title">
              <PenLine size={18} />
              <h3>회의 메모</h3>
            </div>
            <textarea
              className="memo-textarea"
              placeholder="회의 중 자유롭게 메모하세요..."
              value={memo}
              onChange={e => setMemo(e.target.value)}
              style={{ minHeight: 400 }}
            />
          </div>
        )}

        {/* 회의 요약 */}
        {activeTab === 'summary' && (
          <div className="card detail-page-card">
            <div className="block-title">
              <FileText size={18} />
              <h3>회의 요약</h3>
            </div>
            {analyzed ? (
              <p style={{ margin: 0, lineHeight: 1.8, color: '#555', fontSize: 15 }}>
                AI가 분석한 회의 요약 내용이 여기에 표시됩니다. 주요 논의 사항과 결론이 자동으로 정리됩니다.
              </p>
            ) : meeting.summary ? (
              <p style={{ margin: 0, lineHeight: 1.8, color: '#555', fontSize: 15 }}>{meeting.summary}</p>
            ) : (
              <div className="empty-state" style={{ padding: '60px 0' }}>
                <FileText size={36} style={{ opacity: 0.2, marginBottom: 12 }} />
                <p style={{ fontSize: 14 }}>녹음 탭에서 AI 분석을 실행하면<br />요약이 자동 생성됩니다.</p>
              </div>
            )}
          </div>
        )}

        {/* 전체 스크립트 */}
        {activeTab === 'script' && (
          <div className="card detail-page-card">
            <div className="block-title">
              <MessageSquare size={18} />
              <h3>전체 회의 스크립트</h3>
            </div>
            {meeting.transcript ? (
              <div className="script-list">
                {meeting.transcript.split('\n').filter(line => line.trim()).map((line, i) => {
                  const colonIdx = line.indexOf(':')
                  const speaker = colonIdx > -1 ? line.substring(0, colonIdx).trim() : '?'
                  const text = colonIdx > -1 ? line.substring(colonIdx + 1).trim() : line
                  const isFirst = speaker === meeting.transcript.split('\n')[0]?.split(':')?.[0]?.trim()
                  return (
                    <div key={i} className={`script-item${isFirst ? ' speaker-a' : ' speaker-b'}`}>
                      <div className="script-speaker">{speaker}</div>
                      <div className="script-text">{text}</div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: '60px 0' }}>
                <MessageSquare size={36} style={{ opacity: 0.2, marginBottom: 12 }} />
                <p style={{ fontSize: 14 }}>녹음 탭에서 AI 분석을 실행하면<br />전체 스크립트가 표시됩니다.</p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}