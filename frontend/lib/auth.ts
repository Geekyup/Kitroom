const ACCESS_TOKEN_KEY = "drumkit_access_token"
const REFRESH_TOKEN_KEY = "drumkit_refresh_token"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export type AuthUser = {
  id: number
  email: string
  username: string
  is_active: boolean
  avatar_path: string | null
}

export type TokenPair = {
  access_token: string
  refresh_token: string
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function storeTokens(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

// Общий промис на "текущий обновление токена" — если несколько запросов
// словили 401 одновременно, все они должны дождаться ОДНОГО вызова
// /auth/refresh, а не устроить гонку из параллельных обновлений (второй
// refresh_token к этому моменту уже был бы отозван первым же вызовом,
// если на бэкенде реализована ротация с обнаружением повторного использования).
let refreshInFlight: Promise<TokenPair | null> | null = null

async function refreshAccessToken(): Promise<TokenPair | null> {
  if (refreshInFlight) return refreshInFlight

  refreshInFlight = (async () => {
    const refreshToken = getRefreshToken()
    if (!refreshToken) return null

    try {
      const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!res.ok) {
        // refresh_token тоже невалиден/истёк/отозван — дальше уже ничего не поделать,
        // пользователя действительно нужно разлогинить
        clearTokens()
        return null
      }

      const tokens = (await res.json()) as TokenPair
      storeTokens(tokens)
      return tokens
    } catch {
      // сетевая ошибка при попытке рефреша — не чистим токены,
      // возможно это временный сбой сети, а не невалидный токен
      return null
    }
  })()

  try {
    return await refreshInFlight
  } finally {
    refreshInFlight = null
  }
}

export class AuthApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function authRequest<T>(path: string, init?: RequestInit, withAuth = false): Promise<T> {
  async function doFetch(): Promise<Response> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(init?.headers as Record<string, string> | undefined),
    }

    if (init?.body) {
      headers["Content-Type"] = "application/json"
    }

    if (withAuth) {
      const token = getAccessToken()
      if (token) headers["Authorization"] = `Bearer ${token}`
    }

    return fetch(`${API_URL}${path}`, { ...init, headers })
  }

  let res = await doFetch()

  // access token истёк (обычно живёт недолго, см. ACCESS_TOKEN_EXPIRE_MINUTES) —
  // пробуем один раз обновить его по refresh_token и повторить запрос,
  // вместо того чтобы сразу разлогинивать пользователя.
  if (res.status === 401 && withAuth && getRefreshToken()) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      res = await doFetch()
    }
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // тело не JSON
    }
    throw new AuthApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const authApi = {
  async register(email: string, username: string, password: string): Promise<AuthUser> {
    return authRequest("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, username, password }),
    })
  },

  async login(email: string, password: string): Promise<TokenPair> {
    const tokens = await authRequest<TokenPair>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })
    storeTokens(tokens)
    return tokens
  },

  async logout(): Promise<void> {
    const refreshToken = getRefreshToken()
    if (refreshToken) {
      try {
        await authRequest("/api/v1/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
      } catch {
        // даже если запрос не удался — токены на клиенте всё равно чистим
      }
    }
    clearTokens()
  },

  async verifyEmail(email: string, code: string): Promise<void> {
    return authRequest("/api/v1/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ email, code }),
    })
  },

  async resendVerification(email: string): Promise<void> {
    return authRequest("/api/v1/auth/resend-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    })
  },

  async fetchCurrentUser(): Promise<AuthUser | null> {
    if (!getAccessToken()) return null
    try {
      return await authRequest<AuthUser>("/api/v1/auth/me", { method: "GET" }, true)
    } catch (e) {
      if (e instanceof AuthApiError && e.status === 401) {
        clearTokens()
      }
      return null
    }
  },

  async uploadAvatar(file: File): Promise<AuthUser> {
    const token = getAccessToken()
    const formData = new FormData()
    formData.append("file", file)

    const res = await fetch(`${API_URL}/api/v1/auth/me/avatar`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: formData,
    })

    if (!res.ok) {
      let detail = res.statusText
      try {
        const body = await res.json()
        detail = body.detail ?? detail
      } catch {
        // тело не JSON
      }
      throw new AuthApiError(res.status, detail)
    }

    return res.json() as Promise<AuthUser>
  },
}

// Обёртка для авторизованных запросов к остальному API (не auth-эндпоинты),
// используется для upload/delete кита и списка "моих китов"
export async function authorizedFetch(path: string, init?: RequestInit): Promise<Response> {
  async function doFetch(): Promise<Response> {
    const token = getAccessToken()
    const headers: Record<string, string> = {
      ...(init?.headers as Record<string, string> | undefined),
    }
    if (token) headers["Authorization"] = `Bearer ${token}`

    return fetch(`${API_URL}${path}`, { ...init, headers })
  }

  let res = await doFetch()

  if (res.status === 401 && getRefreshToken()) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      res = await doFetch()
    }
  }

  return res
}