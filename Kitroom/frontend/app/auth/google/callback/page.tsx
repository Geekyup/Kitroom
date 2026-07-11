"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { SiteHeader } from "@/components/site-header"
import { storeTokens } from "@/lib/auth"
import { useAuth } from "@/lib/auth-context"

export default function GoogleCallbackPage() {
  const router = useRouter()
  const { refreshUser } = useAuth()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Бэкенд редиректит сюда с токенами в hash-фрагменте
    // (#access_token=...&refresh_token=...), а не в query-параметрах —
    // фрагмент не уходит на сервер, поэтому токены не попадают ни в какие логи.
    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : window.location.hash

    const params = new URLSearchParams(hash)
    const accessToken = params.get("access_token")
    const refreshToken = params.get("refresh_token")

    if (!accessToken || !refreshToken) {
      setError("Не удалось войти через Google. Попробуйте ещё раз.")
      return
    }

    storeTokens({ access_token: accessToken, refresh_token: refreshToken })

    refreshUser().then(() => {
      router.replace("/profile")
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center px-4 py-16 text-center">
        {error ? (
          <>
            <p className="text-sm text-destructive">{error}</p>
            <a href="/login" className="mt-4 text-sm font-medium text-primary hover:underline">
              Вернуться на страницу входа
            </a>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">Входим через Google…</p>
        )}
      </main>
    </div>
  )
}