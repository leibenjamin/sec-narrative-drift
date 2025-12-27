import { Link } from "react-router-dom"
import { copy } from "../lib/copy"

export default function Methodology() {
  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-4xl px-6 py-12 space-y-10">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider opacity-70">
            {copy.global.appName}
          </p>
          <h1 className="text-3xl font-semibold">{copy.methodology.pageTitle}</h1>
          <p className="text-sm opacity-70">{copy.global.sourceLine}</p>
          <p className="text-sm opacity-70">{copy.global.caveatLine}</p>
          <Link
            to="/"
            className="inline-flex items-center rounded-md border border-black/20 px-3 py-2 text-xs hover:bg-black/5"
          >
            {copy.nav.home}
          </Link>
        </header>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.whatMeasures}</h2>
          <p className="text-sm opacity-80">{copy.methodology.paragraphs.whatMeasures}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.whatNot}</h2>
          <p className="text-sm opacity-80">{copy.methodology.paragraphs.whatNot}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.extraction}</h2>
          <p className="text-sm opacity-80">{copy.methodology.paragraphs.extraction}</p>
          <p className="text-sm opacity-80">{copy.dataQuality.helper}</p>
          <p className="text-sm opacity-80">{copy.methodology.paragraphs.secAccess}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.drift}</h2>
          <p className="text-sm opacity-80">{copy.methodology.paragraphs.drift}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.sanityCheck}</h2>
          <p className="text-sm opacity-80">{copy.methodology.paragraphs.sanityCheck}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{copy.methodology.headings.credits}</h2>
          <p className="text-sm opacity-70">{copy.methodology.paragraphs.credits}</p>
        </section>
      </div>
    </main>
  )
}
