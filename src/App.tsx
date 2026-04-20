// src/App.tsx
import { Suspense, lazy, useEffect } from "react"
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom"
import AppHeader from "./components/AppHeader"
import ErrorBoundary from "./components/ErrorBoundary"
import { copy } from "./lib/copy"

const Home = lazy(() => import("./pages/Home"))
const Story = lazy(() => import("./pages/Story"))
const Companies = lazy(() => import("./pages/Companies"))
const Company = lazy(() => import("./pages/Company"))
const Methodology = lazy(() => import("./pages/Methodology"))

function ScrollToHash() {
  const { hash, pathname, search } = useLocation()

  useEffect(() => {
    if (!hash) return

    const targetId = decodeURIComponent(hash.slice(1))
    let attempts = 0
    let timeoutId = 0

    const scrollToTarget = () => {
      const target = document.getElementById(targetId)
      if (target) {
        target.scrollIntoView({ block: "start", inline: "nearest" })
        return
      }

      attempts += 1
      if (attempts >= 20) return
      timeoutId = window.setTimeout(scrollToTarget, 100)
    }

    timeoutId = window.setTimeout(scrollToTarget, 0)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [hash, pathname, search])

  return null
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <ScrollToHash />
        <AppHeader />
        <Suspense
          fallback={
            <main className="min-h-screen page-fade">
              <div className="mx-auto max-w-6xl px-6 py-16">
                <p className="text-sm text-slate-300">{copy.global.loading.base}</p>
              </div>
            </main>
          }
        >
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/story" element={<Story />} />
            <Route path="/companies" element={<Companies />} />
            <Route path="/company" element={<Company />} />
            <Route path="/company/:ticker" element={<Company />} />
            <Route path="/methodology" element={<Methodology />} />
            {/* optional: send unknown URLs back home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
