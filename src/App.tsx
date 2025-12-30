// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import Home from "./pages/Home"
import Companies from "./pages/Companies"
import Company from "./pages/Company"
import Methodology from "./pages/Methodology"

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/companies" element={<Companies />} />
        <Route path="/company" element={<Company />} />
        <Route path="/company/:ticker" element={<Company />} />
        <Route path="/methodology" element={<Methodology />} />
        {/* optional: send unknown URLs back home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
