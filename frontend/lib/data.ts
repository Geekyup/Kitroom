export type SoundType = "kick" | "snare" | "hat" | "clap" | "perc"

export type SoundFile = {
  id: string
  name: string
  type: SoundType
  duration: string
}

export type KitFolder = {
  name: string
  files: SoundFile[]
}

export type Kit = {
  id: string
  title: string
  author: string
  cover: string
  genre: string
  tags: string[]
  soundCount: number
  downloads: number
  sizeMb: number
  description: string
  folders: KitFolder[]
  status?: "pending" | "processing" | "ready" | "failed"
  errorMessage?: string | null
}

export const GENRES = [
  "Все жанры",
  "Trap",
  "Lo-Fi",
  "House",
  "Boom Bap",
  "Techno",
  "Drill",
] as const

const FOLDER_LABELS: Record<SoundType, string> = {
  kick: "Kicks",
  snare: "Snares",
  hat: "Hats",
  clap: "Claps",
  perc: "Percussion",
}

function makeFiles(prefix: string, type: SoundType, count: number): SoundFile[] {
  const durations = ["0:01", "0:01", "0:02", "0:01", "0:03", "0:02"]
  return Array.from({ length: count }).map((_, i) => ({
    id: `${prefix}-${type}-${i + 1}`,
    name: `${prefix}_${FOLDER_LABELS[type]}_${String(i + 1).padStart(2, "0")}.wav`,
    type,
    duration: durations[i % durations.length],
  }))
}

function buildFolders(
  prefix: string,
  counts: Partial<Record<SoundType, number>>,
): KitFolder[] {
  const order: SoundType[] = ["kick", "snare", "hat", "clap", "perc"]
  return order
    .filter((t) => (counts[t] ?? 0) > 0)
    .map((t) => ({
      name: FOLDER_LABELS[t],
      files: makeFiles(prefix, t, counts[t] as number),
    }))
}

export const KITS: Kit[] = [
  {
    id: "midnight-trap",
    title: "Midnight Trap",
    author: "NOVAA",
    cover: "/covers/midnight-trap.png",
    genre: "Trap",
    tags: ["808", "trap", "dark", "hard"],
    soundCount: 42,
    downloads: 12840,
    sizeMb: 128,
    description:
      "Тёмный трап-кит с жирными 808-ми, резкими снейрами и воздушными хэтами. Всё нарезано и отстроено по тональности, готово к загрузке в вашу DAW.",
    folders: buildFolders("Midnight", { kick: 8, snare: 9, hat: 12, clap: 6, perc: 7 }),
  },
  {
    id: "lofi-dust",
    title: "Lo-Fi Dust",
    author: "kotori",
    cover: "/covers/lofi-dust.png",
    genre: "Lo-Fi",
    tags: ["lofi", "vinyl", "warm", "chill"],
    soundCount: 36,
    downloads: 9420,
    sizeMb: 96,
    description:
      "Тёплые пыльные сэмплы с виниловым характером. Мягкие кики, шуршащие перкуссии и приглушённые снейры для расслабленных битов.",
    folders: buildFolders("Dust", { kick: 7, snare: 8, hat: 10, clap: 4, perc: 7 }),
  },
  {
    id: "house-motion",
    title: "House Motion",
    author: "Elias R.",
    cover: "/covers/house-motion.png",
    genre: "House",
    tags: ["house", "groove", "punchy", "club"],
    soundCount: 48,
    downloads: 15310,
    sizeMb: 154,
    description:
      "Плотный набор для хауса: качающие кики, звонкие клэпы и открытые хэты. Отлично ложится в клубные грувы на 124–128 BPM.",
    folders: buildFolders("Motion", { kick: 10, snare: 8, hat: 14, clap: 8, perc: 8 }),
  },
  {
    id: "boom-bap",
    title: "Boom Bap Heritage",
    author: "DJ Krest",
    cover: "/covers/boom-bap.png",
    genre: "Boom Bap",
    tags: ["boombap", "90s", "dusty", "sampled"],
    soundCount: 30,
    downloads: 7280,
    sizeMb: 74,
    description:
      "Классические ударные в духе 90-х: сэмплированные кики и снейры с характером, зернистые перкуссии и живой свинг.",
    folders: buildFolders("Heritage", { kick: 6, snare: 8, hat: 8, clap: 3, perc: 5 }),
  },
  {
    id: "techno-grid",
    title: "Techno Grid",
    author: "MODULA",
    cover: "/covers/techno-grid.png",
    genre: "Techno",
    tags: ["techno", "industrial", "analog", "raw"],
    soundCount: 54,
    downloads: 10960,
    sizeMb: 176,
    description:
      "Сырые аналоговые ударные для техно. Мощные кики, металлические перкуссии и шумовые текстуры для гипнотических лупов.",
    folders: buildFolders("Grid", { kick: 12, snare: 9, hat: 15, clap: 8, perc: 10 }),
  },
  {
    id: "drill-shadow",
    title: "Drill Shadow",
    author: "NOVAA",
    cover: "/covers/drill-shadow.png",
    genre: "Drill",
    tags: ["drill", "uk", "sliding808", "dark"],
    soundCount: 40,
    downloads: 8630,
    sizeMb: 118,
    description:
      "Мрачный дрилл-кит со скользящими 808-ми, острыми хэтами с триолями и жёсткими снейрами. Для тёмных агрессивных битов.",
    folders: buildFolders("Shadow", { kick: 8, snare: 8, hat: 13, clap: 5, perc: 6 }),
  },
]

export function getKit(id: string): Kit | undefined {
  return KITS.find((k) => k.id === id)
}

export const CURRENT_USER = {
  name: "NOVAA",
  handle: "@novaa",
  avatar: "/avatar.png",
  bio: "Саунд-дизайнер и битмейкер. Делаю тёмные трап и дрилл-киты.",
  kitsUploaded: 2,
  totalDownloads: 21470,
  followers: 3120,
  kitIds: ["midnight-trap", "drill-shadow"],
}

export function formatCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(".0", "")}k`
  return String(n)
}
