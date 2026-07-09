"use client"

import { useState, type FormEvent } from "react"
import { Dialog } from "@base-ui/react/dialog"
import { X } from "lucide-react"
import type { Kit } from "@/lib/data"
import { GENRES } from "@/lib/data"
import { Button } from "@/components/ui/button"
import { authorizedFetch } from "@/lib/auth"

const inputClass =
  "h-11 w-full rounded-xl border border-input bg-card px-3.5 text-base outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"

export function EditKitDialog({
  kit,
  open,
  onOpenChange,
  onSaved,
}: {
  kit: Kit
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved: (updated: Kit) => void
}) {
  const [title, setTitle] = useState(kit.title)
  const [genre, setGenre] = useState(kit.genre)
  const [tags, setTags] = useState(kit.tags.join(", "))
  const [description, setDescription] = useState(kit.description)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const genreOptions = GENRES.filter((g) => g !== "Все жанры")

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSaving(true)

    const tagList = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)

    try {
      const res = await authorizedFetch(`/api/v1/kits/${kit.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          genre,
          tags: tagList,
          description: description || null,
        }),
      })

      if (!res.ok) {
        let detail = res.statusText
        try {
          const body = await res.json()
          detail = body.detail ?? detail
        } catch {
          // тело не JSON
        }
        throw new Error(detail)
      }

      onSaved({ ...kit, title, genre, tags: tagList, description })
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить изменения")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/50 transition-opacity data-[ending-style]:opacity-0 data-[starting-style]:opacity-0" />
        <Dialog.Popup className="fixed top-1/2 left-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-card p-6 shadow-xl outline-none transition-all data-[ending-style]:scale-95 data-[ending-style]:opacity-0 data-[starting-style]:scale-95 data-[starting-style]:opacity-0">
          <div className="mb-5 flex items-center justify-between">
            <Dialog.Title className="text-lg font-semibold tracking-tight">
              Редактировать кит
            </Dialog.Title>
            <Dialog.Close
              aria-label="Закрыть"
              className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="size-4" />
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label htmlFor="edit-title" className="mb-1.5 block text-sm font-medium">
                Название
              </label>
              <input
                id="edit-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className={inputClass}
              />
            </div>

            <div>
              <label htmlFor="edit-genre" className="mb-1.5 block text-sm font-medium">
                Жанр
              </label>
              <select
                id="edit-genre"
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                required
                className={inputClass}
              >
                {genreOptions.map((g) => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="edit-tags" className="mb-1.5 block text-sm font-medium">
                Теги (через запятую)
              </label>
              <input
                id="edit-tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="trap, 808, dark"
                className={inputClass}
              />
            </div>

            <div>
              <label htmlFor="edit-description" className="mb-1.5 block text-sm font-medium">
                Описание
              </label>
              <textarea
                id="edit-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full resize-none rounded-xl border border-input bg-card px-3.5 py-2.5 text-base outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="mt-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={() => onOpenChange(false)}
                disabled={saving}
              >
                Отмена
              </Button>
              <Button type="submit" size="lg" disabled={saving}>
                {saving ? "Сохранение…" : "Сохранить"}
              </Button>
            </div>
          </form>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
