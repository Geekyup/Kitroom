import Image from "next/image"
import Link from "next/link"
import { Download, Music2 } from "lucide-react"
import type { Kit } from "@/lib/data"
import { formatCount } from "@/lib/data"
import { KitAuthor } from "@/components/kit-author"

export function KitCard({ kit }: { kit: Kit }) {
  return (
    <div className="group relative flex flex-col overflow-hidden rounded-2xl border border-border bg-card transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-foreground/5">
      <Link href={`/kit/${kit.id}`} className="relative block aspect-square overflow-hidden">
        <Image
          src={kit.cover || "/placeholder.svg"}
          alt={`Обложка кита ${kit.title}`}
          fill
          sizes="(max-width: 768px) 50vw, 25vw"
          className="object-cover transition-transform duration-300 group-hover:scale-[1.03]"
        />
        <span className="absolute top-3 left-3 rounded-full bg-background/85 px-2.5 py-1 text-xs font-medium text-foreground backdrop-blur">
          {kit.genre}
        </span>
      </Link>

      <div className="flex flex-1 flex-col p-4">
        <Link href={`/kit/${kit.id}`} className="min-w-0">
          <h3 className="truncate font-semibold tracking-tight transition-colors group-hover:text-primary">
            {kit.title}
          </h3>
        </Link>
        <div className="mt-1.5">
          <KitAuthor username={kit.ownerUsername ?? kit.author} avatarPath={kit.ownerAvatar} />
        </div>

        <div className="mt-4 flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
            <Music2 className="size-4" />
            {kit.soundCount} звуков
          </span>
          <Link
            href={`/kit/${kit.id}`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-secondary px-3 py-1.5 text-sm font-medium text-secondary-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
            aria-label={`Скачать кит ${kit.title}`}
          >
            <Download className="size-4" />
            {formatCount(kit.downloads)}
          </Link>
        </div>
      </div>
    </div>
  )
}