import { NavLink, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import AuthPage from './pages/AuthPage'
import ChatPage from './pages/ChatPage'
import UploadPage from './pages/UploadPage'

function Shell() {
  const { isAuthed, isLoading, user, logout } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!isAuthed) return <AuthPage />

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
        <div className="ml-auto flex items-center gap-4">
          <span className="text-sm text-gray-500">{user?.displayName ?? user?.email}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-800 transition-colors"
          >
            Sign out
          </button>
        </div>
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

export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  )
}
