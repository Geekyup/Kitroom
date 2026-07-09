"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState, type FormEvent } from "react"
import { SiteHeader } from "@/components/site-header"
import { Button } from "@/components/ui/button"
import { authApi, AuthApiError } from "@/lib/auth"

export default function RegisterPage() {
  const router = useRouter()

  const [email, setEmail] = useState("")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [code, setCode] = useState("")
  const [verifyError, setVerifyError] = useState<string | null>(null)
  const [verifying, setVerifying] = useState(false)
  const [verified, setVerified] = useState(false)
  const [resending, setResending] = useState(false)
  const [resendMessage, setResendMessage] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      await authApi.register(email, username, password)
      setSuccess(true)
    } catch (err) {
      if (err instanceof AuthApiError) {
        setError(err.message)
      } else {
        setError("Что-то пошло не так. Попробуйте ещё раз.")
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function handleVerify(e: FormEvent) {
    e.preventDefault()
    setVerifyError(null)
    setVerifying(true)

    try {
      await authApi.verifyEmail(email, code)
      setVerified(true)
    } catch (err) {
      if (err instanceof AuthApiError) {
        setVerifyError(err.message)
      } else {
        setVerifyError("Что-то пошло не так. Попробуйте ещё раз.")
      }
    } finally {
      setVerifying(false)
    }
  }

  async function handleResend() {
    setResendMessage(null)
    setVerifyError(null)
    setResending(true)

    try {
      await authApi.resendVerification(email)
      setResendMessage("Код отправлен повторно.")
    } catch (err) {
      if (err instanceof AuthApiError) {
        setVerifyError(err.message)
      } else {
        setVerifyError("Что-то пошло не так. Попробуйте ещё раз.")
      }
    } finally {
      setResending(false)
    }
  }

  if (success) {
    if (verified) {
      return (
        <div className="flex min-h-dvh flex-col">
          <SiteHeader />
          <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center px-4 py-16 text-center sm:px-6">
            <h1 className="text-2xl font-semibold tracking-tight">Почта подтверждена</h1>
            <p className="mt-2 text-muted-foreground">
              Аккаунт активирован, можно входить.
            </p>
            <Button render={<Link href="/login" />} size="lg" className="mt-8 h-11 px-6">
              Перейти ко входу
            </Button>
          </main>
        </div>
      )
    }

    return (
      <div className="flex min-h-dvh flex-col">
        <SiteHeader />
        <main className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center px-4 py-16 text-center sm:px-6">
          <h1 className="text-2xl font-semibold tracking-tight">Почти готово</h1>
          <p className="mt-2 text-muted-foreground">
            Мы отправили код подтверждения на {email}. Введите его ниже, чтобы
            активировать аккаунт.
          </p>

          <form onSubmit={handleVerify} className="mt-8 flex w-full flex-col gap-4">
            <div>
              <label htmlFor="code" className="mb-1.5 block text-left text-sm font-medium">
                Код подтверждения
              </label>
              <input
                id="code"
                type="text"
                required
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="h-11 w-full rounded-xl border border-input bg-card px-3.5 text-center text-base tracking-widest outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
                placeholder="123456"
              />
            </div>

            {verifyError && (
              <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {verifyError}
              </p>
            )}
            {resendMessage && (
              <p className="rounded-lg bg-primary/10 px-3 py-2 text-sm text-primary">
                {resendMessage}
              </p>
            )}

            <Button type="submit" size="lg" className="h-11" disabled={verifying}>
              {verifying ? "Проверяем…" : "Подтвердить"}
            </Button>
          </form>

          <button
            type="button"
            onClick={handleResend}
            disabled={resending}
            className="mt-4 text-sm font-medium text-primary hover:underline disabled:opacity-50"
          >
            {resending ? "Отправляем…" : "Отправить код ещё раз"}
          </button>
        </main>
      </div>
    )
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />

      <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 py-16 sm:px-6">
        <h1 className="text-2xl font-semibold tracking-tight">Регистрация</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Создайте аккаунт, чтобы загружать свои драм-киты.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-11 w-full rounded-xl border border-input bg-card px-3.5 text-base outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="username" className="mb-1.5 block text-sm font-medium">
              Никнейм
            </label>
            <input
              id="username"
              type="text"
              required
              minLength={3}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="h-11 w-full rounded-xl border border-input bg-card px-3.5 text-base outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
              placeholder="beatmaker_2000"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium">
              Пароль
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-11 w-full rounded-xl border border-input bg-card px-3.5 text-base outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
              placeholder="Минимум 8 символов"
            />
          </div>

          {error && (
            <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" size="lg" className="mt-2 h-11" disabled={submitting}>
            {submitting ? "Создаём аккаунт…" : "Зарегистрироваться"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Войти
          </Link>
        </p>
      </main>

    </div>
  )
}
