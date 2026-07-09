"use client"

import Image from "next/image"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { Upload, Download, Package, Music2, Camera, Loader2 } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { ProfileKitList } from "@/components/profile-kit-list"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth-context"
import { authApi, authorizedFetch, AuthApiError } from "@/lib/auth"
import { absoluteMediaUrl, type ApiKitCatalogItem } from "@/lib/api"
import { formatCount, type Kit } from "@/lib/data"

export default function ProfilePage() {
  const router = useRouter()
  const { user, loading: authLoading, refreshUser } = useAuth()

  const [kits, setKits] = useState<Kit[] | null>(null)
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [avatarError, setAvatarError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  async function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ""
    if (!file) return

    if (!file.type.startsWith("image/")) {
      setAvatarError("Выберите файл изображения")
      return
    }

    setAvatarError(null)
    setAvatarUploading(true)
    try {
      await authApi.uploadAvatar(file)
      await refreshUser()
    } catch (err) {
      setAvatarError(err instanceof AuthApiError ? err.message : "Не удалось загрузить фото")
    } finally {
      setAvatarUploading(false)
    }
  }

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      router.push("/login")
      return
    }

    authorizedFetch("/api/v1/kits/me")
      .then((res) => res.json())
      .then((items: ApiKitCatalogItem[]) => {
        setKits(
          items.map((item) => ({
            id: item.slug,
            title: item.title,
            author: item.author,
            cover: item.cover_path ? absoluteMediaUrl(item.cover_path) : "/placeholder.svg",
            genre: item.genre,
            tags: item.tags,
            soundCount: item.sound_count,
            downloads: item.downloads_count,
            sizeMb: Math.round(item.size_bytes / 1024 / 1024),
            description: "",
            folders: [],
            status: item.status,
            errorMessage: item.error_message,
          })),
        )
      })
  }, [authLoading, user, router])

  if (authLoading || !user) {
    return (
      <div className="flex min-h-dvh flex-col">
        <SiteHeader />
        <main className="flex-1 px-4 py-16 text-center text-muted-foreground">
          Загрузка…
        </main>
      </div>
    )
  }

  const totalDownloads = kits?.reduce((sum, k) => sum + k.downloads, 0) ?? 0

  const stats = [
    { icon: <Package className="size-5" />, label: "Загружено китов", value: kits?.length ?? 0 },
    { icon: <Download className="size-5" />, label: "Всего скачиваний", value: formatCount(totalDownloads) },
    { icon: <Music2 className="size-5" />, label: "Всего звуков", value: kits?.reduce((s, k) => s + k.soundCount, 0) ?? 0 },
  ]

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6 lg:px-8">
        {/* Profile header */}
        <div className="flex flex-col items-start gap-6 sm:flex-row sm:items-center">
          <div className="group relative size-24 shrink-0">
            <div className="relative size-24 overflow-hidden rounded-2xl border border-border">
              <Image
                src={user.avatar_path ? absoluteMediaUrl(user.avatar_path) : "/placeholder.svg"}
                alt={`Аватар ${user.username}`}
                fill
                sizes="96px"
                className="object-cover"
              />
              {avatarUploading && (
                <div className="absolute inset-0 flex items-center justify-center bg-background/70">
                  <Loader2 className="size-6 animate-spin text-muted-foreground" />
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={avatarUploading}
              aria-label="Изменить фото профиля"
              className="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/0 text-transparent transition-colors group-hover:bg-black/50 group-hover:text-white disabled:cursor-not-allowed"
            >
              <Camera className="size-6" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleAvatarChange}
            />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">{user.username}</h1>
            <p className="text-muted-foreground">{user.email}</p>
            {avatarError && <p className="mt-1 text-sm text-destructive">{avatarError}</p>}
          </div>
          <Button render={<Link href="/upload" />} size="lg" className="h-11 px-5">
            <Upload className="size-4" />
            Загрузить кит
          </Button>
        </div>

        {/* Stats */}
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {stats.map((s) => (
            <div key={s.label} className="flex items-center gap-4 rounded-2xl border border-border bg-card p-5">
              <span className="flex size-11 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                {s.icon}
              </span>
              <div>
                <p className="text-2xl font-semibold tabular-nums">{s.value}</p>
                <p className="text-sm text-muted-foreground">{s.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Uploaded kits */}
        <section className="mt-10">
          <h2 className="mb-4 text-xl font-semibold tracking-tight">Мои киты</h2>
          {kits === null ? (
            <p className="text-muted-foreground">Загрузка китов…</p>
          ) : (
            <ProfileKitList kits={kits} />
          )}
        </section>
      </main>

    </div>
  )
}
