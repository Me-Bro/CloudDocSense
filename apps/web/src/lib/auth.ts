const TOKEN_KEY = 'ds_token'

let _token: string | null = localStorage.getItem(TOKEN_KEY)

export function getToken(): string | null {
  return _token
}

export function setToken(t: string | null): void {
  _token = t
  if (t) localStorage.setItem(TOKEN_KEY, t)
  else localStorage.removeItem(TOKEN_KEY)
}

/** Dispatch so AuthContext can react to 401s from apiClient. */
export function signalUnauthorized(): void {
  window.dispatchEvent(new Event('ds:unauthorized'))
}
