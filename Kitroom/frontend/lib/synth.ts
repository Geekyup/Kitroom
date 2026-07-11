import type { SoundType } from "./data"

let ctx: AudioContext | null = null

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null
  if (!ctx) {
    const AC = window.AudioContext || (window as any).webkitAudioContext
    if (!AC) return null
    ctx = new AC()
  }
  if (ctx.state === "suspended") void ctx.resume()
  return ctx
}

function noiseBuffer(ac: AudioContext, duration: number): AudioBuffer {
  const length = Math.floor(ac.sampleRate * duration)
  const buffer = ac.createBuffer(1, length, ac.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1
  return buffer
}

/**
 * Synthesize a short drum sound of the given type using the Web Audio API.
 * Returns the approximate duration in seconds so callers can time UI state.
 */
export function playDrum(type: SoundType): number {
  const ac = getCtx()
  if (!ac) return 0.3
  const now = ac.currentTime
  const master = ac.createGain()
  master.connect(ac.destination)
  master.gain.value = 0.9

  switch (type) {
    case "kick": {
      const osc = ac.createOscillator()
      const gain = ac.createGain()
      osc.type = "sine"
      osc.frequency.setValueAtTime(150, now)
      osc.frequency.exponentialRampToValueAtTime(48, now + 0.28)
      gain.gain.setValueAtTime(1, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4)
      osc.connect(gain).connect(master)
      osc.start(now)
      osc.stop(now + 0.42)
      return 0.42
    }
    case "snare": {
      const noise = ac.createBufferSource()
      noise.buffer = noiseBuffer(ac, 0.25)
      const hp = ac.createBiquadFilter()
      hp.type = "highpass"
      hp.frequency.value = 1400
      const ng = ac.createGain()
      ng.gain.setValueAtTime(0.9, now)
      ng.gain.exponentialRampToValueAtTime(0.001, now + 0.2)
      noise.connect(hp).connect(ng).connect(master)

      const osc = ac.createOscillator()
      const og = ac.createGain()
      osc.type = "triangle"
      osc.frequency.value = 190
      og.gain.setValueAtTime(0.6, now)
      og.gain.exponentialRampToValueAtTime(0.001, now + 0.13)
      osc.connect(og).connect(master)

      noise.start(now)
      noise.stop(now + 0.25)
      osc.start(now)
      osc.stop(now + 0.15)
      return 0.25
    }
    case "hat": {
      const noise = ac.createBufferSource()
      noise.buffer = noiseBuffer(ac, 0.08)
      const hp = ac.createBiquadFilter()
      hp.type = "highpass"
      hp.frequency.value = 7000
      const ng = ac.createGain()
      ng.gain.setValueAtTime(0.5, now)
      ng.gain.exponentialRampToValueAtTime(0.001, now + 0.06)
      noise.connect(hp).connect(ng).connect(master)
      noise.start(now)
      noise.stop(now + 0.08)
      return 0.09
    }
    case "clap": {
      const hp = ac.createBiquadFilter()
      hp.type = "bandpass"
      hp.frequency.value = 1200
      hp.connect(master)
      const offsets = [0, 0.012, 0.024, 0.045]
      offsets.forEach((off, i) => {
        const noise = ac.createBufferSource()
        noise.buffer = noiseBuffer(ac, 0.1)
        const g = ac.createGain()
        const start = now + off
        g.gain.setValueAtTime(i === offsets.length - 1 ? 0.7 : 0.4, start)
        g.gain.exponentialRampToValueAtTime(0.001, start + (i === offsets.length - 1 ? 0.18 : 0.03))
        noise.connect(g).connect(hp)
        noise.start(start)
        noise.stop(start + 0.2)
      })
      return 0.24
    }
    case "perc":
    default: {
      const osc = ac.createOscillator()
      const gain = ac.createGain()
      osc.type = "square"
      osc.frequency.setValueAtTime(420, now)
      osc.frequency.exponentialRampToValueAtTime(220, now + 0.12)
      gain.gain.setValueAtTime(0.5, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18)
      const bp = ac.createBiquadFilter()
      bp.type = "bandpass"
      bp.frequency.value = 900
      osc.connect(bp).connect(gain).connect(master)
      osc.start(now)
      osc.stop(now + 0.2)
      return 0.2
    }
  }
}
