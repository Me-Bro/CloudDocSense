import { useEffect, useRef, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import AuthPage from './pages/AuthPage'
import ChatPage from './pages/ChatPage'
import UploadPage from './pages/UploadPage'

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    if (saved) return saved === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  return [dark, setDark] as const
}

function initials(name: string | null, email: string): string {
  if (name) {
    const parts = name.trim().split(/\s+/)
    return parts.length >= 2
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : parts[0].slice(0, 2).toUpperCase()
  }
  return email.slice(0, 2).toUpperCase()
}

function ProfileDropdown() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onOutside)
    return () => document.removeEventListener('mousedown', onOutside)
  }, [])

  if (!user) return null

  const displayEmail = user.isGuest ? 'Guest session' : user.email
  const abbr = user.isGuest ? 'G' : initials(user.displayName, user.email)

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
        aria-label="Open profile menu"
      >
        <span className="w-8 h-8 rounded-full bg-indigo-600 text-white text-xs font-semibold flex items-center justify-center select-none">
          {abbr}
        </span>
        <span className="text-sm text-gray-700 dark:text-gray-300 font-medium hidden sm:inline">
          {user.isGuest ? 'Guest' : (user.displayName ?? user.email)}
        </span>
        <svg
          className={`w-4 h-4 text-gray-400 dark:text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-4 flex items-center gap-3 border-b border-gray-100 dark:border-gray-700">
            <span className="w-10 h-10 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center shrink-0">
              {abbr}
            </span>
            <div className="min-w-0">
              {user.displayName && (
                <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">{user.displayName}</p>
              )}
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{displayEmail}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="py-1">
            <button
              onClick={() => { logout(); setOpen(false) }}
              className="w-full text-left px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
              </svg>
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function GuestBanner() {
  const { logout } = useAuth()
  return (
    <div className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-6 py-2 flex items-center justify-between text-sm">
      <span className="text-amber-800 dark:text-amber-300">
        Guest session — up to 2 docs, data clears when you close the tab.
      </span>
      <button
        onClick={logout}
        className="ml-4 text-indigo-600 dark:text-indigo-400 font-medium hover:underline shrink-0"
      >
        Sign up to save your work
      </button>
    </div>
  )
}

function DarkToggle({ dark, onToggle }: { dark: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      aria-label="Toggle dark mode"
      className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
    >
      {dark ? (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ) : (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      )}
    </button>
  )
}

function Shell() {
  const { isAuthed, isGuest, isLoading } = useAuth()
  const [dark, setDark] = useDarkMode()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!isAuthed) return <AuthPage />

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {isGuest && <GuestBanner />}
      <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-3 flex gap-6 items-center">
        <span className="font-bold text-lg text-indigo-600">DocSense</span>
        <NavLink
          to="/"
          className={({ isActive }) => isActive ? 'text-indigo-600 font-medium' : 'text-gray-600 dark:text-gray-400'}
        >
          Chat
        </NavLink>
        <NavLink
          to="/upload"
          className={({ isActive }) => isActive ? 'text-indigo-600 font-medium' : 'text-gray-600 dark:text-gray-400'}
        >
          Upload
        </NavLink>
        <div className="ml-auto flex items-center gap-3">
          <DarkToggle dark={dark} onToggle={() => setDark((v) => !v)} />
          <ProfileDropdown />
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
