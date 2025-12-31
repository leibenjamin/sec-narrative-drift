import { useEffect, useId, useRef, useState, type ReactNode } from "react"

type InlinePopoverProps = {
  label: ReactNode
  ariaLabel: string
  content: ReactNode
  triggerClassName?: string
  panelClassName?: string
  align?: "left" | "right"
  resetKey?: string | number | null
}

export default function InlinePopover({
  label,
  ariaLabel,
  content,
  triggerClassName = "",
  panelClassName = "",
  align = "left",
  resetKey = null,
}: InlinePopoverProps) {
  const [openKey, setOpenKey] = useState<string | number | null | undefined>(undefined)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const tooltipId = useId()

  const isOpen = openKey !== undefined && openKey === resetKey

  useEffect(() => {
    if (!isOpen) return

    function handlePointerDown(event: PointerEvent) {
      if (!containerRef.current) return
      if (containerRef.current.contains(event.target as Node)) return
      setOpenKey(undefined)
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpenKey(undefined)
      }
    }

    document.addEventListener("pointerdown", handlePointerDown)
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [isOpen])

  const panelPosition = align === "right" ? "right-0" : "left-0"

  return (
    <div
      ref={containerRef}
      className="relative inline-flex items-center"
      onMouseEnter={() => setOpenKey(resetKey)}
      onMouseLeave={() => setOpenKey(undefined)}
    >
      <button
        type="button"
        className={triggerClassName}
        aria-label={ariaLabel}
        aria-describedby={isOpen ? tooltipId : undefined}
        aria-expanded={isOpen}
        onClick={(event) => {
          event.stopPropagation()
          setOpenKey(isOpen ? undefined : resetKey)
        }}
        onFocus={() => setOpenKey(resetKey)}
        onBlur={() => setOpenKey(undefined)}
      >
        {label}
      </button>
      {isOpen ? (
        <div
          id={tooltipId}
          role="tooltip"
          className={`absolute z-20 mt-2 w-64 rounded-md border border-black/10 bg-white p-3 text-xs text-slate-700 shadow-lg ${panelPosition} ${panelClassName}`}
        >
          {content}
        </div>
      ) : null}
    </div>
  )
}
