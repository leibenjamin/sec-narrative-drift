import { useEffect, useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { loadLabLlmCampaignsIndex } from "../lib/labData"
import { withBase } from "../lib/paths"

const DEFAULT_RUNTIME_INSTRUCTIONS_ASSET =
  "llm_project_instructions_openai_gpt53codex_xhigh_agent_fullsec_real_2026-02-27.txt"

const DETECTORS = [
  {
    id: "det_logodds_terms_v1",
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
    label: "RBO agreement",
    question: "Where do methods agree?",
    summary: "Checks rank-list agreement across deterministic detectors.",
    whyUsed: "Adds a compact concordance check before deeper per-method investigation.",
    knownLimitation: "Can hide disagreements below top-weighted rank depth.",
    deviation:
      "Used as cross-detector quality framing for one case and lens, not broad benchmark scoring.",
  },
]

export default function Methodology() {
  const [searchParams] = useSearchParams()
  const requestedCampaignId = searchParams.get("llmA")
  const [instructionsAsset, setInstructionsAsset] = useState(DEFAULT_RUNTIME_INSTRUCTIONS_ASSET)
  const [instructionsCampaignLabel, setInstructionsCampaignLabel] = useState(
    "primary runtime campaign"
  )

  useEffect(() => {
    let cancelled = false
    loadLabLlmCampaignsIndex()
      .then((index) => {
        if (cancelled) return
        const runtimeCampaigns = index.campaigns.filter(
          (campaign) =>
            campaign.runtime_visible !== false && campaign.input_mode !== "focuspack_v1"
        )
        const available = runtimeCampaigns.length > 0 ? runtimeCampaigns : index.campaigns
        const selectedCampaign =
          available.find((campaign) => campaign.campaign_id === requestedCampaignId) ??
          available.find((campaign) => campaign.campaign_id === index.primary_campaign_id) ??
          available[0] ??
          null
        if (!selectedCampaign) return
        setInstructionsAsset(
          selectedCampaign.instructions_asset?.trim() || DEFAULT_RUNTIME_INSTRUCTIONS_ASSET
        )
        setInstructionsCampaignLabel(selectedCampaign.display_name)
      })
      .catch(() => {
        if (cancelled) return
        setInstructionsCampaignLabel("primary runtime campaign")
      })
    return () => {
      cancelled = true
    }
  }, [requestedCampaignId])

  const instructionsPath = useMemo(
    () => withBase(`data/sec_narrative_drift_lab/${instructionsAsset}`),
    [instructionsAsset]
  )

  return (
    <main className="min-h-screen page-fade">
      <div className="mx-auto max-w-6xl space-y-10 px-6 py-12">
        <header className="space-y-4">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-300">Methodology</p>
          <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">How to evaluate one case quickly, then audit it deeply</h1>
          <p className="max-w-4xl text-sm text-slate-300">
            Every result starts from deterministic methods applied directly to SEC filing text. Model-produced compare artifacts are
            offline sidecars with explicit provenance, never runtime inference. The product is built to move from fast investor read
            to audit trail without changing tools.
          </p>
        </header>

        <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <article className="rounded-[1.5rem] border border-sky-300/25 bg-sky-400/10 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-sky-100">Fast path</div>
            <h2 className="mt-2 text-xl font-semibold text-slate-100">How to read a case in 60 seconds</h2>
            <ol className="mt-4 space-y-2 text-sm text-slate-200">
              <li>1. Read the lead material change and the paired prior-year versus current-year evidence.</li>
              <li>2. Check the two core deterministic methods to see whether the language shift looks real.</li>
              <li>3. Use the agreement panel to decide whether the filing needs a deeper method-by-method read.</li>
              <li>4. Only then compare Codex and ChatGPT framing in the outline view.</li>
            </ol>
          </article>

          <article className="rounded-[1.5rem] border border-white/10 bg-slate-900/45 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-slate-300">Core trust model</div>
            <ul className="mt-4 space-y-2 text-sm text-slate-200">
              <li>No runtime LLM or ML calls in the shipped app.</li>
              <li>Frontend reads static Lab JSON only from <code>data/sec_narrative_drift_lab/</code>.</li>
              <li>SEC text is treated as untrusted input and rendered as plain text only.</li>
              <li>Missing artifacts stay visible with expected paths instead of silently falling back.</li>
            </ul>
          </article>
        </section>

        <section className="space-y-4 rounded-[1.45rem] border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold text-slate-100">What each deterministic method answers</h2>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {DETECTORS.map((detector) => (
              <article key={detector.id} id={`detector-${detector.id}`} className="rounded-xl border border-white/10 bg-slate-950/35 p-4">
                <div className="text-xs uppercase tracking-[0.22em] text-slate-400">{detector.question}</div>
                <h3 className="mt-2 text-sm font-semibold text-slate-100">{detector.label}</h3>
                <p className="mt-1 text-xs text-slate-400">{detector.id}</p>
                <p className="mt-3 text-sm text-slate-200">{detector.summary}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="space-y-4 rounded-[1.45rem] border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold text-slate-100">Why these methods are here</h2>
          <div className="overflow-x-auto">
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
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <article className="space-y-3 rounded-[1.45rem] border border-white/10 bg-slate-900/45 p-5">
            <h2 className="text-xl font-semibold text-slate-100">How the model sidecars are produced</h2>
            <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-200">
              <li>Generate pair and year inputs from deterministic scripts.</li>
              <li>Run one manual thread per pair, lens, and campaign under the strict JSON-only outline-compare contract.</li>
              <li>Write the structured artifact to its canonical output path.</li>
              <li>Project it deterministically into runtime outputs and validate before deployment.</li>
            </ol>
            <p className="text-xs text-slate-400">
              Runtime instructions asset for the selected compare campaign:
              <a
                className="ml-1 text-sky-300 underline decoration-sky-300/60 underline-offset-2"
                href={instructionsPath}
                target="_blank"
                rel="noopener noreferrer"
              >
                {instructionsAsset}
              </a>
            </p>
            <p className="text-xs text-slate-400">
              Selected campaign context: <span className="text-slate-200">{instructionsCampaignLabel}</span>
            </p>
          </article>

          <article className="space-y-3 rounded-[1.45rem] border border-white/10 bg-slate-900/45 p-5">
            <h2 className="text-xl font-semibold text-slate-100">Confidence and limits</h2>
            <ul className="list-disc space-y-2 pl-5 text-sm text-slate-200">
              <li>Extraction confidence is a heuristic quality signal, not a calibrated probability.</li>
              <li>Per-method confidence bands are ordinal triage aids, not statistical confidence intervals.</li>
              <li>High agreement is useful, but it does not remove the need to inspect the filing evidence.</li>
              <li>Treat model rows as structured interpretations anchored to evidence, not ground truth by themselves.</li>
            </ul>
          </article>
        </section>

        <section className="space-y-3 rounded-[1.45rem] border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold text-slate-100">Technical appendix and source links</h2>
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
            Open showcase catalog
          </Link>
        </footer>
      </div>
    </main>
  )
}
