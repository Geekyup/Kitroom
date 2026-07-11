const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
const SERVER_API_URL = process.env.API_URL ?? PUBLIC_API_URL
const API_URL = typeof window === "undefined" ? SERVER_API_URL : PUBLIC_API_URL

export type ApiNodeType = "folder" | "file"

export type ApiNode = {
  id: number
  name: string
  node_type: ApiNodeType
  file_format: string | null
  duration_ms: number | null
  order_index: number
  sound_url: string | null
  children: ApiNode[]
}

export type ApiKitTree = {
  kit_slug: string
  kit_title: string
  root: ApiNode[]
}

export type ApiKitCatalogItem = {
  id: number
  title: string
  slug: string
  author: string
  genre: string
  tags: string[]
  cover_path: string | null
  sound_count: number
  downloads_count: number
  size_bytes: number
  status: "pending" | "processing" | "ready" | "failed"
  error_message: string | null
}

export type ApiKitDetail = ApiKitCatalogItem & {
  description: string | null
  created_at: string
}

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // тело не JSON — оставляем statusText
    }
    throw new ApiError(res.status, detail)
  }

  return res.json() as Promise<T>
}

export function absoluteMediaUrl(path: string): string {
  // sound_url/cover_path могут приходить двумя видами:
  // 1) относительный путь вида "/static/kits/3/..." — старый локальный storage backend,
  //    нужно склеить с публичным адресом бэкенда.
  // 2) уже АБСОЛЮТНЫЙ presigned URL от S3-совместимого хранилища (B2/Cloud.ru) —
  //    начинается с http(s):// и содержит подпись запроса (X-Amz-Signature и т.д.).
  //    Такой URL трогать нельзя: конкатенация с PUBLIC_API_URL превращает его
  //    в невалидный адрес вида "http://localhost:8000https://s3.../..." и
  //    <audio>/<img> тихо перестают грузиться.
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  // ВАЖНО: этот URL всегда попадёт в <img>/<audio> в БРАУЗЕРЕ, даже если функция
  // вызвана на сервере (SSR) — поэтому всегда берём публичный адрес,
  // а не внутренний docker-хостнейм (API_URL), иначе картинки/звук будут биты.
  return `${PUBLIC_API_URL}${path}`
}

// Заглушки без реального cover_path (например, сид-скрипт для теста пагинации)
// получают одну из готовых обложек по жанру — так каталог не выглядит пустым.
const GENRE_FALLBACK_COVERS: Record<string, string> = {
  Trap: "/covers/midnight-trap.png",
  "Lo-Fi": "/covers/lofi-dust.png",
  House: "/covers/house-motion.png",
  "Boom Bap": "/covers/boom-bap.png",
  Techno: "/covers/techno-grid.png",
  Drill: "/covers/drill-shadow.png",
}
const FALLBACK_COVER_LIST = Object.values(GENRE_FALLBACK_COVERS)

export function coverForKit(item: Pick<ApiKitCatalogItem, "cover_path" | "genre" | "id">): string {
  if (item.cover_path) return absoluteMediaUrl(item.cover_path)
  return GENRE_FALLBACK_COVERS[item.genre] ?? FALLBACK_COVER_LIST[item.id % FALLBACK_COVER_LIST.length]
}

export const api = {
  listCatalog(params?: { limit?: number; offset?: number }): Promise<ApiKitCatalogItem[]> {
    const search = new URLSearchParams()
    if (params?.limit) search.set("limit", String(params.limit))
    if (params?.offset) search.set("offset", String(params.offset))
    const qs = search.toString()
    return request(`/api/v1/kits${qs ? `?${qs}` : ""}`)
  },

  getKit(slug: string): Promise<ApiKitDetail> {
    return request(`/api/v1/kits/${slug}`)
  },

  getKitTree(slug: string): Promise<ApiKitTree> {
    return request(`/api/v1/kits/${slug}/tree`)
  },

  downloadKitUrl(slug: string): string {
    // прямая ссылка для <a href>, не через fetch — браузер сам стартует скачивание
    return `${API_URL}/api/v1/kits/${slug}/download`
  },
}

export { ApiError }