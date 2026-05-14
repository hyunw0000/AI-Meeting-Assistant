import { useState, useEffect } from 'react'
import Calendar from 'react-calendar'
import 'react-calendar/dist/Calendar.css'
import { useNavigate } from 'react-router-dom'
import { Calendar as CalendarIcon, X, Clock, Upload, Loader2 } from 'lucide-react'
import { useMeetings } from '../context/MeetingContext'
import type { Meeting } from '../context/MeetingContext'
import '../App.css'

const MEETING_COLORS = [
  { label: '파랑', value: '#039be5' },
  { label: '초록', value: '#33b679' },
  { label: '보라', value: '#8e24aa' },
  { label: '빨강', value: '#e53935' },
  { label: '주황', value: '#f4511e' },
]

interface CreatePopup {
  date: Date
  x: number
  y: number
}

interface UserInfo {
  name: string
  email: string
  picture?: string
}

const formatLocalDate = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const parseLocalDate = (dateString: string) => {
  const [year, month, day] = dateString.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export default function CalendarPage() {
  const navigate = useNavigate()
  const { meetings, addMeeting, setMeetings } = useMeetings()

  const [showLoginModal, setShowLoginModal] = useState(false)
  const [isAuthChecking, setIsAuthChecking] = useState(true)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [user, setUser] = useState<UserInfo | null>(null)
  const [showProfileMenu, setShowProfileMenu] = useState(false)

  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [createPopup, setCreatePopup] = useState<CreatePopup | null>(null)
  const [newTitle, setNewTitle] = useState('')
  const [newColor, setNewColor] = useState('#039be5')
  const [listModalDate, setListModalDate] = useState<Date | null>(null)

  const [isDataLoaded, setIsDataLoaded] = useState(false)
  const [isUploading, setIsUploading] = useState(false)

  useEffect(() => {
    const checkLoginStatus = async () => {
      try {
        const host = window.location.hostname || 'localhost'
        const res = await fetch(`http://${host}:8000/api/v1/calendar/status`)
        if (!res.ok) throw new Error('API not found')

        const data = await res.json()

        if (data.is_logged_in) {
          setIsLoggedIn(true)
          setUser(data.user)
          setShowLoginModal(false)

          if (!isDataLoaded) {
            await fetchGoogleEvents()
            await fetchDbCalendarEvents()
            setIsDataLoaded(true)
          }
        } else {
          setIsLoggedIn(false)
          setUser(null)
          setShowLoginModal(true)
        }

        setIsAuthChecking(false)
      } catch (e) {
        console.error('인증 상태 확인 실패:', e)
        setIsAuthChecking(false)
      }
    }

    checkLoginStatus()
  }, [isDataLoaded])

  const fetchGoogleEvents = async () => {
    try {
      const host = window.location.hostname || 'localhost'
      const res = await fetch(`http://${host}:8000/api/v1/calendar/events`)
      const data = await res.json()

      if (data.events) {
        const googleMeetings: Meeting[] = data.events.map((evt: any) => ({
          id: `google_${evt.id}`,
          title: evt.summary || '제목 없음',
          date: new Date(evt.start.dateTime || evt.start.date),
          summary: evt.description || '',
          actionItems: [],
          transcript: '',
          color: '#33b679',
        }))

        const nonGoogleMeetings = meetings.filter(m => !m.id.startsWith('google_'))
        setMeetings([...nonGoogleMeetings, ...googleMeetings])
      }
    } catch (e) {
      console.error('구글 캘린더 이벤트 불러오기 실패:', e)
    }
  }

  const fetchDbCalendarEvents = async () => {
    try {
      const host = window.location.hostname || 'localhost'

      const eventRes = await fetch(`http://${host}:8000/api/v1/meetings/calendar/events`)
      const eventData = await eventRes.json()

      const events = eventData.events || []

      const meetingDates = Array.from(
        new Set(
          events
            .filter((event: any) => event.type === 'meeting')
            .map((event: any) => event.date)
        )
      )

      const meetingResults = await Promise.all(
        meetingDates.map(async (date: any) => {
          const res = await fetch(`http://${host}:8000/api/v1/meetings/date?date=${date}`)
          const data = await res.json()
          return data.meetings || []
        })
      )

      const dbMeetings: Meeting[] = meetingResults
        .flat()
        .map((m: any) => ({
          id: String(m.id),
          title: m.title || '회의록',
          date: parseLocalDate(m.meeting_date),
          summary: m.summary || '',
          actionItems: (m.tasks || [])
            .map((t: any) => {
              if (typeof t === 'string') return t
              return t.content || ''
            })
            .filter(Boolean),
          transcript: m.transcript || '',
          memo: m.memo || '',
          color: '#039be5',
          fileUrl: m.file_url || '',
        }))

      const taskEvents: Meeting[] = events
        .filter((event: any) => event.type === 'task')
        .map((event: any) => ({
          id: `task_${event.meeting_id}_${event.date}_${event.title}`,
          title: event.title || '할 일',
          date: parseLocalDate(event.date),
          summary: `회의에서 추출된 할 일입니다.\n담당자: ${event.assignee || '미정'}`,
          actionItems: [],
          transcript: '',
          memo: '',
          color: '#f4511e',
          fileUrl: '',
        }))

      setMeetings(prev => {
        const googleMeetings = prev.filter(m => m.id.startsWith('google_'))
        return [...googleMeetings, ...dbMeetings, ...taskEvents]
      })
    } catch (err) {
      console.error('DB 캘린더 이벤트 불러오기 실패:', err)
    }
  }

  const uploadMeetingAudio = async (file: File) => {
    try {
      setIsUploading(true)

      const formData = new FormData()
      formData.append('file', file)
      formData.append('source', 'upload')
      formData.append('meeting_date', formatLocalDate(selectedDate))

      const host = window.location.hostname || 'localhost'
      const res = await fetch(`http://${host}:8000/api/v1/meetings/audio`, {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()

      if (!res.ok) throw new Error(data.detail || '업로드 실패')

      const savedMeeting = data.meeting

      // ✅ 해당 날짜에 미리 저장해둔 회의 찾기
      const existingMeeting = meetings.find(
        m => m.date.toDateString() === parseLocalDate(savedMeeting.meeting_date).toDateString()
          && !m.id.startsWith('google_')
          && !m.id.startsWith('task_')
      )

      const newMeeting: Meeting = {
        id: String(savedMeeting.id),
        title: existingMeeting?.title || savedMeeting.meeting_result?.title || '회의록', // ✅
        date: parseLocalDate(savedMeeting.meeting_date),
        summary: savedMeeting.meeting_result?.summary || '',
        actionItems: (savedMeeting.meeting_result?.tasks || []).map((task: any) => {
          if (typeof task === 'string') return task
          return task.content || ''
        }).filter(Boolean),
        transcript: savedMeeting.transcript || '',
        color: existingMeeting?.color || '#039be5', // ✅
      }

      const taskMeetings: Meeting[] = (savedMeeting.meeting_result?.tasks || [])
        .filter((task: any) => task.due_date)
        .map((task: any, index: number) => ({
          id: `${savedMeeting.id}_task_${index}`,
          title: task.content || '할 일',
          date: parseLocalDate(task.due_date),
          summary: `회의에서 추출된 할 일입니다.\n담당자: ${task.assignee || '미정'}`,
          actionItems: [],
          transcript: savedMeeting.transcript || '',
          color: '#f4511e',
          fileUrl: savedMeeting.file_path || '',
        }))

      setMeetings(prev => [...prev, newMeeting, ...taskMeetings])
      setSelectedDate(newMeeting.date)

      alert('회의록 생성 완료!')
    } catch (err) {
      console.error('업로드 실패:', err)
      alert('업로드 실패. 백엔드, STT, Ollama 실행 상태를 확인해줘.')
    } finally {
      setIsUploading(false)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    uploadMeetingAudio(file)
    e.target.value = ''
  }

  const meetingsOnDate = (date: Date) =>
    meetings.filter(m => m.date.toDateString() === date.toDateString())

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const oneWeekLater = new Date(today)
  oneWeekLater.setDate(today.getDate() + 7)

  const upcomingMeetings = meetings
    .filter(m => {
      const d = new Date(m.date)
      d.setHours(0, 0, 0, 0)
      return d >= today && d <= oneWeekLater
    })
    .sort((a, b) => a.date.getTime() - b.date.getTime())

  const handleTileClick = (date: Date, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedDate(date)

    const dayMeetings = meetingsOnDate(date)

    if (dayMeetings.length > 0) {
      setListModalDate(date)
      setCreatePopup(null)
      return
    }

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    setCreatePopup({ date, x: rect.left, y: rect.bottom + 8 })
    setListModalDate(null)
    setNewTitle('')
    setNewColor('#039be5')
  }

  const handleCreateMeeting = () => {
    if (!newTitle.trim() || !createPopup) return

    const meeting: Meeting = {
      id: Date.now().toString(),
      title: newTitle.trim(),
      date: createPopup.date,
      summary: '',
      actionItems: [],
      transcript: '',
      color: newColor,
    }

    addMeeting(meeting)
    setCreatePopup(null)
  }

  const tileContent = ({ date, view }: { date: Date; view: string }) => {
    if (view !== 'month') return null

    const dayMeetings = meetingsOnDate(date)

    return (
      <div className="tile-events">
        {dayMeetings.slice(0, 3).map(m => (
          <div
            key={m.id}
            className="meeting-bar"
            style={{ backgroundColor: m.color }}
            onClick={e => {
              e.stopPropagation()
              if (m.id.startsWith('task_')) {
                alert(`${m.title}\n\n${m.summary || ''}`)
                return
              }
              navigate(`/meeting/${m.id}`)
            }}
          >
            {m.title}
          </div>
        ))}

        {dayMeetings.length > 3 && (
          <div
            className="more-bar"
            onClick={e => {
              e.stopPropagation()
              setSelectedDate(date)
            }}
          >
            +{dayMeetings.length - 3}개 더보기
          </div>
        )}
      </div>
    )
  }

  const miniTileContent = ({ date, view }: { date: Date; view: string }) => {
    if (view !== 'month') return null
    const hasMeeting = meetings.some(m => m.date.toDateString() === date.toDateString())
    return hasMeeting ? <div className="mini-dot" /> : null
  }

  const formatRelativeDate = (date: Date) => {
    const d = new Date(date)
    d.setHours(0, 0, 0, 0)
    const diff = Math.round((d.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    if (diff === 0) return '오늘'
    if (diff === 1) return '내일'
    if (diff <= 7) return `${diff}일 후`
    return date.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
  }

  const handleGoogleLogin = async (e: React.MouseEvent) => {
    e.preventDefault()
    try {
      const host = window.location.hostname || 'localhost'
      const res = await fetch(`http://${host}:8000/api/v1/calendar/auth`)
      const data = await res.json()
      if (data.auth_url) window.location.href = data.auth_url
    } catch (err) {
      console.error('구글 로그인 시도 중 오류 발생:', err)
    }
  }

  const handleLogout = () => {
    setIsLoggedIn(false)
    setUser(null)
    setShowLoginModal(true)
    setShowProfileMenu(false)
  }

  return (
    <div
      className="dashboard"
      onClick={() => {
        setCreatePopup(null)
        setShowProfileMenu(false)
      }}
    >
      {!isAuthChecking && showLoginModal && (
        <div className="modal-overlay" style={{ zIndex: 9999 }}>
          <div className="login-modal" onClick={e => e.stopPropagation()} style={{ zIndex: 10000 }}>
            <div className="login-modal-logo">
              <CalendarIcon size={48} color="#aa3bff" />
              <h1 className="login-modal-title">MeetLog</h1>
              <p className="login-modal-desc" style={{ marginTop: 12 }}>
                AI 회의 기록 서비스, 지금 시작해보세요!
              </p>
            </div>
            <button
              className="google-login-btn"
              onClick={handleGoogleLogin}
              style={{ position: 'relative', zIndex: 10001, cursor: 'pointer' }}
            >
              <img
                src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
                width={20}
                height={20}
                alt="google"
              />
              Google로 로그인
            </button>
          </div>
        </div>
      )}

      <div className="inline-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 1, marginLeft: 50 }}>
          <CalendarIcon size={22} color="#aa3bff" />
          <span className="logo-text">MeetLog</span>
        </div>

        {isLoggedIn && user && (
          <div className="profile-wrapper" style={{ marginRight: 20 }}>
            <div
              className="profile-avatar"
              style={{ cursor: 'pointer', overflow: 'hidden' }}
              onClick={e => { e.stopPropagation(); setShowProfileMenu(prev => !prev) }}
            >
              {user.picture ? (
                <img src={user.picture} alt={user.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                user.name.charAt(0)
              )}
            </div>

            {showProfileMenu && (
              <div className="profile-dropdown" onClick={e => e.stopPropagation()}>
                <div className="profile-dropdown-info">
                  <span className="profile-dropdown-name">{user.name}</span>
                  <span className="profile-dropdown-email">{user.email}</span>
                </div>
                <hr className="profile-dropdown-divider" />
                <button className="profile-dropdown-logout" onClick={handleLogout}>
                  로그아웃
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <main className="page-layout">
        <aside className="sidebar">
          <div className="sidebar-card">
            <Calendar
              value={selectedDate}
              onChange={val => setSelectedDate(val as Date)}
              tileContent={miniTileContent}
              formatDay={(_locale, date) => String(date.getDate())}
              prevLabel="‹"
              nextLabel="›"
              prev2Label={null}
              next2Label={null}
              calendarType="gregory"
              minDetail="month"
              className="mini-calendar"
            />
          </div>

          <div className="sidebar-card">
            <div className="sidebar-section-title">
              <Upload size={16} />
              <span>녹음 파일 업로드</span>
            </div>

            <div className="upload-zone" onClick={e => e.stopPropagation()} style={{ padding: 24 }}>
              {isUploading ? (
                <>
                  <Loader2 className="upload-icon" size={32} />
                  <p>AI가 회의록을 생성하는 중...</p>
                  <p className="hint">STT와 LLM 분석 때문에 시간이 걸릴 수 있습니다</p>
                </>
              ) : (
                <>
                  <Upload className="upload-icon" size={32} />
                  <p>음성 파일을 선택하세요</p>
                  <p className="hint">선택 날짜: {formatLocalDate(selectedDate ?? new Date())}</p>
                  <p className="hint">MP3, WAV, M4A 지원</p>
                </>
              )}
              <input
                type="file"
                className="file-input"
                accept="audio/*"
                onChange={handleFileUpload}
                disabled={isUploading}
              />
            </div>
          </div>

          {selectedDate && (
            <div className="sidebar-card">
              <div className="sidebar-section-title">
                <CalendarIcon size={16} />
                <span>
                  {selectedDate.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}
                </span>
              </div>

              {meetingsOnDate(selectedDate).length === 0 ? (
                <p className="sidebar-empty">등록된 회의가 없습니다</p>
              ) : (
                <ul className="upcoming-list">
                  {meetingsOnDate(selectedDate).map(m => (
                    <li key={m.id} className="upcoming-item" onClick={() => navigate(`/meeting/${m.id}`)}>
                      <span className="upcoming-dot" style={{ backgroundColor: m.color }} />
                      <div className="upcoming-info">
                        <span className="upcoming-title">{m.title}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div className="sidebar-card">
            <div className="sidebar-section-title">
              <Clock size={16} />
              <span>다가오는 회의</span>
            </div>

            {upcomingMeetings.length === 0 ? (
              <p className="sidebar-empty">예정된 회의가 없습니다</p>
            ) : (
              <ul className="upcoming-list">
                {upcomingMeetings.map(m => (
                  <li key={m.id} className="upcoming-item" onClick={() => navigate(`/meeting/${m.id}`)}>
                    <span className="upcoming-dot" style={{ backgroundColor: m.color }} />
                    <div className="upcoming-info">
                      <span className="upcoming-title">{m.title}</span>
                      <span className="upcoming-date">{formatRelativeDate(m.date)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>

        <section className="main-calendar-section">
          <div className="calendar-card-large">
            <div className="card-header">
              <CalendarIcon size={20} />
              <h2>회의 일정 캘린더</h2>
            </div>

            <Calendar
              value={selectedDate}
              onClickDay={(date, e) => handleTileClick(date, e as unknown as React.MouseEvent)}
              tileContent={tileContent}
              formatDay={(_locale, date) => String(date.getDate())}
              prevLabel="‹"
              nextLabel="›"
              prev2Label={null}
              next2Label={null}
              minDetail="month"
              calendarType="gregory"
              formatShortWeekday={(_locale, date) => ['일', '월', '화', '수', '목', '금', '토'][date.getDay()]}
              className="custom-calendar-large"
            />
          </div>
        </section>
      </main>

      {createPopup && (
        <div
          className="create-popup card"
          style={{ position: 'fixed', top: createPopup.y, left: Math.min(createPopup.x, window.innerWidth - 340) }}
          onClick={e => e.stopPropagation()}
        >
          <div className="create-popup-header">
            <span className="create-popup-date">
              {createPopup.date.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })} 새 회의
            </span>
            <button className="icon-btn" onClick={() => setCreatePopup(null)}>
              <X size={16} />
            </button>
          </div>

          <input
            autoFocus
            className="create-title-input"
            placeholder="회의 제목 추가"
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreateMeeting()}
          />

          <div className="color-row">
            {MEETING_COLORS.map(c => (
              <button
                key={c.value}
                className={`color-dot${newColor === c.value ? ' selected' : ''}`}
                style={{ backgroundColor: c.value }}
                title={c.label}
                onClick={() => setNewColor(c.value)}
              />
            ))}
          </div>

          <div className="create-popup-actions">
            <button className="cancel-btn" onClick={() => setCreatePopup(null)}>취소</button>
            <button
              className="save-btn"
              style={{ backgroundColor: newColor }}
              onClick={handleCreateMeeting}
              disabled={!newTitle.trim()}
            >
              저장
            </button>
          </div>
        </div>
      )}

      {listModalDate && (
        <div className="modal-overlay" onClick={() => setListModalDate(null)}>
          <div className="modal-content card list-modal" onClick={e => e.stopPropagation()}>
            <div className="detail-header">
              <div className="title-with-icon">
                <h2>
                  {listModalDate.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}의 회의
                </h2>
              </div>

              {/* ✅ 회의 추가 버튼 + X 버튼 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button
                  className="save-btn"
                  style={{ backgroundColor: '#039be5', fontSize: 13, padding: '6px 12px' }}
                  onClick={() => {
                    setListModalDate(null)
                    setNewTitle('')
                    setNewColor('#039be5')
                    setTimeout(() => {
                      setCreatePopup({
                        date: listModalDate,
                        x: window.innerWidth / 2 - 160,
                        y: window.innerHeight / 2 - 100,
                      })
                    }, 50)
                  }}
                >
                  + 회의 추가
                </button>

                <button className="icon-btn" onClick={() => setListModalDate(null)}>
                  <X size={20} />
                </button>
              </div>
            </div>

            <div className="meeting-list">
              {meetingsOnDate(listModalDate).map(m => (
                <div
                  key={m.id}
                  className="meeting-item"
                  style={{ borderLeftColor: m.color }}
                  onClick={() => {
                    navigate(`/meeting/${m.id}`)
                    setListModalDate(null)
                  }}
                >
                  <h3>{m.title}</h3>
                  {m.summary && <p>{m.summary.substring(0, 70)}...</p>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}