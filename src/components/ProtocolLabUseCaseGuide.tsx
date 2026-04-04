import FixtureRoleCard from "./FixtureRoleCard"
import { compactText } from "../lib/compactText"
import {
  buildProtocolLabCaseHref,
  type ProtocolLabVisiblePilotEntry,
} from "../lib/protocolLabProductPositioning"
import {
  VISIBLE_FAMILY_TICKERS,
  getRouteFamilyConfig,
  type VisibleFamilyTicker,
} from "../lib/routeFamilyUi"

type ProtocolLabUseCaseGuideProps = {
  visiblePilots: ProtocolLabVisiblePilotEntry[]
  title?: string
  description?: string
  className?: string
  showIntro?: boolean
}

function resolvePilot(
  visiblePilots: ProtocolLabVisiblePilotEntry[],
  ticker: VisibleFamilyTicker
): ProtocolLabVisiblePilotEntry | null {
  for (const pilot of visiblePilots) {
    if (pilot.ticker === ticker) return pilot
  }
  return null
}

function resolveHref(
  visiblePilots: ProtocolLabVisiblePilotEntry[],
  ticker: VisibleFamilyTicker
): string {
  const pilot = resolvePilot(visiblePilots, ticker)
  if (pilot) return pilot.href
  return buildProtocolLabCaseHref(ticker, 2024, 2025)
}

export default function ProtocolLabUseCaseGuide({
  visiblePilots,
  title = "Choose by goal",
  description = "Each option below is a fixed visible pilot fixture.",
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
        {VISIBLE_FAMILY_TICKERS.map((ticker) => {
          const pilot = resolvePilot(visiblePilots, ticker)
          const familyConfig = getRouteFamilyConfig(ticker)
          const primaryLine = compactText(
            familyConfig?.chooserCardDescription ??
              pilot?.guidance.what_you_learn ??
              "Open the current fixture for this pilot role.",
            74
          )
          const supportLine = compactText(
            familyConfig?.chooserBestFor ?? pilot?.best_for ?? pilot?.guidance.why_pick ?? "Open this fixture.",
            32
          )
          const isRecommended = Boolean(pilot?.is_recommended_first_case)
          return (
            <FixtureRoleCard
              key={ticker}
              ticker={ticker}
              companyName={pilot?.company_name ?? familyConfig?.companyName ?? ticker}
              roleLabel={familyConfig?.chooserObjectiveLabel ?? ticker}
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
