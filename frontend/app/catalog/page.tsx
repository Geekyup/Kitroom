import { SiteHeader } from "@/components/site-header"
import { KitExplorer } from "@/components/kit-explorer"
import { api, coverForKit } from "@/lib/api"
import type { Kit } from "@/lib/data"

export const dynamic = "force-dynamic"

export const PAGE_SIZE = 8

function toKit(item: Awaited<ReturnType<typeof api.listCatalog>>[number]): Kit {
  return {
    id: item.slug,
    title: item.title,
    author: item.author,
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

export default async function CatalogPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>
}) {
  const { q = "" } = await searchParams

  // Первую порцию тянем на сервере — дальше страницы подгружает клиент при скролле.
  const firstPage = await api.listCatalog({ limit: PAGE_SIZE, offset: 0 })
  const kits: Kit[] = firstPage.map(toKit)
  const hasMoreInitially = firstPage.length === PAGE_SIZE

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader initialQuery={q} />

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 className="text-3xl font-semibold tracking-tight">Каталог китов</h1>
          <p className="mt-1 text-muted-foreground">
            Киты от продюсеров со всего мира. Ищите по названию, автору или тегам.
          </p>
        </div>

        <KitExplorer
          initialKits={kits}
          showSearch
          initialQuery={q}
          pageSize={PAGE_SIZE}
          hasMoreInitially={hasMoreInitially}
        />
      </main>

    </div>
  )
}
