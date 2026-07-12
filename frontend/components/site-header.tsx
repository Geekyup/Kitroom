"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useState } from "react"
import { Search, Upload, User, Menu, X, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth-context"

const NAV = [
  { href: "/", label: "Главная" },
  { href: "/catalog", label: "Каталог" },
]

export function SiteHeader({ initialQuery = "" }: { initialQuery?: string }) {
  const router = useRouter()
  const pathname = usePathname()
  const [query, setQuery] = useState(initialQuery)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, loading, logout } = useAuth()

  // На /catalog уже есть свой поиск с фильтрами по жанру — второй, в шапке,
  // был бы дублем того же самого поля. На /login и /register поиск вообще
  // не по смыслу этих страниц (это служебные auth-экраны, а не часть
  // основного продукта) — так же скрыт, как и на этих страницах не
  // показываются кнопки "Загрузить кит"/профиль.
  const hideSearch = pathname === "/catalog" || pathname === "/login" || pathname === "/register"

  async function handleLogout() {
    await logout()
    setMobileOpen(false)
    router.push("/")
  }

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const q = query.trim()
    router.push(q ? `/catalog?q=${encodeURIComponent(q)}` : "/catalog")
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-4">
          <Link href="/" className="flex shrink-0 items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <svg viewBox="0 0 24 24" className="size-4" fill="none" aria-hidden="true">
                <circle cx="8" cy="16" r="3" fill="currentColor" />
                <path d="M11 16V5l9-2v9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span className="text-lg font-semibold tracking-tight">Kitroom</span>
          </Link>

          <nav className="hidden items-center gap-1 lg:flex">
            {NAV.map((item) => {
              const active = pathname === item.href
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={
                    "rounded-lg px-3 py-2 text-sm font-medium transition-colors " +
                    (active
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground")
                  }
                >
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>

        {!hideSearch && (
          <form onSubmit={submit} className="relative hidden max-w-md flex-1 md:block">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Поиск китов, авторов, тегов…"
              aria-label="Поиск драм-китов"
              className="h-10 w-full rounded-lg border border-input bg-card pr-4 pl-9 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
            />
          </form>
        )}

        <div className="hidden items-center gap-2 md:flex">
          {!loading && user ? (
            <>
              <Button
                render={<Link href="/upload" />}
                variant="outline"
                size="lg"
                className="h-10 px-3"
              >
                <Upload className="size-4" />
                Загрузить кит
              </Button>
              <Button render={<Link href="/profile" />} size="lg" className="h-10 px-3">
                <User className="size-4" />
                {user.username}
              </Button>
              <Button
                variant="outline"
                size="icon-lg"
                className="h-10 w-10"
                onClick={handleLogout}
                aria-label="Выйти"
              >
                <LogOut className="size-4" />
              </Button>
            </>
          ) : !loading ? (
            <>
              <Button render={<Link href="/login" />} variant="outline" size="lg" className="h-10 px-4">
                Войти
              </Button>
              <Button render={<Link href="/register" />} size="lg" className="h-10 px-4">
                Регистрация
              </Button>
            </>
          ) : null}
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen((o) => !o)}
          className="ml-auto flex size-10 items-center justify-center rounded-lg border border-input text-foreground md:hidden"
          aria-label={mobileOpen ? "Закрыть меню" : "Открыть меню"}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="border-t border-border bg-background px-4 pt-3 pb-4 md:hidden">
          {!hideSearch && (
            <form onSubmit={submit} className="relative mb-3">
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Поиск китов, авторов, тегов…"
                aria-label="Поиск драм-китов"
                className="h-11 w-full rounded-lg border border-input bg-card pr-4 pl-9 text-sm shadow-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/20"
              />
            </form>
          )}
          <div className="mb-3 flex flex-col gap-1">
            {NAV.map((item) => {
              const active = pathname === item.href
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  aria-current={active ? "page" : undefined}
                  className={
                    "rounded-lg px-3 py-2.5 text-sm font-medium transition-colors " +
                    (active
                      ? "bg-accent text-accent-foreground"
                      : "text-foreground hover:bg-secondary")
                  }
                >
                  {item.label}
                </Link>
              )
            })}
          </div>
          <div className="flex flex-col gap-2">
            {!loading && user ? (
              <>
                <Button
                  render={<Link href="/upload" onClick={() => setMobileOpen(false)} />}
                  variant="outline"
                  size="lg"
                  className="h-11 w-full justify-start"
                >
                  <Upload className="size-4" />
                  Загрузить кит
                </Button>
                <Button
                  render={<Link href="/profile" onClick={() => setMobileOpen(false)} />}
                  size="lg"
                  className="h-11 w-full justify-start"
                >
                  <User className="size-4" />
                  {user.username}
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  className="h-11 w-full justify-start"
                  onClick={handleLogout}
                >
                  <LogOut className="size-4" />
                  Выйти
                </Button>
              </>
            ) : !loading ? (
              <>
                <Button
                  render={<Link href="/login" onClick={() => setMobileOpen(false)} />}
                  variant="outline"
                  size="lg"
                  className="h-11 w-full justify-start"
                >
                  Войти
                </Button>
                <Button
                  render={<Link href="/register" onClick={() => setMobileOpen(false)} />}
                  size="lg"
                  className="h-11 w-full justify-start"
                >
                  Регистрация
                </Button>
              </>
            ) : null}
          </div>
        </div>
      )}
    </header>
  )
}