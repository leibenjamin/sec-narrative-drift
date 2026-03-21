import { z } from 'zod'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Disable Zod's JIT code generation so schema validation works under
// strict Content-Security-Policy (script-src 'self' without 'unsafe-eval').
z.config({ jitless: true })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
