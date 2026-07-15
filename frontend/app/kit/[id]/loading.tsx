import { SiteHeader } from "@/components/site-header"

export default function KitLoading() {
  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6 h-5 w-24 animate-pulse rounded bg-muted" />

        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:gap-8">
          <div className="aspect-square w-full shrink-0 animate-pulse rounded-2xl bg-muted sm:w-56 lg:w-64" />

          <div className="flex-1 space-y-4">
            <div className="h-8 w-2/3 animate-pulse rounded bg-muted" />
            <div className="h-5 w-32 animate-pulse rounded bg-muted" />
            <div className="flex gap-3">
              <div className="h-9 w-28 animate-pulse rounded-lg bg-muted" />
              <div className="h-9 w-28 animate-pulse rounded-lg bg-muted" />
            </div>
          </div>
        </div>

        <div className="mt-10 space-y-2">
          <div className="h-6 w-40 animate-pulse rounded bg-muted" />
          <div className="h-12 w-full animate-pulse rounded-xl bg-muted" />
          <div className="h-12 w-full animate-pulse rounded-xl bg-muted" />
          <div className="h-12 w-full animate-pulse rounded-xl bg-muted" />
        </div>
      </main>
    </div>
  )
}