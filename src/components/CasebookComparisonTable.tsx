import {
  CASEBOOK_COMPARISON_ROWS,
  PUBLIC_CASEBOOK_TICKERS,
  PUBLIC_CASEBOOK_CASES,
} from "../lib/casebookContent"

export default function CasebookComparisonTable() {
  return (
    <section className="rounded-[1.35rem] border border-white/10 bg-slate-950/46 p-4 shadow-[0_18px_40px_rgba(2,6,23,0.18)] sm:p-5">
      <div className="overflow-x-auto">
        <table className="w-full min-w-4xl table-fixed text-left text-[13px] text-slate-100">
          <thead>
            <tr className="border-b border-white/10">
              <th className="w-24 px-3 py-3 text-[11px] uppercase tracking-[0.22em] text-slate-400 sm:w-28">
                Approach across cases
              </th>
              {PUBLIC_CASEBOOK_TICKERS.map((ticker) => (
                <th
                  key={ticker}
                  className="w-32 px-3 py-3 align-top text-[11px] uppercase tracking-[0.22em] text-slate-300"
                >
                  <div className="text-base font-semibold tracking-normal text-slate-50">
                    {ticker}
                  </div>
                  <div className="mt-1 text-[11px] normal-case leading-5 text-slate-400">
                    {PUBLIC_CASEBOOK_CASES[ticker].publicRoleLabel}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {CASEBOOK_COMPARISON_ROWS.map((row) => (
              <tr key={row.label} className="border-b border-white/6 align-top">
                <th className="px-3 py-3 text-[11px] uppercase tracking-[0.18em] text-slate-400">
                  {row.label}
                </th>
                {PUBLIC_CASEBOOK_TICKERS.map((ticker) => (
                  <td
                    key={`${row.label}-${ticker}`}
                    className="px-3 py-3 text-[13px] leading-5 text-slate-200"
                  >
                    {row.values[ticker]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
