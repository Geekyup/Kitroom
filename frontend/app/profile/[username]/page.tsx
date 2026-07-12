import Image from "next/image"
import { notFound } from "next/navigation"
import { Music2, Package } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { KitCard } from "@/components/kit-card"
import { api, avatarForUser, coverForKit, ApiError } from "@/lib/api"
import type { Kit } from "@/lib/data"

export const dynamic = "force-dynamic"

function toKit(item: Awaited<ReturnType<typeof api.getUserKits>>[number]): Kit {
  return {
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
  }
}

export default async function PublicProfilePage({
  params,
}: {
  params: Promise<{ username: string }>
}) {
  const { username } = await params

  let profile
  try {
    profile = await api.getUserProfile(username)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound()
    throw e
  }

  const items = await api.getUserKits(username, { limit: 50 })
  const kits: Kit[] = items.map(toKit)
  const totalDownloads = kits.reduce((sum, k) => sum + k.downloads, 0)
  const totalSounds = kits.reduce((sum, k) => sum + k.soundCount, 0)

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-10 sm:px-6 lg:px-8">
        {/* Profile header */}
        <div className="flex flex-col items-start gap-6 sm:flex-row sm:items-center">
          <div className="relative size-24 shrink-0 overflow-hidden rounded-2xl border border-border">
            <Image
              src={avatarForUser(profile.avatar_path)}
              alt={`Аватар ${profile.username}`}
              fill
              sizes="96px"
              className="object-cover"
            />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">{profile.username}</h1>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            { icon: <Package className="size-5" />, label: "Загружено китов", value: kits.length },
            { icon: <Music2 className="size-5" />, label: "Всего звуков", value: totalSounds },
            { icon: <Package className="size-5" />, label: "Всего скачиваний", value: totalDownloads },
          ].map((s) => (
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

        {/* Kits */}
        <section className="mt-10">
          <h2 className="mb-4 text-xl font-semibold tracking-tight">Киты автора</h2>
          {kits.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border py-16 text-center text-muted-foreground">
              Пока нет опубликованных китов
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:gap-5 lg:grid-cols-3 xl:grid-cols-4">
              {kits.map((kit) => (
                <KitCard key={kit.id} kit={kit} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}