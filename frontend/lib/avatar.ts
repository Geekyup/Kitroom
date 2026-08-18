const AVATAR_PALETTE = [
  "#F43F5E",
  "#F97316",
  "#F59E0B",
  "#84CC16",
  "#10B981",
  "#14B8A6",
  "#06B6D4",
  "#3B82F6",
  "#6366F1",
  "#8B5CF6",
  "#D946EF",
  "#EC4899",
] as const

function hashString(input: string): number {
  let hash = 0
  for (let i = 0; i < input.length; i++) {
    hash = (hash << 5) - hash + input.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

function colorForUsername(username: string): string {
  const index = hashString(username.toLowerCase()) % AVATAR_PALETTE.length
  return AVATAR_PALETTE[index]
}

function initialsForUsername(username: string): string {
  const trimmed = username.trim()
  if (!trimmed) return "?"
  return trimmed.slice(0, 2).toUpperCase()
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
}

export function avatarPlaceholderFor(username: string): string {
  const initials = escapeXml(initialsForUsername(username))
  const bgColor = colorForUsername(username)

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">
<rect width="96" height="96" fill="${bgColor}"/>
<text x="48" y="48" text-anchor="middle" dominant-baseline="central" font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif" font-size="38" font-weight="600" fill="#ffffff">${initials}</text>
</svg>`

  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}