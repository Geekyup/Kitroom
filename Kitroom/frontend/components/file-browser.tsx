"use client"

import { useRef, useState } from "react"
import { ChevronRight, Play, Pause, Folder, FolderOpen } from "lucide-react"
import { absoluteMediaUrl, type ApiNode } from "@/lib/api"

function formatDuration(ms: number | null): string {
  if (ms === null) return "--:--"
  const totalSeconds = Math.round(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, "0")}`
}

export function FileBrowser({ nodes }: { nodes: ApiNode[] }) {
  const [open, setOpen] = useState<Record<number, boolean>>(
    nodes[0] ? { [nodes[0].id]: true } : {},
  )
  const [playingId, setPlayingId] = useState<number | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  function toggleFolder(id: number) {
    setOpen((o) => ({ ...o, [id]: !o[id] }))
  }

  function togglePlay(node: ApiNode) {
    if (!node.sound_url) return

    if (playingId === node.id) {
      audioRef.current?.pause()
      setPlayingId(null)
      return
    }

    if (audioRef.current) {
      audioRef.current.pause()
    }

    const audio = new Audio(absoluteMediaUrl(node.sound_url))
    audio.onended = () => setPlayingId(null)
    audioRef.current = audio
    audio.play()
    setPlayingId(node.id)
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card">
      {nodes.map((node) => (
        <TreeNode
          key={node.id}
          node={node}
          depth={0}
          open={open}
          onToggleFolder={toggleFolder}
          playingId={playingId}
          onTogglePlay={togglePlay}
        />
      ))}
    </div>
  )
}

function TreeNode({
  node,
  depth,
  open,
  onToggleFolder,
  playingId,
  onTogglePlay,
}: {
  node: ApiNode
  depth: number
  open: Record<number, boolean>
  onToggleFolder: (id: number) => void
  playingId: number | null
  onTogglePlay: (node: ApiNode) => void
}) {
  if (node.node_type === "folder") {
    const isOpen = open[node.id]
    return (
      <div className="border-b border-border last:border-b-0">
        <button
          type="button"
          onClick={() => onToggleFolder(node.id)}
          aria-expanded={isOpen}
          className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-secondary/60"
          style={{ paddingLeft: `${16 + depth * 20}px` }}
        >
          <ChevronRight
            className={
              "size-4 shrink-0 text-muted-foreground transition-transform " +
              (isOpen ? "rotate-90" : "")
            }
          />
          {isOpen ? (
            <FolderOpen className="size-5 shrink-0 text-primary" />
          ) : (
            <Folder className="size-5 shrink-0 text-muted-foreground" />
          )}
          <span className="font-medium">{node.name}</span>
          <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-muted-foreground">
            {node.children.length}
          </span>
        </button>

        {isOpen && (
          <div className="pb-2">
            {node.children.map((child) => (
              <TreeNode
                key={child.id}
                node={child}
                depth={depth + 1}
                open={open}
                onToggleFolder={onToggleFolder}
                playingId={playingId}
                onTogglePlay={onTogglePlay}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  const isPlaying = playingId === node.id

  return (
    <button
      type="button"
      onClick={() => onTogglePlay(node)}
      disabled={!node.sound_url}
      aria-label={isPlaying ? `Остановить ${node.name}` : `Проиграть ${node.name}`}
      className={
        "group flex w-full items-center gap-3 py-2 pr-4 text-left transition-colors " +
        (isPlaying ? "bg-accent" : "hover:bg-secondary/70")
      }
      style={{ paddingLeft: `${40 + depth * 20}px` }}
    >
      <span
        className={
          "flex size-8 shrink-0 items-center justify-center rounded-full transition-colors " +
          (isPlaying
            ? "bg-primary text-primary-foreground"
            : "bg-secondary text-foreground group-hover:bg-primary group-hover:text-primary-foreground")
        }
      >
        {isPlaying ? (
          <Pause className="size-3.5" />
        ) : (
          <Play className="size-3.5 translate-x-px fill-current" />
        )}
      </span>
      <span
        className={
          "min-w-0 flex-1 truncate font-mono text-sm " +
          (isPlaying ? "text-accent-foreground" : "text-foreground")
        }
      >
        {node.name}
      </span>
      {node.file_format && (
        <span className="hidden shrink-0 rounded bg-secondary px-1.5 py-0.5 text-xs uppercase text-muted-foreground sm:inline">
          {node.file_format}
        </span>
      )}
      <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
        {formatDuration(node.duration_ms)}
      </span>
    </button>
  )
}
