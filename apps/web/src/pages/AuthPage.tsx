import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

export default function AuthPage() {
  const { login, register, loginAsGuest } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [guestLoading, setGuestLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(email, password, displayName || undefined)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('400')) setError('duplicate_email')
      else if (msg.includes('401')) setError('Invalid email or password.')
      else setError('Something went wrong. Try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleGuest() {
    setError(null)
    setGuestLoading(true)
    try {
      await loginAsGuest()
    } catch {
      setError('Could not start guest session. Try again.')
    } finally {
      setGuestLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 w-full max-w-sm p-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-indigo-600">DocSense</h1>
          <p className="text-sm text-gray-500 mt-1">
            {mode === 'login' ? 'Sign in to your account' : 'Create your account'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Display name</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Your name"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {error && (
            error === 'duplicate_email' ? (
              <p className="text-sm text-red-500">
                An account with <span className="font-medium">{email}</span> already exists.{' '}
                <button
                  type="button"
                  onClick={() => { setMode('login'); setError(null) }}
                  className="underline font-medium hover:text-red-700"
                >
                  Sign in instead?
                </button>
              </p>
            ) : (
              <p className="text-sm text-red-500">{error}</p>
            )
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-xs text-gray-400">
            <span className="bg-white px-2">or</span>
          </div>
        </div>

        <button
          onClick={handleGuest}
          disabled={guestLoading}
          className="w-full border border-gray-300 text-gray-700 rounded-lg py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          {guestLoading ? 'Starting session…' : 'Continue as Guest'}
        </button>

        <p className="text-center text-xs text-gray-400">
          Guest sessions last 2 hours and data is not saved.
        </p>

        <p className="text-center text-sm text-gray-500">
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}
            className="text-indigo-600 font-medium hover:underline"
          >
            {mode === 'login' ? 'Sign up' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  )
}
