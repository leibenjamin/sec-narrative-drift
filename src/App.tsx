// src/App.tsx
import { Suspense, lazy } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import AppHeader from "./components/AppHeader"
import { copy } from "./lib/copy"

const Home = lazy(() => import("./pages/Home"))
const Companies = lazy(() => import("./pages/Companies"))
const Company = lazy(() => import("./pages/Company"))
const Methodology = lazy(() => import("./pages/Methodology"))

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <AppHeader />
      <Suspense
        fallback={
          <main className="min-h-screen">
            <div className="mx-auto max-w-6xl px-6 py-16">
              <p className="text-sm text-slate-300">{copy.global.loading.base}</p>
            </div>
          </main>
        }
      >
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/companies" element={<Companies />} />
          <Route path="/company" element={<Company />} />
          <Route path="/company/:ticker" element={<Company />} />
          <Route path="/methodology" element={<Methodology />} />
          {/* optional: send unknown URLs back home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
