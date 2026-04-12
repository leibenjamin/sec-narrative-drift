import { Link } from "react-router-dom"
import FixtureRoleStrip, { type FixtureRoleStripItem } from "../components/FixtureRoleStrip"
import MethodFamilySummary, { type MethodFamily } from "../components/MethodFamilySummary"
import PageMetadata from "../components/PageMetadata"
import TrustModelRow, { type TrustModelItem } from "../components/TrustModelRow"
import WorkflowAnatomyDiagram, {
  type WorkflowAnatomyStage,
} from "../components/WorkflowAnatomyDiagram"
import {
  PEDAGOGIC_COMPARE_EXAMPLES,
  PUBLIC_CASEBOOK_TICKERS,
  casebookFraming,
  getPublicCasebookEntry,
} from "../lib/casebookContent"
import { withBase } from "../lib/paths"
import { getRouteFamilyConfig } from "../lib/routeFamilyUi"

const METHODOLOGY_TITLE = casebookFraming.methodology.title
const METHODOLOGY_DESCRIPTION = casebookFraming.methodology.metaDescription

const DETECTORS = [
  {
    id: "det_logodds_terms_v1",
    family: "Lexical drift",
    label: "Log-odds terms",
    question: "What language moved most?",
    summary: "Ranks distinctive term shifts while downweighting common boilerplate.",
    whyUsed: "Fast lexical signal with transparent ranked evidence for first-pass interpretation.",
    knownLimitation: "Can over-weight one-off terms or style noise if cleaning quality drops.",
    deviation:
      "Scoped to adjacent Item 1A comparisons with lens-constrained preprocessing and evidence cards.",
  },
  {
    id: "det_jsd_ngrams_v1",
    family: "Lexical drift",
    label: "JSD n-grams",
    question: "How much did the language distribution shift?",
    summary: "Measures distribution drift in n-gram usage between adjacent years.",
    whyUsed: "Adds distribution-level drift signal to complement term-level rankings.",
    knownLimitation: "Can elevate format or template churn even when substantive risk meaning is stable.",
    deviation:
      "Applied to filing-section n-grams and paired with evidence snippets instead of corpus-only diagnostics.",
  },
  {
    id: "det_minhash_boilerplate_v1",
    family: "Reuse / continuity",
    label: "Minhash boilerplate",
    question: "How much was recycled?",
    summary: "Estimates near-duplicate reuse across years.",
    whyUsed: "Separates persistent boilerplate from true narrative novelty.",
    knownLimitation: "Misses paraphrase-level similarity when exact shingle overlap is limited.",
    deviation:
      "Paragraph-level reuse diagnostics tuned for Item 1A, surfaced as interpretable card outputs.",
  },
  {
    id: "det_winnowing_fingerprint_v1",
    family: "Reuse / continuity",
    label: "Winnowing fingerprints",
    question: "Which exact spans carried over?",
    summary: "Tracks exact overlapping fingerprint spans.",
    whyUsed: "Provides exact-span overlap evidence that is easy to audit quickly.",
    knownLimitation: "Insensitive to semantic drift that preserves little exact wording.",
    deviation:
      "Used as a reuse and continuity lens in a drift lab, not as a standalone plagiarism detector.",
  },
  {
    id: "det_structure_artifacts_v1",
    family: "Structure / agreement",
    label: "Structure artifacts",
    question: "Where did the structure change?",
    summary: "Highlights heading and section-shape changes not obvious in term stats.",
    whyUsed: "Exposes template and structure shifts that can distort lexical-only interpretation.",
    knownLimitation: "Can look strong when format changes but content meaning does not.",
    deviation:
      "Focused on Item 1A heading and structural diagnostics with evidence-level traceability.",
  },
  {
    id: "det_rbo_agreement_v1",
    family: "Structure / agreement",
    label: "RBO agreement",
    question: "Where do methods agree?",
    summary: "Checks rank-list agreement across deterministic detectors.",
    whyUsed: "Adds a compact concordance check before deeper per-method investigation.",
    knownLimitation: "Can hide disagreements below top-weighted rank depth.",
    deviation:
      "Used as cross-detector quality framing for one case and lens, not broad benchmark scoring.",
  },
]

const WORKFLOW_STAGES: WorkflowAnatomyStage[] = [
  {
    title: "Source prep",
    detail: "Clean filings and precompute runtime artifacts before anything ships.",
    chip: "Offline",
    discipline: "Static runtime only",
    tone: "source",
  },
  {
    title: "Filing answer / claim",
    detail: "Lead with the filing answer before protocol explanation takes over.",
    chip: "Claim",
    discipline: "Answer first",
    tone: "claim",
  },
  {
    title: "Proof / evidence",
    detail: "Keep excerpts and method evidence adjacent to the claim.",
    chip: "Proof",
    discipline: "Evidence adjacent",
    tone: "proof",
  },
  {
    title: "Stop / limits",
    detail: "Make scope boundaries and honest stopping points visible.",
    chip: "Stop",
    discipline: "Scope stays visible",
    tone: "stop",
  },
  {
    title: "Audit if needed",
    detail: "Leave detector families and provenance lower and optional.",
    chip: "Appendix",
    discipline: "Audit on demand",
    tone: "audit",
  },
]

const TRUST_MODEL_ITEMS: TrustModelItem[] = [
  { label: "Static JSON only" },
  { label: "No runtime LLM" },
  { label: "Evidence-based" },
  { label: "Bounded scope" },
]

const FIXTURE_ROLE_ITEMS: FixtureRoleStripItem[] = PUBLIC_CASEBOOK_TICKERS.map((ticker) => {
  const familyConfig = getRouteFamilyConfig(ticker)
  if (!familyConfig) {
    throw new Error(`Missing route-family config for ${ticker}.`)
  }

  return {
    ticker,
    role: familyConfig.publicRoleLabel,
    detail: familyConfig.methodologyDetail,
  }
})

const PEDAGOGIC_COMPARE_ITEMS = PEDAGOGIC_COMPARE_EXAMPLES.map((example) => {
  const entry = getPublicCasebookEntry(example.ticker)
  if (!entry) {
    throw new Error(`Missing pedagogic compare case for ${example.ticker}.`)
  }

  return {
    ...example,
    companyName: entry.companyName,
    roleLabel: entry.publicRoleLabel,
  }
})

const METHOD_FAMILIES: MethodFamily[] = [
  {
    title: "Lexical drift",
    summary:
      "Pressure-test the filing answer with ranked term movement and distribution drift when the wording itself feels meaningfully different.",
    detectors: DETECTORS.filter((detector) => detector.family === "Lexical drift"),
  },
  {
    title: "Reuse / continuity",
    summary:
      "Check whether novelty is real or mostly recycled by separating near-duplicate reuse from exact carryover spans.",
    detectors: DETECTORS.filter((detector) => detector.family === "Reuse / continuity"),
  },
  {
    title: "Structure / agreement",
    summary:
      "Use heading shifts and cross-method agreement to see whether the answer survives a stronger audit pass.",
    detectors: DETECTORS.filter((detector) => detector.family === "Structure / agreement"),
  },
]

export default function Methodology() {
  return (
    <main className="min-h-screen page-fade">
      <PageMetadata title={METHODOLOGY_TITLE} description={METHODOLOGY_DESCRIPTION} />
      <div className="mx-auto max-w-6xl space-y-5 px-5 py-5 sm:space-y-7 sm:px-6 sm:py-8">
        <section
          id="methodology-top-fold"
          className="relative overflow-hidden rounded-4xl border border-white/10 bg-linear-to-br from-slate-950/92 via-slate-950/84 to-slate-900/72 p-4 shadow-[0_30px_80px_rgba(2,6,23,0.38)] sm:p-6"
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.16),transparent_36%),radial-gradient(circle_at_bottom_right,rgba(16,185,129,0.11),transparent_30%)]" />
          <div className="relative space-y-3 sm:space-y-4">
            <div className="flex flex-wrap items-center gap-1.5 text-[11px] uppercase tracking-[0.24em] text-slate-300">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                Methodology
              </span>
              <span className="rounded-full border border-sky-300/25 bg-sky-400/10 px-3 py-1 text-sky-100">
                Field guide
              </span>
            </div>

            <header className="space-y-1.5">
              <h1 className="max-w-3xl text-[clamp(2rem,3.4vw,3.15rem)] font-semibold leading-[0.95] tracking-[-0.04em] text-slate-50">
                {casebookFraming.methodology.heading}
              </h1>
              <p className="max-w-3xl text-sm leading-6 text-slate-300">
                {casebookFraming.methodology.intro}
              </p>
            </header>

            <div className="grid gap-3.5 sm:gap-4">
              <div className="lg:order-2">
                <TrustModelRow items={TRUST_MODEL_ITEMS} />
              </div>
              <div className="lg:order-3">
                <FixtureRoleStrip items={FIXTURE_ROLE_ITEMS} />
              </div>
              <div className="lg:order-1">
                <WorkflowAnatomyDiagram stages={WORKFLOW_STAGES} />
              </div>
            </div>

            <section className="grid gap-3 md:grid-cols-2">
              <article
                id="methodology-frontier-models"
                className="rounded-[1.2rem] border border-sky-300/18 bg-sky-400/8 p-4"
              >
                <div className="text-[11px] uppercase tracking-[0.24em] text-sky-100">
                  {casebookFraming.methodology.whyFrontierTitle}
                </div>
                <div className="mt-2 space-y-2 text-sm leading-6 text-slate-100">
                  {casebookFraming.methodology.whyFrontierBody.map((item) => (
                    <p key={item}>{item}</p>
                  ))}
                </div>
              </article>

              <article className="rounded-[1.2rem] border border-white/10 bg-slate-950/30 p-4">
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  {casebookFraming.methodology.nonClaimsTitle}
                </div>
                <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-slate-200">
                  {casebookFraming.methodology.nonClaims.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            </section>

            <section
              id="methodology-compare"
              className="space-y-3 rounded-[1.2rem] border border-white/10 bg-slate-950/30 p-4"
            >
              <div className="space-y-2">
                <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                  Simple read vs structured read
                </div>
                <h2 className="text-xl font-semibold text-slate-50 sm:text-2xl">
                  {casebookFraming.methodology.compareTitle}
                </h2>
                <p className="max-w-3xl text-sm leading-6 text-slate-300">
                  {casebookFraming.methodology.compareIntro}
                </p>
              </div>

              <div className="grid gap-3 lg:grid-cols-2">
                {PEDAGOGIC_COMPARE_ITEMS.map((item) => (
                  <article
                    key={item.ticker}
                    id={`methodology-compare-${item.ticker.toLowerCase()}`}
                    className="rounded-[1.15rem] border border-white/10 bg-slate-950/62 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                          {item.ticker}
                        </div>
                        <h3 className="mt-1 text-lg font-semibold text-slate-50">
                          {item.companyName}
                        </h3>
                      </div>
                      <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] tracking-[0.06em] text-slate-200">
                        {item.roleLabel}
                      </div>
                    </div>

                    <div className="mt-3 grid gap-2.5">
                      <article className="rounded-2xl border border-white/10 bg-slate-950/58 p-3">
                        <div className="text-[10px] uppercase tracking-[0.24em] text-slate-400">
                          What a simpler read gets you
                        </div>
                        <p className="mt-1.5 text-sm leading-6 text-slate-100">
                          {item.simpleRead}
                        </p>
                      </article>

                      <article className="rounded-2xl border border-sky-300/18 bg-sky-400/8 p-3">
                        <div className="text-[10px] uppercase tracking-[0.24em] text-sky-100">
                          What the structured read adds
                        </div>
                        <p className="mt-1.5 text-sm leading-6 text-slate-100">
                          {item.structuredRead}
                        </p>
                      </article>

                      <article className="rounded-2xl border border-white/10 bg-slate-950/58 p-3">
                        <div className="text-[10px] uppercase tracking-[0.24em] text-slate-400">
                          Why this matters
                        </div>
                        <p className="mt-1.5 text-sm leading-6 text-slate-100">
                          {item.whyItMatters}
                        </p>
                      </article>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <article className="rounded-[1.2rem] border border-white/10 bg-slate-950/30 p-4">
              <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                Matrix-first public cases
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-200">
                {casebookFraming.methodology.matrixOnlyNote}
              </p>
            </article>
          </div>
        </section>

        <MethodFamilySummary families={METHOD_FAMILIES} />

        <details className="rounded-[1.45rem] border border-white/10 bg-slate-900/45 p-4 sm:p-5">
          <summary className="cursor-pointer list-none">
            <div className="flex flex-wrap items-start justify-between gap-3 rounded-[1.1rem] border border-white/10 bg-slate-950/34 px-4 py-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
                  Deeper method appendix
                </div>
                <h2 className="mt-2 text-xl font-semibold text-slate-100 sm:text-2xl">
                  Full method rationale stays below the first read
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                  Open the full table only when you need method-by-method limitations and deviations.
                </p>
              </div>
              <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-300">
                Detailed audit only
              </div>
            </div>
          </summary>

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-xs text-slate-100">
              <thead className="text-slate-300">
                <tr>
                  <th className="px-2 py-2">Question answered</th>
                  <th className="px-2 py-2">Method</th>
                  <th className="px-2 py-2">Why used here</th>
                  <th className="px-2 py-2">Known limitation</th>
                  <th className="px-2 py-2">App-specific deviation</th>
                </tr>
              </thead>
              <tbody>
                {DETECTORS.map((detector) => (
                  <tr key={`${detector.id}-row`} className="border-t border-white/10 align-top">
                    <td className="px-2 py-2 text-slate-200">{detector.question}</td>
                    <td className="px-2 py-2">
                      <a
                        href={`#detector-${detector.id}`}
                        className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                      >
                        {detector.label}
                      </a>
                    </td>
                    <td className="px-2 py-2 text-slate-200">{detector.whyUsed}</td>
                    <td className="px-2 py-2 text-slate-200">{detector.knownLimitation}</td>
                    <td className="px-2 py-2 text-slate-200">{detector.deviation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>

        <details className="rounded-[1.45rem] border border-white/10 bg-slate-900/45 p-4 sm:p-5">
          <summary className="cursor-pointer list-none">
            <div className="flex flex-wrap items-start justify-between gap-3 rounded-[1.1rem] border border-white/10 bg-slate-950/34 px-4 py-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
                  Operational appendix
                </div>
                <h2 className="mt-2 text-xl font-semibold text-slate-100 sm:text-2xl">
                  Sidecars, audit boundary, and source references
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                  Keep the workflow above primary. Open this appendix for offline sidecars, explicit limits, and source indexes.
                </p>
              </div>
              <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-300">
                Appendix
              </div>
            </div>
          </summary>

          <div className="mt-4 space-y-4">
            <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
              <article className="space-y-3 rounded-[1.2rem] border border-white/10 bg-slate-950/30 p-4">
                <div className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
                  Offline model sidecars
                </div>
                <h3 className="text-xl font-semibold text-slate-100">
                  Structured compare artifacts are produced before runtime
                </h3>
                <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-200">
                  <li>Generate case and year inputs from deterministic scripts.</li>
                  <li>Run one manual thread per case, lens, and campaign under the strict JSON-only outline-compare contract.</li>
                  <li>Write the structured artifact to its canonical output path.</li>
                  <li>Project it deterministically into runtime outputs and validate before deployment.</li>
                </ol>
                <p className="text-xs text-slate-400">
                  The shipped app never invokes a model at runtime. Users only see projected runtime
                  artifacts and the structured evidence they were derived from.
                </p>
              </article>

              <article className="space-y-3 rounded-[1.2rem] border border-white/10 bg-slate-950/30 p-4">
                <div className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
                  Audit boundary
                </div>
                <h3 className="text-xl font-semibold text-slate-100">Confidence and limits stay explicit</h3>
                <ul className="list-disc space-y-2 pl-5 text-sm text-slate-200">
                  <li>Extraction confidence is a heuristic quality signal, not a calibrated probability.</li>
                  <li>Per-method confidence bands are ordinal triage aids, not statistical confidence intervals.</li>
                  <li>High agreement is useful, but it does not remove the need to inspect the filing evidence.</li>
                  <li>Treat model rows as structured interpretations anchored to evidence, not ground truth by themselves.</li>
                  <li>Bounded visible cases can stop earlier than full-runtime cases; that stopping point is an explicit product decision, not a hidden fallback.</li>
                </ul>
              </article>
            </section>

            <section className="space-y-3 rounded-[1.2rem] border border-white/10 bg-slate-950/30 p-4">
              <div className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
                Appendix links
              </div>
              <h3 className="text-xl font-semibold text-slate-100">Source indexes and route truth references</h3>
              <div className="space-y-2 text-sm text-slate-200">
                <p>
                  Full-section input indexes:
                  <a
                    className="ml-1 text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                    href={withBase("data/sec_narrative_drift_lab/llm_inputs_v2/inputs_index_pair_v2.json")}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    inputs_index_pair_v2.json
                  </a>
                  {" | "}
                  <a
                    className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                    href={withBase("data/sec_narrative_drift_lab/llm_inputs_v2/inputs_index_year_v2.json")}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    inputs_index_year_v2.json
                  </a>
                </p>
                <p>
                  Method profile metadata:
                  <a
                    className="ml-1 text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                    href={withBase("data/sec_narrative_drift_lab/lab_method_profiles_v1.json")}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    lab_method_profiles_v1.json
                  </a>
                </p>
                <p>
                  Source docs: <code>docs/SEC_TEXT_SAFETY.md</code> and <code>docs/lab/05_llm_reproducibility_contract.md</code>
                </p>
              </div>
            </section>
          </div>
        </details>

        <footer className="flex flex-wrap items-center gap-2 text-sm">
          <Link
            to="/"
            className="inline-flex items-center rounded-full border border-white/20 px-4 py-2 text-slate-200 hover:border-white/40 hover:bg-white/5"
          >
            Back to home
          </Link>
          <Link
            to="/companies"
            className="inline-flex items-center rounded-full border border-white/20 px-4 py-2 text-slate-200 hover:border-white/40 hover:bg-white/5"
          >
            Open Casebook
          </Link>
        </footer>
      </div>
    </main>
  )
}
