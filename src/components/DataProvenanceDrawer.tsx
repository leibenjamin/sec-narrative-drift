import { copy } from "../lib/copy"

export default function DataProvenanceDrawer() {
  return (
    <details className="rounded-md border border-black/20 text-sm">
      <summary className="cursor-pointer list-none px-3 py-2 font-medium">
        {copy.dataQuality.title}
      </summary>
      <div className="space-y-3 px-3 pb-3 text-sm">
        <p className="text-slate-200">{copy.global.sourceLine}</p>
        <p className="text-slate-200">{copy.methodology.paragraphs.secAccess}</p>
        <p className="text-slate-200">{copy.dataQuality.helper}</p>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full border border-black/10 px-2 py-1">
            {copy.dataQuality.badges.high}
          </span>
          <span className="rounded-full border border-black/10 px-2 py-1">
            {copy.dataQuality.badges.medium}
          </span>
          <span className="rounded-full border border-black/10 px-2 py-1">
            {copy.dataQuality.badges.low}
          </span>
          <span className="rounded-full border border-black/10 px-2 py-1">
            {copy.dataQuality.badges.skipped}
          </span>
        </div>
        <p className="text-slate-200">{copy.dataQuality.guidance}</p>
      </div>
    </details>
  )
}
