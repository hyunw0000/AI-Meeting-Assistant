import { Routes, Route } from 'react-router-dom'
import CalendarPage from './pages/CalendarPage'
import MeetingDetailPage from './pages/MeetingDetailPage'
import { MeetingProvider } from './context/MeetingContext'
function App() {
  return (
    <MeetingProvider>
      <Routes>
        <Route path="/" element={<CalendarPage />} />
        <Route path="/meeting/:id" element={<MeetingDetailPage />} />
      </Routes>
    </MeetingProvider>
  )
}

export default App