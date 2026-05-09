import { useState } from 'react';
import Calendar from 'react-calendar';
import 'react-calendar/dist/Calendar.css';
import { Calendar as CalendarIcon, FileText, Plus, MessageSquare, CheckCircle, Clock } from 'lucide-react';
import './App.css';

interface Meeting {
  id: string;
  title: string;
  date: Date;
  summary: string;
  actionItems: string[];
  transcript: string;
}

const mockMeetings: Meeting[] = [
  {
    id: '1',
    title: 'AI Meeting Assistant 기획 회의',
    date: new Date(2026, 4, 9), // 2026-05-09
    summary: '프로젝트 초기 아키텍처 및 프론트엔드 개발 우선순위에 대해 논의함. 달력 중심의 UI를 구축하기로 결정.',
    actionItems: ['React Calendar 라이브러리 설치', 'Mock 데이터 구조 설계', 'NCP API 연동 가이드 확인'],
    transcript: 'A: 안녕하세요. 오늘 회의 시작합시다. B: 네, 달력 화면부터 만드는거 맞죠? A: 네, 맞습니다.'
  },
  {
    id: '2',
    title: '디자인 시스템 리뷰',
    date: new Date(2026, 4, 10), // 2026-05-10
    summary: '사용자 경험을 개선하기 위한 디자인 시스템 초안 리뷰. 보라색 테마를 유지하기로 함.',
    actionItems: ['색상 팔레트 확정', '아이콘 팩 선택 (Lucide React)'],
    transcript: '디자이너: 보라색이 브랜드 아이덴티티에 잘 맞을 것 같아요. 개발자: 좋습니다. 구현하기 편하겠네요.'
  }
];

function App() {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // 선택된 날짜에 해당하는 회의 필터링
  const meetingsOnSelectedDate = mockMeetings.filter(
    (m) => m.date.toDateString() === selectedDate.toDateString()
  );

  const handleUpload = () => {
    setIsUploading(true);
    // 실제 서버 연동 전까지 Mock 업로드 시뮬레이션
    setTimeout(() => {
      setIsUploading(false);
      setIsUploadModalOpen(false);
      alert('회의록 분석이 완료되었습니다! (Mock)');
    }, 2000);
  };

  // 달력에 회의가 있는 날 표시를 위한 함수
  const tileContent = ({ date, view }: { date: Date; view: string }) => {
    if (view === 'month') {
      const hasMeeting = mockMeetings.some((m) => m.date.toDateString() === date.toDateString());
      return hasMeeting ? <div className="dot"></div> : null;
    }
    return null;
  };

  return (
    <div className="dashboard">
      <header className="header">
        <h1>AI Meeting Assistant</h1>
        <button className="upload-btn" onClick={() => setIsUploadModalOpen(true)}>
          <Plus size={20} />
          새 회의 업로드
        </button>
      </header>

      <main className="main-content">
        <section className="calendar-section">
          <div className="card">
            <div className="card-header">
              <CalendarIcon size={20} />
              <h2>회의 일정</h2>
            </div>
            <Calendar
              onChange={(value) => setSelectedDate(value as Date)}
              value={selectedDate}
              tileContent={tileContent}
              className="custom-calendar"
            />
          </div>
        </section>

        <section className="list-section">
          <div className="card">
            <div className="card-header">
              <Clock size={20} />
              <h2>{selectedDate.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })}의 회의</h2>
            </div>
            <div className="meeting-list">
              {meetingsOnSelectedDate.length > 0 ? (
                meetingsOnSelectedDate.map((meeting) => (
                  <div
                    key={meeting.id}
                    className={`meeting-item ${selectedMeeting?.id === meeting.id ? 'active' : ''}`}
                    onClick={() => setSelectedMeeting(meeting)}
                  >
                    <h3>{meeting.title}</h3>
                    <p>{meeting.summary.substring(0, 50)}...</p>
                  </div>
                ))
              ) : (
                <div className="empty-state">
                  <p>이 날짜에는 회의록이 없습니다.</p>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>

      {selectedMeeting && (
        <section className="detail-section">
          <div className="card">
            <div className="detail-header">
              <h2>{selectedMeeting.title}</h2>
              <button className="close-btn" onClick={() => setSelectedMeeting(null)}>닫기</button>
            </div>
            
            <div className="detail-grid">
              <div className="detail-block">
                <div className="block-title">
                  <FileText size={18} />
                  <h3>회의 요약</h3>
                </div>
                <p>{selectedMeeting.summary}</p>
              </div>

              <div className="detail-block">
                <div className="block-title">
                  <CheckCircle size={18} />
                  <h3>주요 결정 사항 (Action Items)</h3>
                </div>
                <ul>
                  {selectedMeeting.actionItems.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="detail-block full-width">
                <div className="block-title">
                  <MessageSquare size={18} />
                  <h3>전체 대화 내용 (Transcript)</h3>
                </div>
                <div className="transcript-box">
                  {selectedMeeting.transcript}
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {isUploadModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content card">
            <div className="detail-header">
              <h2>새 회의 업로드</h2>
              <button className="close-btn" onClick={() => setIsUploadModalOpen(false)}>취소</button>
            </div>
            <div className="upload-zone">
              <Plus size={48} className="upload-icon" />
              <p>회의 음성 파일을 드래그하여 놓거나 클릭하여 선택하세요.</p>
              <p className="hint">지원 형식: MP3, WAV, M4A (최대 50MB)</p>
              <input type="file" className="file-input" onChange={handleUpload} disabled={isUploading} />
            </div>
            {isUploading && (
              <div className="uploading-status">
                <div className="spinner"></div>
                <p>AI가 회의록을 분석 중입니다... 잠시만 기다려주세요.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
