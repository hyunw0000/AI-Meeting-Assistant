import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

export interface Meeting {
  id: string
  title: string
  date: Date
  summary: string
  actionItems: string[]
  transcript: string
  color: string
}

const initialMeetings: Meeting[] = [
  {
    id: '1',
    title: 'AI Meeting Assistant 기획 회의',
    date: new Date(2026, 4, 9),
    summary: '프로젝트 초기 아키텍처 및 프론트엔드 개발 우선순위에 대해 논의함.',
    actionItems: ['React Calendar 라이브러리 설치', 'Mock 데이터 구조 설계', 'NCP API 연동 가이드 확인'],
    transcript: 'A: 안녕하세요. 오늘 회의 시작합시다.\nB: 네, 달력 화면부터 만드는거 맞죠?\nA: 네, 맞습니다.',
    color: '#039be5',
  },
  {
    id: '2',
    title: '디자인 시스템 리뷰',
    date: new Date(2026, 4, 10),
    summary: '사용자 경험을 개선하기 위한 디자인 시스템 초안 리뷰.',
    actionItems: ['색상 팔레트 확정', '아이콘 팩 선택 (Lucide React)'],
    transcript: '디자이너: 보라색이 브랜드 아이덴티티에 잘 맞을 것 같아요.\n개발자: 좋습니다.',
    color: '#8e24aa',
  },
]

interface MeetingContextType {
  meetings: Meeting[]
  addMeeting: (meeting: Meeting) => void
}

const MeetingContext = createContext<MeetingContextType | null>(null)

export function MeetingProvider({ children }: { children: ReactNode }) {
  const [meetings, setMeetings] = useState<Meeting[]>(initialMeetings)
  const addMeeting = (meeting: Meeting) => setMeetings(prev => [...prev, meeting])
  return (
    <MeetingContext.Provider value={{ meetings, addMeeting }}>
      {children}
    </MeetingContext.Provider>
  )
}

export function useMeetings() {
  const ctx = useContext(MeetingContext)
  if (!ctx) throw new Error('MeetingProvider 밖에서 사용됨')
  return ctx
}