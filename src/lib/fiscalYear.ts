export function formatFiscalYearLabel(year: number | string): string {
  const normalized = String(year).trim()
  if (!normalized) return "FY?"
  return normalized.toUpperCase().startsWith("FY") ? normalized.toUpperCase() : `FY${normalized}`
}

export function formatFiscalYearRange(fromYear: number | string, toYear: number | string): string {
  return `${formatFiscalYearLabel(fromYear)} vs ${formatFiscalYearLabel(toYear)}`
}
