import type { SyntheticEvent } from "react"
import { copy } from "../lib/copy"

type DataProvenanceDrawerProps = {
  isOpen?: boolean
  onOpenChange?: (isOpen: boolean) => void
}

export default function DataProvenanceDrawer({
  isOpen,
  onOpenChange,
}: DataProvenanceDrawerProps) {
  const handleToggle = (event: SyntheticEvent<HTMLDetailsElement>) => {
    onOpenChange?.(event.currentTarget.open)
  }

  return (
    <details className="rounded-md border border-white/15 bg-slate-900/60 text-sm" open={isOpen} onToggle={handleToggle}>
      <summary className="cursor-pointer list-none px-3 py-2 font-medium text-slate-100">
        {copy.dataQuality.title}
      </summary>
      <div className="space-y-3 px-3 pb-3 text-sm">
        <p className="text-slate-200">{copy.global.sourceLine}</p>
        <p className="text-slate-200">{copy.methodology.paragraphs.secAccess}</p>
        <p className="text-slate-200">{copy.dataQuality.helper}</p>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full border border-white/15 bg-white/5 px-2 py-1 text-slate-300">
            {copy.dataQuality.badges.high}
          </span>
          <span className="rounded-full border border-white/15 bg-white/5 px-2 py-1 text-slate-300">
            {copy.dataQuality.badges.medium}
          </span>
          <span className="rounded-full border border-white/15 bg-white/5 px-2 py-1 text-slate-300">
            {copy.dataQuality.badges.low}
          </span>
          <span className="rounded-full border border-white/15 bg-white/5 px-2 py-1 text-slate-300">
            {copy.dataQuality.badges.skipped}
          </span>
        </div>
        <p className="text-slate-200">{copy.dataQuality.guidance}</p>
      </div>
    </details>
  )
}
