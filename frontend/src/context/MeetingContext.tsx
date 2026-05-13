import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

export interface Meeting {
  id: string
  title: string
  date: Date
  summary: string
  actionItems: string[]
  transcript: string
  color: string
  fileUrl?: string
}

interface MeetingContextType {
  meetings: Meeting[]
  addMeeting: (meeting: Meeting) => void
  updateMeeting: (id: string, meeting: Partial<Meeting>) => void
  setMeetings: React.Dispatch<React.SetStateAction<Meeting[]>>
  deleteMeeting: (id: string) => void
}

const MeetingContext = createContext<MeetingContextType | null>(null)

const STORAGE_KEY = 'meetlog_meetings'

const initialMeetings: Meeting[] = []

export function MeetingProvider({ children }: { children: ReactNode }) {
  const [meetings, setMeetings] = useState<Meeting[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEY)

    if (!saved) return initialMeetings

    return JSON.parse(saved).map((m: any) => ({
      ...m,
      date: new Date(m.date),
    }))
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(meetings))
  }, [meetings])

  const addMeeting = (meeting: Meeting) => {
    setMeetings(prev => [...prev, meeting])
  }

  const updateMeeting = (id: string, updated: Partial<Meeting>) => {
    setMeetings(prev =>
      prev.map(m =>
        m.id === id ? { ...m, ...updated } : m
      )
    )
  }

  const deleteMeeting = (id: string) => {
    setMeetings(prev => prev.filter(m => m.id !== id))
  }

  return (
    <MeetingContext.Provider
      value={{ meetings, addMeeting, updateMeeting, setMeetings, deleteMeeting }}
    >
      {children}
    </MeetingContext.Provider>
  )
}

export function useMeetings() {
  const ctx = useContext(MeetingContext)
  if (!ctx) throw new Error('MeetingProvider 밖에서 사용됨')
  return ctx
}