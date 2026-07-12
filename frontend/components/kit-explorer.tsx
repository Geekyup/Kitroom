"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Search, X, SlidersHorizontal, Loader2 } from "lucide-react"
import { GENRES, type Kit } from "@/lib/data"
import { KitCard } from "@/components/kit-card"
import { api, coverForKit } from "@/lib/api"

type Props = {
  initialKits: Kit[]
  showSearch?: boolean
  initialQuery?: string
  pageSize?: number
  hasMoreInitially?: boolean
}

export function KitExplorer({
  initialKits,
  showSearch = false,
  initialQuery = "",
  pageSize = 8,
  hasMoreInitially = false,
}: Props) {
  const [genre, setGenre] = useState<string>("Все жанры")
  const [query, setQuery] = useState(initialQuery)

  // Список китов, догружаемый с бэкенда порциями по pageSize при скролле вниз.
  const [kits, setKits] = useState<Kit[]>(initialKits)
  const [offset, setOffset] = useState(initialKits.length)
  const [hasMore, setHasMore] = useState(hasMoreInitially)
  const [loading, setLoading] = useState(false)

  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const loadingRef = useRef(false) // защита от повторных вызовов, пока стейт ещё не обновился

  const loadMore = useCallback(async () => {
    if (loadingRef.current || !hasMore) return
    loadingRef.current = true
    setLoading(true)
    try {
      const page = await api.listCatalog({ limit: pageSize, offset })
      const mapped: Kit[] = page.map((item) => ({
        id: item.slug,
        title: item.title,
        author: item.author,
        ownerUsername: item.owner_username,
        ownerAvatar: item.owner_avatar_path,
        cover: coverForKit(item),
        genre: item.genre,
        tags: item.tags,
        soundCount: item.sound_count,
        downloads: item.downloads_count,
        sizeMb: Math.round(item.size_bytes / 1024 / 1024),
        description: "",
        folders: [],
      }))
      setKits((prev) => {
        // на случай гонок/повторных подгрузок не дублируем киты с одинаковым id
        const seen = new Set(prev.map((k) => k.id))
        return [...prev, ...mapped.filter((k) => !seen.has(k.id))]
      })
      setOffset((prev) => prev + page.length)
      setHasMore(page.length === pageSize)
    } catch {
      // тихо останавливаем автодогрузку, чтобы не спамить запросами при ошибке сети
      setHasMore(false)
    } finally {
      loadingRef.current = false
      setLoading(false)
    }
  }, [hasMore, offset, pageSize])

  // Бесконечный скролл: как только сентинел внизу списка появляется в вьюпорте — грузим следующую страницу.
  useEffect(() => {
    const node = sentinelRef.current
    if (!node) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          loadMore()
        }
      },
      { rootMargin: "800px" }, // начинаем подгружать заранее, до того как юзер долистает до самого низа
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [loadMore])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return kits.filter((k) => {
      const genreOk = genre === "Все жанры" || k.genre === genre
      const queryOk =
        !q ||
        k.title.toLowerCase().includes(q) ||
        k.author.toLowerCase().includes(q) ||
        k.genre.toLowerCase().includes(q) ||
        k.tags.some((t) => t.toLowerCase().includes(q))
      return genreOk && queryOk
    })
  }, [kits, genre, query])

  // Пока активны локальные фильтры/поиск — докручивать бэкенд бессмысленно,
  // т.к. новые киты не будут проходить через клиентский фильтр видимым образом.
  const isFiltering = Boolean(query.trim()) || genre !== "Все жанры"
  const shown = filtered
  const showSentinel = !isFiltering && hasMore

  return (
    <div>
      {showSearch && (
        <div className="relative mb-5">
          <Search className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск по названию, автору или тегу…"
            aria-label="Поиск драм-китов"
            className="h-13 w-full rounded-xl border border-input bg-card py-3.5 pr-4 pl-12 text-base outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
          />
        </div>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 pr-1 text-sm font-medium text-muted-foreground">
          <SlidersHorizontal className="size-4" />
          Жанр:
        </span>
        {GENRES.map((g) => {
          const active = genre === g
          return (
            <button
              key={g}
              type="button"
              onClick={() => setGenre(g)}
              aria-pressed={active}
              className={
                "rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors " +
                (active
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground hover:border-foreground/20 hover:text-foreground")
              }
            >
              {g}
            </button>
          )
        })}
      </div>

      {(query.trim() || genre !== "Все жанры") && (
        <div className="mb-6 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">Активные фильтры:</span>
          {genre !== "Все жанры" && (
            <Chip label={genre} onClear={() => setGenre("Все жанры")} />
          )}
          {query.trim() && (
            <Chip label={`«${query.trim()}»`} onClear={() => setQuery("")} />
          )}
          <span className="text-muted-foreground">· найдено {filtered.length}</span>
        </div>
      )}

      {shown.length > 0 ? (
        <div className="grid grid-cols-2 gap-4 sm:gap-5 lg:grid-cols-3 xl:grid-cols-4">
          {shown.map((kit) => (
            <KitCard key={kit.id} kit={kit} />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-border py-20 text-center">
          <p className="font-medium">Ничего не найдено</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Попробуйте изменить запрос или сбросить фильтры.
          </p>
        </div>
      )}

      {isFiltering && hasMore && (
        <p className="mt-10 text-center text-sm text-muted-foreground">
          Показаны совпадения среди уже загруженных китов. Сбросьте фильтры, чтобы
          продолжить бесконечную подгрузку.
        </p>
      )}

      {showSentinel && (
        <div ref={sentinelRef} className="mt-10 flex justify-center py-6">
          {loading && (
            <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Загружаем ещё киты…
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function Chip({ label, onClear }: { label: string; onClear: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-accent py-1 pr-1 pl-3 font-medium text-accent-foreground">
      {label}
      <button
        type="button"
        onClick={onClear}
        aria-label={`Убрать фильтр ${label}`}
        className="flex size-5 items-center justify-center rounded-full transition-colors hover:bg-primary/15"
      >
        <X className="size-3.5" />
      </button>
    </span>
  )
}