import FixtureRoleCard from "./FixtureRoleCard"
import { compactText } from "../lib/compactText"
import {
  PUBLIC_CASEBOOK_TICKERS,
  getPublicCasebookEntry,
  type PublicCasebookTicker,
} from "../lib/casebookContent"
import {
  buildProtocolLabCaseHref,
  type ProtocolLabVisiblePilotEntry,
} from "../lib/protocolLabProductPositioning"
import { getRouteFamilyConfig } from "../lib/routeFamilyUi"

type ProtocolLabUseCaseGuideProps = {
  visiblePilots: ProtocolLabVisiblePilotEntry[]
  title?: string
  description?: string
  className?: string
  showIntro?: boolean
}

function resolvePilot(
  visiblePilots: ProtocolLabVisiblePilotEntry[],
  ticker: PublicCasebookTicker
): ProtocolLabVisiblePilotEntry | null {
  for (const pilot of visiblePilots) {
    if (pilot.ticker === ticker) return pilot
  }
  return null
}

function resolveHref(
  visiblePilots: ProtocolLabVisiblePilotEntry[],
  ticker: PublicCasebookTicker
): string {
  const pilot = resolvePilot(visiblePilots, ticker)
  if (pilot) return pilot.href
  const entry = getPublicCasebookEntry(ticker)
  if (!entry) {
    throw new Error(`Missing casebook entry for ${ticker}.`)
  }
  return buildProtocolLabCaseHref(ticker, entry.yearFrom, entry.yearTo)
}

export default function ProtocolLabUseCaseGuide({
  visiblePilots,
  title = "Choose by goal",
  description = "Each option below is a current public case.",
  className = "",
  showIntro = true,
}: ProtocolLabUseCaseGuideProps) {
  return (
    <section className={`space-y-4 ${className}`.trim()}>
      {showIntro ? (
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-slate-400">{title}</div>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">{description}</p>
        </div>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-3">
        {PUBLIC_CASEBOOK_TICKERS.map((ticker) => {
          const pilot = resolvePilot(visiblePilots, ticker)
          const familyConfig = getRouteFamilyConfig(ticker)
          const casebookEntry = getPublicCasebookEntry(ticker)
          const primaryLine = compactText(
            familyConfig?.chooserCardDescription ??
              casebookEntry?.chooserCardDescription ??
              pilot?.guidance.what_you_learn ??
              "Open the current case for this route.",
            74
          )
          const supportLine = compactText(
            familyConfig?.chooserBestFor ??
              casebookEntry?.bestUsedWhen ??
              pilot?.best_for ??
              pilot?.guidance.why_pick ??
              "Open this case.",
            32
          )
          const isRecommended = Boolean(pilot?.is_recommended_first_case)
          return (
            <FixtureRoleCard
              key={ticker}
              ticker={ticker}
              companyName={familyConfig?.companyName ?? casebookEntry?.companyName ?? pilot?.company_name ?? ticker}
              roleLabel={familyConfig?.chooserObjectiveLabel ?? casebookEntry?.publicRoleLabel ?? ticker}
              description={primaryLine}
              bestFor={supportLine}
              href={resolveHref(visiblePilots, ticker)}
              ctaLabel={`Open ${ticker}`}
              emphasis={isRecommended ? "primary" : "default"}
              variant="cases"
            />
          )
        })}
      </div>
    </section>
  )
}
