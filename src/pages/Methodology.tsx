import { copy } from "../lib/copy"

export default function Methodology() {
  return (
    <main className="min-h-screen page-fade">
      <div className="mx-auto max-w-4xl px-6 py-12 space-y-10">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-slate-300">
            {copy.global.appName}
          </p>
          <h1 className="text-3xl font-semibold">{copy.methodology.pageTitle}</h1>
          <p className="text-sm text-slate-300">{copy.global.sourceLine}</p>
          <p className="text-sm text-slate-300">{copy.global.caveatLine}</p>
        </header>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.whatMeasures}</h2>
          <p className="text-sm text-slate-200">{copy.methodology.paragraphs.whatMeasures}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.whatNot}</h2>
          <p className="text-sm text-slate-200">{copy.methodology.paragraphs.whatNot}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.extraction}</h2>
          <p className="text-sm text-slate-200">{copy.methodology.paragraphs.extraction}</p>
          <p className="text-sm text-slate-200">{copy.dataQuality.helper}</p>
          <p className="text-sm text-slate-200">{copy.methodology.paragraphs.secAccess}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.drift}</h2>
          <p className="text-sm text-slate-200">{copy.methodology.paragraphs.drift}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.sanityCheck}</h2>
          <p className="text-sm text-slate-200">{copy.methodology.paragraphs.sanityCheck}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.relatedWork}</h2>
          <p className="text-sm text-slate-200">{copy.methodology.paragraphs.relatedWorkLead}</p>
          <ul className="space-y-2 text-sm text-slate-200 list-disc pl-5">
            {copy.methodology.relatedWork.items.map((it) => (
              <li key={it.href}>
                <a
                  className="underline underline-offset-2 hover:opacity-90"
                  href={it.href}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {it.label}
                </a>
                <span className="text-slate-300"> - {it.note}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-400">
            {copy.methodology.paragraphs.relatedWorkDisclaimer}
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">
            {copy.methodology.headings.securityPrivacy}
          </h2>
          <p className="text-sm text-slate-200">{copy.methodology.paragraphs.securityPrivacy}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.credits}</h2>
          <p className="text-sm text-slate-300">{copy.methodology.paragraphs.credits}</p>
        </section>
      </div>
    </main>
  )
}
