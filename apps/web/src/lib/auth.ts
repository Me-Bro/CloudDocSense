const TOKEN_KEY = 'ds_token'
const GUEST_TOKEN_KEY = 'ds_guest_token'

function decodeIsGuest(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return !!payload.is_guest
  } catch {
    return false
  }
}

let _token: string | null =
  sessionStorage.getItem(GUEST_TOKEN_KEY) ?? localStorage.getItem(TOKEN_KEY)

export function getToken(): string | null {
  return _token
}

export function setToken(t: string | null): void {
  _token = t
  if (t) {
    if (decodeIsGuest(t)) {
      sessionStorage.setItem(GUEST_TOKEN_KEY, t)
      localStorage.removeItem(TOKEN_KEY)
    } else {
      localStorage.setItem(TOKEN_KEY, t)
      sessionStorage.removeItem(GUEST_TOKEN_KEY)
    }
  } else {
    localStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(GUEST_TOKEN_KEY)
  }
}

/** Dispatch so AuthContext can react to 401s from apiClient. */
export function signalUnauthorized(): void {
  window.dispatchEvent(new Event('ds:unauthorized'))
}
