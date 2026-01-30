import { defineConfig, loadEnv } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const base = env.VITE_BASE_PATH || "/"

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
