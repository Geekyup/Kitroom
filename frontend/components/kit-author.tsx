"use client"

import Image from "next/image"
import Link from "next/link"
import { avatarForUser } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"

type KitAuthorProps = {
  username: string
  avatarPath?: string | null
  size?: "sm" | "md"
  /** Останавливает всплытие клика — нужно, когда автор рендерится
   * внутри другой кликабельной ссылки (например, карточки кита). */
  stopPropagation?: boolean
}

const SIZE_CLASSES = {
  sm: { avatar: "size-5", text: "text-sm" },
  md: { avatar: "size-8", text: "text-base" },
} as const

export function KitAuthor({ username, avatarPath, size = "sm", stopPropagation }: KitAuthorProps) {
  const sizes = SIZE_CLASSES[size]
  const { user } = useAuth()

  // Если это кит текущего залогиненного пользователя — ведём в его личный
  // кабинет /profile (со статистикой и редактированием), а не на публичную
  // страницу /profile/[username], которую видят посторонние.
  const isOwnProfile = !!user && user.username.toLowerCase() === username.toLowerCase()
  const href = isOwnProfile ? "/profile" : `/profile/${encodeURIComponent(username)}`

  return (
    <Link
      href={href}
      onClick={stopPropagation ? (e) => e.stopPropagation() : undefined}
      className="group/author inline-flex min-w-0 items-center gap-2 hover:underline"
    >
      <span className={`relative shrink-0 overflow-hidden rounded-full ${sizes.avatar}`}>
        <Image
          src={avatarForUser(avatarPath)}
          alt={`Аватар ${username}`}
          fill
          sizes="32px"
          className="object-cover"
        />
      </span>
      <span className={`truncate text-muted-foreground group-hover/author:text-foreground ${sizes.text}`}>
        {username}
      </span>
    </Link>
  )
}