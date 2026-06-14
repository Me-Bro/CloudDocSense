import { NavLink, Route, Routes } from 'react-router-dom'
import ChatPage from './pages/ChatPage'
import UploadPage from './pages/UploadPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex gap-6 items-center">
        <span className="font-bold text-lg text-indigo-600">DocSense</span>
        <NavLink
          to="/"
          className={({ isActive }) => isActive ? 'text-indigo-600 font-medium' : 'text-gray-600'}
        >
          Chat
        </NavLink>
        <NavLink
          to="/upload"
          className={({ isActive }) => isActive ? 'text-indigo-600 font-medium' : 'text-gray-600'}
        >
          Upload
        </NavLink>
      </nav>
      <main className="max-w-4xl mx-auto p-6">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/upload" element={<UploadPage />} />
        </Routes>
      </main>
    </div>
  )
}
