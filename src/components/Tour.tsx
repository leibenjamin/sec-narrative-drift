import { useEffect, useRef, useState } from "react"

type TourStep = {
  targetId: string
  title: string
  body: string
}

type TourProps = {
  isOpen: boolean
  steps: TourStep[]
  onClose: () => void
}

const CARD_WIDTH = 260
const CARD_HEIGHT = 150
const PADDING = 12

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

export default function Tour({ isOpen, steps, onClose }: TourProps) {
  const [index, setIndex] = useState(0)
  const [position, setPosition] = useState({ top: PADDING, left: PADDING })
  const activeRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!isOpen || steps.length === 0) return undefined

    const update = () => {
      const step = steps[index] ?? steps[0]
      const target = document.getElementById(step.targetId)

      if (activeRef.current && activeRef.current !== target) {
        activeRef.current.removeAttribute("data-tour-active")
      }

      if (!target) {
        setPosition({ top: PADDING, left: PADDING })
        return
      }

      activeRef.current = target
      target.setAttribute("data-tour-active", "true")
      target.scrollIntoView({ behavior: "smooth", block: "center" })

      const rect = target.getBoundingClientRect()
      let left = rect.left + rect.width + PADDING
      if (left + CARD_WIDTH > window.innerWidth - PADDING) {
        left = rect.left - CARD_WIDTH - PADDING
      }
      left = clamp(left, PADDING, window.innerWidth - CARD_WIDTH - PADDING)

      let top = rect.top
      if (top + CARD_HEIGHT > window.innerHeight - PADDING) {
        top = window.innerHeight - CARD_HEIGHT - PADDING
      }
      top = clamp(top, PADDING, window.innerHeight - CARD_HEIGHT - PADDING)

      setPosition({ top, left })
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIndex(0)
        onClose()
      }
    }

    update()
    window.addEventListener("resize", update)
    window.addEventListener("scroll", update, true)
    window.addEventListener("keydown", handleKeyDown)

    return () => {
      window.removeEventListener("resize", update)
      window.removeEventListener("scroll", update, true)
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [index, isOpen, onClose, steps])

  useEffect(() => {
    if (isOpen) return undefined
    if (activeRef.current) {
      activeRef.current.removeAttribute("data-tour-active")
    }
    return undefined
  }, [isOpen])

  if (!isOpen || steps.length === 0) return null

  const step = steps[index] ?? steps[0]
  const stepCount = steps.length

  function handleAdvance() {
    if (index >= stepCount - 1) {
      setIndex(0)
      onClose()
      return
    }
    setIndex((prev) => Math.min(prev + 1, stepCount - 1))
  }

  return (
    <div
      className="fixed z-50 max-w-xs rounded-lg border border-black/20 bg-white p-4 text-sm shadow-lg"
      style={{ top: position.top, left: position.left }}
      onClick={handleAdvance}
      role="dialog"
      aria-live="polite"
    >
      <div className="text-[10px] uppercase tracking-wider opacity-60">
        {index + 1}/{stepCount}
      </div>
      <div className="mt-1 text-sm font-semibold">{step.title}</div>
      <p className="mt-2 text-sm opacity-80">{step.body}</p>
    </div>
  )
}
