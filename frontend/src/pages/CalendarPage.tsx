import { useState, useEffect } from 'react'
import Calendar from 'react-calendar'
import 'react-calendar/dist/Calendar.css'
import { useNavigate } from 'react-router-dom'
import { Calendar as CalendarIcon, X, Clock } from 'lucide-react'
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

export default function CalendarPage() {
  const navigate = useNavigate()
  const { meetings, addMeeting } = useMeetings()

  const [showLoginModal, setShowLoginModal] = useState(true)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [miniDate, setMiniDate] = useState(new Date())
  const [selectedSideDate, setSelectedSideDate] = useState<Date | null>(null)
  const [createPopup, setCreatePopup] = useState<CreatePopup | null>(null)
  const [newTitle, setNewTitle] = useState('')
  const [newColor, setNewColor] = useState('#039be5')
  const [listModalDate, setListModalDate] = useState<Date | null>(null)

  useEffect(() => {
    const checkLoginStatus = async () => {
      try {
        const res = await fetch(`http://${window.location.hostname}:8000/api/v1/calendar/status`)
        const data = await res.json()
        if (data.is_logged_in) {
          setIsLoggedIn(true)
          setShowLoginModal(false)
        }
      } catch (e) {
        console.error('인증 상태 확인 실패:', e)
      }
    }
    checkLoginStatus()
  }, [])

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
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    setCreatePopup({ date, x: rect.left, y: rect.bottom + 8 })
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
            onClick={e => { e.stopPropagation(); navigate(`/meeting/${m.id}`) }}
          >
            {m.title}
          </div>
        ))}
        {dayMeetings.length > 3 && (
          <div
            className="more-bar"
            onClick={e => { e.stopPropagation(); setListModalDate(date) }}
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

  // ✅ JSON 받아서 window.location.href로 이동
  const handleGoogleLogin = async () => {
    try {
      const response = await fetch('/api/v1/calendar/auth')
      const data = await response.json()
      window.location.href = data.auth_url
    } catch (e) {
      console.error('로그인 실패', e)
    }
  }

  const handleLogout = () => {
    setIsLoggedIn(false)
    setShowLoginModal(true)
    setShowProfileMenu(false)
  }

  return (
    <div className="dashboard" onClick={() => { setCreatePopup(null); setShowProfileMenu(false) }}>

      {showLoginModal && (
        <div className="modal-overlay">
          <div className="login-modal" onClick={e => e.stopPropagation()}>
            <div className="login-modal-logo">
              <CalendarIcon size={48} color="#aa3bff" />
              <h1 className="login-modal-title">MeetLog</h1>
              <p className="login-modal-desc" style={{ marginTop: 12 }}>AI 회의 기록 서비스, 지금 시작해보세요!</p>
            </div>
            <button className="google-login-btn" onClick={handleGoogleLogin}>
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
        {isLoggedIn && (
          <div className="profile-wrapper" style={{ marginRight: 20 }}>
            <div
              className="profile-avatar"
              style={{ cursor: 'pointer' }}
              onClick={e => { e.stopPropagation(); setShowProfileMenu(prev => !prev) }}
            >
              은
            </div>
            {showProfileMenu && (
              <div className="profile-dropdown" onClick={e => e.stopPropagation()}>
                <div className="profile-dropdown-info">
                  <span className="profile-dropdown-name">은주</span>
                  <span className="profile-dropdown-email">ieunjuee@gmail.com</span>
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
              value={miniDate}
              onChange={val => {
                setMiniDate(val as Date)
                setSelectedSideDate(val as Date)
              }}
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

          {selectedSideDate && (
            <div className="sidebar-card">
              <div className="sidebar-section-title">
                <CalendarIcon size={16} />
                <span>
                  {selectedSideDate.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}
                </span>
              </div>
              {meetingsOnDate(selectedSideDate).length === 0 ? (
                <p className="sidebar-empty">등록된 회의가 없습니다</p>
              ) : (
                <ul className="upcoming-list">
                  {meetingsOnDate(selectedSideDate).map(m => (
                    <li
                      key={m.id}
                      className="upcoming-item"
                      onClick={() => navigate(`/meeting/${m.id}`)}
                    >
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
                  <li
                    key={m.id}
                    className="upcoming-item"
                    onClick={() => navigate(`/meeting/${m.id}`)}
                  >
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
          style={{ top: createPopup.y, left: Math.min(createPopup.x, window.innerWidth - 340) }}
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
                <h2>{listModalDate.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}의 회의</h2>
              </div>
              <button className="icon-btn" onClick={() => setListModalDate(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="meeting-list">
              {meetingsOnDate(listModalDate).map(m => (
                <div
                  key={m.id}
                  className="meeting-item"
                  style={{ borderLeftColor: m.color }}
                  onClick={() => { navigate(`/meeting/${m.id}`); setListModalDate(null) }}
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