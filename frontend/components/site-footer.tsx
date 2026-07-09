import Link from "next/link"

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t border-border">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
        <div className="flex items-center gap-2">
          <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <svg viewBox="0 0 24 24" className="size-3.5" fill="none" aria-hidden="true">
              <circle cx="8" cy="16" r="3" fill="currentColor" />
              <path d="M11 16V5l9-2v9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <span className="text-sm font-semibold">Kitroom</span>
          <span className="text-sm text-muted-foreground">— библиотека драм-китов</span>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
          <Link href="/" className="transition-colors hover:text-foreground">Главная</Link>
          <Link href="/catalog" className="transition-colors hover:text-foreground">Каталог</Link>
          <Link href="/upload" className="transition-colors hover:text-foreground">Загрузить</Link>
          <Link href="/profile" className="transition-colors hover:text-foreground">Профиль</Link>
        </nav>
        <p className="text-sm text-muted-foreground">© 2026 Kitroom</p>
      </div>
    </footer>
  )
}
