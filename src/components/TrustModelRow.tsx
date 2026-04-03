export type TrustModelItem = {
  label: string
}

type TrustModelRowProps = {
  items: TrustModelItem[]
}

export default function TrustModelRow({ items }: TrustModelRowProps) {
  return (
    <section
      aria-labelledby="methodology-trust-model"
      className="rounded-[1.35rem] border border-white/10 bg-slate-950/42 p-3.5"
    >
      <div
        id="methodology-trust-model"
        className="text-[11px] uppercase tracking-[0.28em] text-slate-400"
      >
        Trust model
      </div>
      <ul className="mt-3 grid grid-cols-2 gap-2 xl:grid-cols-4">
        {items.map((item) => (
          <li
            key={item.label}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] font-medium tracking-[0.04em] text-slate-100"
          >
            <span className="h-2 w-2 rounded-full bg-sky-300" aria-hidden="true" />
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
