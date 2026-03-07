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
    summary: "Ranks distinctive term shifts while downweighting common boilerplate.",
    whyUsed: "Fast lexical signal with transparent ranked evidence for first-pass interpretation.",
    knownLimitation: "Can over-weight one-off terms or style noise if cleaning quality drops.",
    deviation:
      "Scoped to adjacent Item 1A comparisons with lens-constrained preprocessing and evidence cards.",
  },
  {
    id: "det_jsd_ngrams_v1",
    label: "JSD n-grams",
    summary: "Measures distribution drift in n-gram usage between adjacent years.",
    whyUsed: "Adds distribution-level drift signal to complement term-level rankings.",
    knownLimitation: "Can elevate format/template churn even when substantive risk meaning is stable.",
    deviation:
      "Applied to filing-section n-grams and paired with evidence snippets instead of corpus-only diagnostics.",
  },
  {
    id: "det_minhash_boilerplate_v1",
    label: "Minhash boilerplate",
    summary: "Estimates near-duplicate reuse across years.",
    whyUsed: "Separates persistent boilerplate from true narrative novelty.",
    knownLimitation: "Misses paraphrase-level similarity when exact shingle overlap is limited.",
    deviation:
      "Paragraph-level reuse diagnostics tuned for Item 1A, surfaced as interpretable card outputs.",
  },
  {
    id: "det_winnowing_fingerprint_v1",
    label: "Winnowing fingerprints",
    summary: "Tracks exact overlapping fingerprint spans.",
    whyUsed: "Provides exact-span overlap evidence that is easy to audit quickly.",
    knownLimitation: "Insensitive to semantic drift that preserves little exact wording.",
    deviation:
      "Used as a reuse/continuity lens in a drift lab, not as a standalone plagiarism detector.",
  },
  {
    id: "det_structure_artifacts_v1",
    label: "Structure artifacts",
    summary: "Highlights heading and section-shape changes not obvious in term stats.",
    whyUsed: "Exposes template and structure shifts that can distort lexical-only interpretation.",
    knownLimitation: "Can look strong when format changes but content meaning does not.",
    deviation:
      "Focused on Item 1A heading and structural diagnostics with evidence-level traceability.",
  },
  {
    id: "det_rbo_agreement_v1",
    label: "RBO agreement",
    summary: "Checks rank-list agreement across deterministic detectors.",
    whyUsed: "Adds a compact concordance check before deeper per-method investigation.",
    knownLimitation: "Can hide disagreements below top-weighted rank depth.",
    deviation:
      "Used as cross-detector quality framing for one case/lens, not broad IR benchmark scoring.",
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
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-widest text-slate-300">Methodology</p>
          <h1 className="text-3xl font-semibold">How to read SEC Narrative Drift Lab</h1>
          <p className="max-w-4xl text-sm text-slate-300">
            Every result here starts from deterministic, reproducible methods applied directly to SEC
            filing text. AI-generated analyses are precomputed sidecars with full provenance — never
            runtime inference.
          </p>
          <p className="max-w-4xl rounded-md border border-white/10 bg-slate-900/35 px-3 py-2 text-sm text-slate-200">
            Executive mode gives a rapid overview of what changed and how strong the signal is. Deep
            mode expands each method with caveats, sourced origins, and structural detail.
          </p>
        </header>

        <section className="space-y-3 rounded-xl border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold">Runtime contract</h2>
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-200">
            <li>No runtime LLM/ML calls in the shipped app.</li>
            <li>No POS tagging in detector logic.</li>
            <li>Frontend reads static Lab JSON only from <code>data/sec_narrative_drift_lab/</code>.</li>
            <li>Public detector envelopes and keys remain fixed across releases.</li>
          </ul>
        </section>

        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Detector roster</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {DETECTORS.map((detector) => (
              <article
                key={detector.id}
                id={`detector-${detector.id}`}
                className="rounded-lg border border-white/10 bg-slate-900/35 p-4"
              >
                <h3 className="text-sm font-semibold text-slate-100">{detector.label}</h3>
                <p className="mt-1 text-xs text-slate-400">{detector.id}</p>
                <p className="mt-2 text-sm text-slate-200">{detector.summary}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="space-y-4 rounded-xl border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold">Detector decision rationale</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-xs text-slate-100">
              <thead className="text-slate-300">
                <tr>
                  <th className="px-2 py-2">Method</th>
                  <th className="px-2 py-2">Why used here</th>
                  <th className="px-2 py-2">Known limitation</th>
                  <th className="px-2 py-2">Deviation from canonical usage</th>
                </tr>
              </thead>
              <tbody>
                {DETECTORS.map((detector) => (
                  <tr key={`${detector.id}-row`} className="border-t border-white/10 align-top">
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

        <section className="space-y-3 rounded-xl border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold">Reproducible LLM sidecar flow</h2>
          <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-200">
            <li>Generate run manifest and inputs from deterministic scripts.</li>
            <li>Run one manual thread per pair and detector with strict JSON-only rules.</li>
            <li>Save outputs directly to canonical <code>outputs/&lt;detector_id&gt;/...</code> paths.</li>
            <li>Run strict manifest validator before deployment.</li>
          </ol>
          <p className="text-xs text-slate-400">
            Runtime instructions asset (campaign-aware):{" "}
            <a
              className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
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
          <p className="text-xs text-slate-400">
            Full-section input indexes:{" "}
            <a
              className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
              href={withBase("data/sec_narrative_drift_lab/llm_inputs_v2/inputs_index_pair_v2.json")}
              target="_blank"
              rel="noopener noreferrer"
            >
              inputs_index_pair_v2.json
            </a>{" "}
            |{" "}
            <a
              className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
              href={withBase("data/sec_narrative_drift_lab/llm_inputs_v2/inputs_index_year_v2.json")}
              target="_blank"
              rel="noopener noreferrer"
            >
              inputs_index_year_v2.json
            </a>
          </p>
          <p className="text-xs text-slate-400">
            Method profile metadata:{" "}
            <a
              className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
              href={withBase("data/sec_narrative_drift_lab/lab_method_profiles_v1.json")}
              target="_blank"
              rel="noopener noreferrer"
            >
              lab_method_profiles_v1.json
            </a>
          </p>
          <p className="text-xs text-slate-400">
            Source docs: <code>docs/SEC_TEXT_SAFETY.md</code> and{" "}
            <code>docs/lab/05_llm_reproducibility_contract.md</code>.
          </p>
        </section>

        <section className="space-y-3 rounded-xl border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold">Confidence semantics</h2>
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-200">
            <li>
              Extraction confidence is a heuristic quality score for section-capture reliability, not
              a calibrated probability.
            </li>
            <li>
              Per-method <span className="font-semibold text-slate-100">confidence bands</span> are
              ordinal tiers (Low / Medium / High), useful for triage but not for statistical claims.
            </li>
            <li>
              Treat all confidence readouts as directional signals. Verify with evidence blocks,
              the agreement matrix, and cross-method consistency before drawing conclusions.
            </li>
          </ul>
        </section>

        <section className="space-y-3 rounded-xl border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold">Suggested reading order</h2>
          <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-200">
            <li>
              <span className="font-semibold text-slate-100">Risk narrative summary</span> — start
              here for the structural drift score, top material changes, and investor-relevant
              takeaways.
            </li>
            <li>
              <span className="font-semibold text-slate-100">Deterministic methods</span> — review
              per-method drift scores, evidence excerpts, and the agreement matrix to see where
              methods converge or disagree.
            </li>
            <li>
              <span className="font-semibold text-slate-100">Outline comparison</span> — drill into
              the AI-generated structural analysis for specific change mechanisms, evidence
              provenance, and analysis limitations.
            </li>
            <li>
              <span className="font-semibold text-slate-100">Method context</span> — expand any
              method card to see canonical usage, known failure modes, and sourced references.
            </li>
          </ol>
        </section>

        <section className="space-y-3 rounded-xl border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold">Security model</h2>
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-200">
            <li>SEC filing text is treated as untrusted input.</li>
            <li>No <code>dangerouslySetInnerHTML</code>, no <code>innerHTML</code> APIs, no raw HTML injection.</li>
            <li>Highlights are rendered with safe React text nodes and <code>&lt;mark&gt;</code> spans.</li>
            <li>External links open in a new tab with <code>rel=&quot;noopener noreferrer&quot;</code>.</li>
          </ul>
        </section>

        <footer className="flex flex-wrap items-center gap-2 text-sm">
          <Link
            to="/"
            className="inline-flex items-center rounded-md border border-white/20 px-3 py-2 text-slate-200 hover:border-white/40 hover:bg-white/5"
          >
            Back to home
          </Link>
          <Link
            to="/companies"
            className="inline-flex items-center rounded-md border border-white/20 px-3 py-2 text-slate-200 hover:border-white/40 hover:bg-white/5"
          >
            Open showcase catalog
          </Link>
        </footer>
      </div>
    </main>
  )
}
