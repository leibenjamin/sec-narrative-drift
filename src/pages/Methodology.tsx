import { Link } from "react-router-dom"
import { withBase } from "../lib/paths"

const DETECTORS = [
  {
    id: "det_logodds_terms_v1",
    label: "Log-odds terms",
    summary: "Ranks distinctive term shifts while downweighting common boilerplate.",
  },
  {
    id: "det_jsd_ngrams_v1",
    label: "JSD n-grams",
    summary: "Measures distribution drift in n-gram usage between adjacent years.",
  },
  {
    id: "det_minhash_boilerplate_v1",
    label: "Minhash boilerplate",
    summary: "Estimates near-duplicate reuse across years.",
  },
  {
    id: "det_winnowing_fingerprint_v1",
    label: "Winnowing fingerprints",
    summary: "Tracks exact overlapping fingerprint spans.",
  },
  {
    id: "det_structure_artifacts_v1",
    label: "Structure artifacts",
    summary: "Highlights heading and section-shape changes not obvious in term stats.",
  },
  {
    id: "det_rbo_agreement_v1",
    label: "RBO agreement",
    summary: "Checks rank-list agreement across deterministic detectors.",
  },
  {
    id: "det_llm_delta_brief_v1 + det_llm_excerpt_picker_v1",
    label: "LLM sidecars (precomputed)",
    summary: "Offline-only overlays for transparent model comparison; never runtime model calls.",
  },
]

export default function Methodology() {
  return (
    <main className="min-h-screen page-fade">
      <div className="mx-auto max-w-5xl space-y-10 px-6 py-12">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-widest text-slate-300">Methodology</p>
          <h1 className="text-3xl font-semibold">How to read SEC Narrative Drift Lab</h1>
          <p className="max-w-4xl text-sm text-slate-300">
            The product is deterministic-first and evidence-first. LLM outputs are optional
            precomputed artifacts with reproducibility tooling, not runtime inference.
          </p>
        </header>

        <section className="grid gap-4 rounded-xl border border-white/10 bg-slate-900/45 p-5 md:grid-cols-3">
          <article className="rounded-md border border-sky-300/25 bg-sky-400/10 p-3">
            <h2 className="text-sm font-semibold text-sky-100">Manager / Executive</h2>
            <p className="mt-2 text-xs text-slate-100">
              Ask: What changed, how strong is the shift, and which evidence lines support it?
            </p>
          </article>
          <article className="rounded-md border border-white/10 bg-slate-950/35 p-3">
            <h2 className="text-sm font-semibold text-slate-100">Analyst</h2>
            <p className="mt-2 text-xs text-slate-200">
              Cross-check top terms, distribution changes, and reuse/structure signals before
              drawing interpretation.
            </p>
          </article>
          <article className="rounded-md border border-white/10 bg-slate-950/35 p-3">
            <h2 className="text-sm font-semibold text-slate-100">Engineer / Data Scientist</h2>
            <p className="mt-2 text-xs text-slate-200">
              Validate output envelopes, provenance fields, and snippet-to-paragraph mapping with
              strict validators.
            </p>
          </article>
        </section>

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
              <article key={detector.id} className="rounded-lg border border-white/10 bg-slate-900/35 p-4">
                <h3 className="text-sm font-semibold text-slate-100">{detector.label}</h3>
                <p className="mt-1 text-xs text-slate-400">{detector.id}</p>
                <p className="mt-2 text-sm text-slate-200">{detector.summary}</p>
              </article>
            ))}
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
            Runtime instructions asset:{" "}
            <a
              className="text-sky-300 underline decoration-sky-300/60 underline-offset-2"
              href={withBase("data/sec_narrative_drift_lab/llm_project_instructions_v1.txt")}
              target="_blank"
              rel="noopener noreferrer"
            >
              llm_project_instructions_v1.txt
            </a>
          </p>
          <p className="text-xs text-slate-400">
            Source docs: <code>docs/SEC_TEXT_SAFETY.md</code> and{" "}
            <code>docs/lab/05_llm_reproducibility_contract.md</code>.
          </p>
        </section>

        <section className="space-y-3 rounded-xl border border-white/10 bg-slate-900/45 p-5">
          <h2 className="text-xl font-semibold">Security model</h2>
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-200">
            <li>SEC filing text is treated as untrusted input.</li>
            <li>No <code>dangerouslySetInnerHTML</code>, no <code>innerHTML</code> APIs, no raw HTML injection.</li>
            <li>Highlights are rendered with safe React text nodes and <code>&lt;mark&gt;</code> spans.</li>
            <li>External links open in a new tab with <code>rel="noopener noreferrer"</code>.</li>
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
