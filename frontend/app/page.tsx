import Link from "next/link"
import { ArrowRight, Upload } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { KitExplorer } from "@/components/kit-explorer"
import { Button } from "@/components/ui/button"
import { api, coverForKit } from "@/lib/api"
import type { Kit } from "@/lib/data"

export const dynamic = "force-dynamic"


export default async function HomePage() {
  const items = await api.listCatalog({ limit: 12 })

  const kits: Kit[] = items.map((item) => ({
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

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto max-w-7xl px-4 pt-14 pb-10 sm:px-6 sm:pt-20 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-sm text-muted-foreground">
              <span className="flex size-1.5 rounded-full bg-primary" />
              Новые киты каждый день
            </span>
            <h1 className="mt-5 text-balance text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
              Библиотека драм-китов для продюсеров
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-pretty text-lg leading-relaxed text-muted-foreground">
              Находите, прослушивайте и скачивайте драм-киты прямо в браузере.
              Чистый файловый браузер, мгновенное превью каждого звука и загрузка
              одним архивом.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Button render={<Link href="/catalog" />} size="lg" className="h-12 px-5 text-base">
                Смотреть каталог
                <ArrowRight className="size-4" />
              </Button>
              <Button
                render={<Link href="/upload" />}
                variant="outline"
                size="lg"
                className="h-12 px-5 text-base"
              >
                <Upload className="size-4" />
                Загрузить свой кит
              </Button>
            </div>
          </div>
        </section>

        {/* Catalog */}
        <section className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="mb-6 flex items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Популярные киты</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Отфильтруйте по жанру или откройте полный каталог.
              </p>
            </div>
            <Link
              href="/catalog"
              className="hidden shrink-0 items-center gap-1 text-sm font-medium text-primary hover:underline sm:inline-flex"
            >
              Весь каталог
              <ArrowRight className="size-4" />
            </Link>
          </div>

          <KitExplorer initialKits={kits} hasMoreInitially={false} />
        </section>
      </main>

    </div>
  )
}