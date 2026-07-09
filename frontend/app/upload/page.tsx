"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { SiteHeader } from "@/components/site-header"
import { UploadForm } from "@/components/upload-form"
import { useAuth } from "@/lib/auth-context"

export default function UploadPage() {
  const router = useRouter()
  const { user, loading } = useAuth()

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login")
    }
  }, [loading, user, router])

  if (loading || !user) {
    return (
      <div className="flex min-h-dvh flex-col">
        <SiteHeader />
        <main className="flex-1 px-4 py-16 text-center text-muted-foreground">
          Загрузка…
        </main>
      </div>
    )
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8 max-w-2xl">
          <h1 className="text-3xl font-semibold tracking-tight">Загрузить кит</h1>
          <p className="mt-2 text-muted-foreground">
            Соберите звуки в ZIP-архив с папками (Kicks, Snares, Hats…). Мы
            автоматически разложим их в файловый браузер и покажем превью.
          </p>
        </div>

        <UploadForm />
      </main>

    </div>
  )
}
