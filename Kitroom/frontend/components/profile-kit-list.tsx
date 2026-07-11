"use client"

import { useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { Pencil, Trash2, Download, Music2, Plus } from "lucide-react"
import type { Kit } from "@/lib/data"
import { formatCount } from "@/lib/data"
import { Button } from "@/components/ui/button"
import { EditKitDialog } from "@/components/edit-kit-dialog"
import { authorizedFetch } from "@/lib/auth"

export function ProfileKitList({ kits }: { kits: Kit[] }) {
  const [items, setItems] = useState(kits)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [editingKit, setEditingKit] = useState<Kit | null>(null)

  async function remove(id: string) {
    if (!confirm("Удалить этот кит без возможности восстановления?")) return

    setDeletingId(id)
    try {
      const res = await authorizedFetch(`/api/v1/kits/${id}`, { method: "DELETE" })
      if (!res.ok && res.status !== 204) {
        throw new Error("Не удалось удалить кит")
      }
      setItems((prev) => prev.filter((k) => k.id !== id))
    } catch {
      alert("Не удалось удалить кит. Попробуйте ещё раз.")
    } finally {
      setDeletingId(null)
    }
  }

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border py-16 text-center">
        <p className="font-medium">Пока нет загруженных китов</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Загрузите свой первый кит, чтобы он появился здесь.
        </p>
        <Button render={<Link href="/upload" />} size="lg" className="mt-5 h-11 px-5">
          <Plus className="size-4" />
          Загрузить кит
        </Button>
      </div>
    )
  }

  return (
    <>
    <ul className="flex flex-col gap-3">
      {items.map((kit) => (
        <li
          key={kit.id}
          className="flex items-center gap-4 rounded-2xl border border-border bg-card p-3 sm:p-4"
        >
          <Link
            href={`/kit/${kit.id}`}
            className="relative size-16 shrink-0 overflow-hidden rounded-xl border border-border sm:size-20"
          >
            <Image
              src={kit.cover || "/placeholder.svg"}
              alt={`Обложка кита ${kit.title}`}
              fill
              sizes="80px"
              className="object-cover"
            />
          </Link>

          <div className="min-w-0 flex-1">
            <Link href={`/kit/${kit.id}`} className="block">
              <h3 className="truncate font-semibold tracking-tight hover:text-primary">
                {kit.title}
              </h3>
            </Link>
            <p className="mt-0.5 text-sm text-muted-foreground">{kit.genre}</p>
            {kit.status && kit.status !== "ready" && (
              <p
                className={
                  kit.status === "failed"
                    ? "mt-1 text-xs font-medium text-destructive"
                    : "mt-1 text-xs font-medium text-muted-foreground"
                }
              >
                {kit.status === "pending" && "Ожидает обработки…"}
                {kit.status === "processing" && "Обрабатывается…"}
                {kit.status === "failed" && (kit.errorMessage || "Ошибка обработки")}
              </p>
            )}
            <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <Music2 className="size-3.5" /> {kit.soundCount} звуков
              </span>
              <span className="inline-flex items-center gap-1">
                <Download className="size-3.5" /> {formatCount(kit.downloads)}
              </span>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <Button
              variant="outline"
              size="icon-lg"
              aria-label={`Редактировать ${kit.title}`}
              onClick={() => setEditingKit(kit)}
            >
              <Pencil className="size-4" />
            </Button>
            <Button
              variant="destructive"
              size="icon-lg"
              aria-label={`Удалить ${kit.title}`}
              onClick={() => remove(kit.id)}
              disabled={deletingId === kit.id}
            >
              <Trash2 className="size-4" />
            </Button>
          </div>
        </li>
      ))}
    </ul>

    {editingKit && (
      <EditKitDialog
        kit={editingKit}
        open={editingKit !== null}
        onOpenChange={(open) => {
          if (!open) setEditingKit(null)
        }}
        onSaved={(updated) => {
          setItems((prev) => prev.map((k) => (k.id === updated.id ? updated : k)))
        }}
      />
    )}
    </>
  )
}
