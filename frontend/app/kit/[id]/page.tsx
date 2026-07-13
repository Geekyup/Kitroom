import Image from "next/image"
import Link from "next/link"
import { notFound } from "next/navigation"
import { ArrowLeft, Download, Music2, HardDrive } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { FileBrowser } from "@/components/file-browser"
import { KitAuthor } from "@/components/kit-author"
import { Button } from "@/components/ui/button"
import { api, absoluteMediaUrl, ApiError } from "@/lib/api"
import { formatCount } from "@/lib/data"

export const dynamic = "force-dynamic"

export default async function KitPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params

  let kit
  try {
    kit = await api.getKit(id)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound()
    throw e
  }

  // Дерево доступно только когда кит обработан (status === "ready").
  // Пока обрабатывается — показываем страницу без дерева и просим подождать.
  const tree = kit.status === "ready" ? await api.getKitTree(id) : null

  const coverSrc = kit.cover_path ? absoluteMediaUrl(kit.cover_path) : "/placeholder.svg"

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <Link
          href="/catalog"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          К каталогу
        </Link>

        {/* Header */}
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:gap-8">
          <div className="relative aspect-square w-full shrink-0 overflow-hidden rounded-2xl border border-border sm:w-56 lg:w-64">
            <Image
              src={coverSrc}
              alt={`Обложка кита ${kit.title}`}
              fill
              sizes="256px"
              className="object-cover"
              priority
            />
          </div>

          <div className="flex min-w-0 flex-1 flex-col">
            <span className="inline-flex w-fit items-center rounded-full bg-accent px-2.5 py-1 text-xs font-medium text-accent-foreground">
              {kit.genre}
            </span>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
              {kit.title}
            </h1>
            <span className="mt-2 inline-flex w-fit items-center">
              <KitAuthor username={kit.owner_username} avatarPath={kit.owner_avatar_path} size="md" />
            </span>

            {kit.description && (
              <p className="mt-4 max-w-2xl text-pretty leading-relaxed text-muted-foreground">
                {kit.description}
              </p>
            )}

            <div className="mt-5 flex flex-wrap gap-2">
              {kit.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground"
                >
                  #{tag}
                </span>
              ))}
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Music2 className="size-4" /> {kit.sound_count} звуков
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Download className="size-4" /> {formatCount(kit.downloads_count)} скачиваний
              </span>
              <span className="inline-flex items-center gap-1.5">
                <HardDrive className="size-4" /> {Math.round(kit.size_bytes / 1024 / 1024)} МБ
              </span>
            </div>

            <div className="mt-6">
              {kit.status === "ready" ? (
                <Button
                  size="lg"
                  className="h-12 px-6 text-base"
                  render={<a href={api.downloadKitUrl(id)} download />}
                >
                  <Download className="size-4" />
                  Скачать весь кит (ZIP)
                </Button>
              ) : (
                <Button size="lg" className="h-12 px-6 text-base" disabled>
                  {kit.status === "failed" ? "Обработка не удалась" : "Кит обрабатывается…"}
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* File browser */}
        <section className="mt-10">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-xl font-semibold tracking-tight">Содержимое кита</h2>
            {tree && (
              <span className="text-sm text-muted-foreground">
                Нажмите на файл, чтобы прослушать
              </span>
            )}
          </div>

          {tree ? (
            <FileBrowser nodes={tree.root} />
          ) : (
            <div className="rounded-2xl border border-dashed border-border py-16 text-center text-muted-foreground">
              {kit.status === "failed"
                ? kit.error_message ?? "Не удалось обработать архив кита."
                : "Кит ещё обрабатывается, дерево файлов появится после завершения."}
            </div>
          )}
        </section>
      </main>

    </div>
  )
}