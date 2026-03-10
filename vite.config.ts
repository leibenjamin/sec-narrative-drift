import { defineConfig, loadEnv } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

const URL_SCHEME_RE = /^[A-Za-z][A-Za-z0-9+.-]*:/
function hasControlChars(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index)
    if (code <= 0x1f || code === 0x7f) return true
  }
  return false
}


function normalizeBasePath(rawValue: string | undefined): string {
  const candidate = (rawValue ?? "/").trim()
  if (!candidate) return "/"
  if (hasControlChars(candidate)) {
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
