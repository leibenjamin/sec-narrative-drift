export function withBase(path: string): string {
  const baseRaw = import.meta.env.BASE_URL || "/"
  const base = baseRaw.endsWith("/") ? baseRaw : `${baseRaw}/`
  const normalizedPath = path.replace(/^\/+/, "")
  return `${base}${normalizedPath}`
}
