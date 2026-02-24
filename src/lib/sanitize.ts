import { withBase } from "./paths"

const URL_SCHEME_RE = /^[A-Za-z][A-Za-z0-9+.-]*:/

function hasControlChars(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const codePoint = value.charCodeAt(index)
    if (codePoint <= 0x1f || codePoint === 0x7f) return true
  }
  return false
}

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

export function assertSameOriginPathLike(pathValue: string): string {
  const normalized = pathValue.trim().replace(/\\/g, "/").replace(/^\.\/+/, "")
  if (!normalized || hasControlChars(normalized)) {
    throw new Error("Invalid path-like value")
  }
  if (URL_SCHEME_RE.test(normalized) || normalized.startsWith("//")) {
    throw new Error("External URL schemes are not allowed")
  }
  if (normalized.includes("..")) {
    throw new Error("Path traversal is not allowed")
  }
  if (normalized.startsWith("/")) {
    return normalized
  }
  if (normalized.startsWith("inputs/")) {
    return withBase(`data/sec_narrative_drift_lab/llm_inputs_v2/${normalized}`)
  }
  if (normalized.startsWith("public/")) {
    return withBase(normalized.replace(/^public\//, ""))
  }
  if (normalized.startsWith("data/")) {
    return withBase(normalized)
  }
  throw new Error("Unsupported path-like value")
}

export function isHttpsUrl(value: string): boolean {
  try {
    const parsed = new URL(value)
    return parsed.protocol === "https:"
  } catch {
    return false
  }
}
