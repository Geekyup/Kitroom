"use client"

import { useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { UploadCloud, FileArchive, X, Image as ImageIcon, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { GENRES } from "@/lib/data"
import { authorizedFetch } from "@/lib/auth"

type Stage = "idle" | "creating" | "uploading" | "confirming" | "done" | "error"

export function UploadForm() {
  const router = useRouter()

  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [cover, setCover] = useState<File | null>(null)
  const [stage, setStage] = useState<Stage>("idle")
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)

  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [genre, setGenre] = useState<string>("Trap")
  const [tags, setTags] = useState("")

  const inputRef = useRef<HTMLInputElement>(null)
  const coverInputRef = useRef<HTMLInputElement>(null)

  function handleFiles(files: FileList | null) {
    const f = files?.[0]
    if (f) setFile(f)
  }

  /**
   * PUT файла напрямую в S3 (Railway Bucket) с прогрессом через XHR.
   * fetch() не отдаёт upload progress, поэтому для прогресс-бара нужен XHR.
   */
  function putToStorage(url: string, body: File, onProgress: (pct: number) => void): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open("PUT", url, true)
      xhr.setRequestHeader("Content-Type", body.type || "application/octet-stream")

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress(Math.round((event.loaded / event.total) * 100))
        }
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          onProgress(100)
          resolve()
        } else {
          reject(new Error(`Хранилище вернуло ошибку: ${xhr.status}`))
        }
      }

      xhr.onerror = () => reject(new Error("Сетевая ошибка при загрузке файла в хранилище"))
      xhr.onabort = () => reject(new Error("Загрузка отменена"))

      xhr.send(body)
    })
  }

  async function startUpload(e: React.FormEvent) {
    e.preventDefault()
    setErrorMessage(null)

    if (!file) {
      inputRef.current?.click()
      return
    }
    if (!title.trim()) {
      setErrorMessage("Укажите название кита.")
      return
    }

    setProgress(0)

    try {
      // Шаг 1 — создаём кит в БД (status=pending) и получаем presigned URL.
      // Файл ещё не загружен, сервер тут почти не тратит времени.
      setStage("creating")
      const initRes = await authorizedFetch("/api/v1/kits/upload-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          genre,
          tags,
          description,
          content_type: file.type || "application/zip",
        }),
      })

      if (!initRes.ok) {
        let detail = initRes.statusText
        try {
          const body = await initRes.json()
          detail = body.detail ?? detail
        } catch {
          // тело не JSON
        }
        throw new Error(detail)
      }

      const { kit_id, upload_url } = await initRes.json()

      // Шаг 2 — грузим файл НАПРЯМУЮ в S3, минуя наш сервер целиком.
      // Именно это убирает зависания через Docker/сервер на больших файлах.
      setStage("uploading")
      await putToStorage(upload_url, file, setProgress)

      // Шаг 2.5 — если есть обложка, грузим её тем же способом.
      if (cover) {
        const coverInitRes = await authorizedFetch(
          `/api/v1/kits/${kit_id}/cover-upload-url?content_type=${encodeURIComponent(
            cover.type || "image/jpeg"
          )}`,
          { method: "POST" }
        )
        if (coverInitRes.ok) {
          const { upload_url: coverUploadUrl, object_key } = await coverInitRes.json()
          await putToStorage(coverUploadUrl, cover, () => {})
          await authorizedFetch(`/api/v1/kits/${kit_id}/cover-confirm-upload`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ object_key }),
          })
        }
        // Если обложка не загрузилась — не блокируем публикацию кита из-за неё.
      }

      // Шаг 3 — подтверждаем: сервер проверит через head_object, что файл
      // реально долетел, и только тогда поставит job в очередь на распаковку.
      setStage("confirming")
      const confirmRes = await authorizedFetch(`/api/v1/kits/${kit_id}/confirm-upload`, {
        method: "POST",
      })

      if (!confirmRes.ok) {
        let detail = confirmRes.statusText
        try {
          const body = await confirmRes.json()
          detail = body.detail ?? detail
        } catch {
          // тело не JSON
        }
        throw new Error(detail)
      }

      setStage("done")
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Не удалось загрузить кит. Попробуйте ещё раз.")
      setStage("error")
    }
  }

  function reset() {
    setFile(null)
    setCover(null)
    setTitle("")
    setDescription("")
    setTags("")
    setStage("idle")
    setErrorMessage(null)
    setProgress(0)
  }

  const formatSize = (bytes: number) =>
    bytes > 1024 * 1024
      ? `${(bytes / 1024 / 1024).toFixed(1)} МБ`
      : `${Math.max(1, Math.round(bytes / 1024))} КБ`

  const isBusy = stage === "creating" || stage === "uploading" || stage === "confirming"

  const stageLabel: Record<string, string> = {
    creating: "Создаём кит…",
    uploading: `Загружаем файл в хранилище… ${progress}%`,
    confirming: "Проверяем загрузку и ставим в очередь…",
  }

  if (stage === "done") {
    return (
      <div className="rounded-2xl border border-border bg-card p-8 text-center">
        <span className="mx-auto flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <Check className="size-7" />
        </span>
        <h2 className="mt-4 text-xl font-semibold">Кит загружен</h2>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
          Файлы отправлены на обработку. Кит появится в вашем профиле, как только
          обработка завершится.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button size="lg" className="h-11 px-5" onClick={reset}>
            Загрузить ещё
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="h-11 px-5"
            onClick={() => router.push("/profile")}
          >
            В профиль
          </Button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={startUpload} className="grid grid-cols-1 gap-8 lg:grid-cols-[1.1fr_1fr]">
      {/* Dropzone + progress */}
      <div className="flex flex-col gap-4">
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            handleFiles(e.dataTransfer.files)
          }}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click()
          }}
          className={
            "flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-colors " +
            (dragging
              ? "border-primary bg-accent"
              : "border-border bg-card hover:border-primary/50 hover:bg-secondary/40")
          }
        >
          <input
            ref={inputRef}
            type="file"
            accept=".zip"
            className="sr-only"
            onChange={(e) => handleFiles(e.target.files)}
          />
          {file ? (
            <div className="flex w-full max-w-sm items-center gap-3 rounded-xl border border-border bg-background p-3 text-left">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <FileArchive className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  setFile(null)
                }}
                aria-label="Удалить файл"
                className="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            </div>
          ) : (
            <>
              <span className="flex size-14 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
                <UploadCloud className="size-7" />
              </span>
              <p className="mt-4 font-medium">Перетащите ZIP-архив сюда</p>
              <p className="mt-1 text-sm text-muted-foreground">
                или нажмите, чтобы выбрать файл · до 500 МБ
              </p>
            </>
          )}
        </div>

        {isBusy && (
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <span className="size-2 animate-pulse rounded-full bg-primary" />
              {stageLabel[stage]}
            </div>
            {stage === "uploading" && (
              <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-150"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}
          </div>
        )}

        {errorMessage && (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {errorMessage}
          </p>
        )}
      </div>

      {/* Fields */}
      <div className="flex flex-col gap-5">
        <Field label="Название кита">
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Например, Midnight Trap"
            className="h-11 w-full rounded-lg border border-input bg-card px-3.5 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
          />
        </Field>

        <Field label="Описание">
          <textarea
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Расскажите, что внутри: характер звуков, темп, вайб…"
            className="w-full resize-none rounded-lg border border-input bg-card p-3.5 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
          />
        </Field>

        <Field label="Жанр">
          <div className="flex flex-wrap gap-2">
            {GENRES.filter((g) => g !== "Все жанры").map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGenre(g)}
                aria-pressed={genre === g}
                className={
                  "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors " +
                  (genre === g
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:text-foreground")
                }
              >
                {g}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Теги (через запятую)">
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="808, dark, hard"
            className="h-11 w-full rounded-lg border border-input bg-card px-3.5 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
          />
        </Field>

        <Field label="Обложка">
          <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-border bg-card p-3 text-sm text-muted-foreground transition-colors hover:border-primary/50">
            <span className="flex size-10 items-center justify-center rounded-lg bg-secondary text-foreground">
              <ImageIcon className="size-4" />
            </span>
            {cover ? cover.name : "Загрузить изображение обложки (JPG, PNG)"}
            <input
              ref={coverInputRef}
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(e) => setCover(e.target.files?.[0] ?? null)}
            />
          </label>
        </Field>

        <Button type="submit" size="lg" className="mt-1 h-12 text-base" disabled={isBusy}>
          {isBusy ? "Загрузка…" : "Опубликовать кит"}
        </Button>
      </div>
    </form>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium">{label}</label>
      {children}
    </div>
  )
}