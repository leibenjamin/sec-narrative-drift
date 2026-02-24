import { defineConfig, loadEnv } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

const URL_SCHEME_RE = /^[A-Za-z][A-Za-z0-9+.-]*:/
const CONTROL_CHAR_RE = /[\u0000-\u001F\u007F]/

function normalizeBasePath(rawValue: string | undefined): string {
  const candidate = (rawValue ?? "/").trim()
  if (!candidate) return "/"
  if (CONTROL_CHAR_RE.test(candidate)) {
    throw new Error("VITE_BASE_PATH contains control characters.")
  }
  if (URL_SCHEME_RE.test(candidate) || candidate.startsWith("//")) {
    throw new Error("VITE_BASE_PATH must be a path-like value, not a full URL.")
  }
  const withLeadingSlash = candidate.startsWith("/") ? candidate : `/${candidate}`
  const normalized = withLeadingSlash.replace(/\/{2,}/g, "/")
  return normalized.endsWith("/") ? normalized : `${normalized}/`
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const base = normalizeBasePath(env.VITE_BASE_PATH)

  return {
    base,
    plugins: [react(), tailwindcss()],
    build: {
      // Disable source maps in production to avoid exposing source code
      sourcemap: mode === "development",
      rollupOptions: {
        output: {
          manualChunks: {
            // Vendor chunk for better caching - React libraries change less frequently
            "react-vendor": ["react", "react-dom", "react-router-dom"],
          },
        },
      },
    },
  }
})
