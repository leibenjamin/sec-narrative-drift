export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
}

export function assertSafeExternalUrl(url: string): string {
  let parsed: URL
  try {
    parsed = new URL(url)
  } catch {
    throw new Error("Invalid URL")
  }

  if (parsed.protocol !== "https:" || parsed.hostname !== "www.sec.gov") {
    throw new Error("Unsafe external URL")
  }

  return parsed.toString()
}
