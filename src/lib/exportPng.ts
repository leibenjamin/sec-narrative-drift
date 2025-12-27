export async function exportExecBriefPng(
  svgElement: SVGSVGElement,
  filename: string
): Promise<void> {
  if (!svgElement) return

  const width = Number(svgElement.getAttribute("width")) || 1200
  const height = Number(svgElement.getAttribute("height")) || 630
  const serializer = new XMLSerializer()
  const svgString = serializer.serializeToString(svgElement)
  const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" })
  const url = URL.createObjectURL(svgBlob)

  await new Promise<void>((resolve) => {
    const img = new Image()
    img.onload = () => {
      const scale = window.devicePixelRatio || 1
      const canvas = document.createElement("canvas")
      canvas.width = width * scale
      canvas.height = height * scale
      const ctx = canvas.getContext("2d")

      if (!ctx) {
        URL.revokeObjectURL(url)
        resolve()
        return
      }

      ctx.scale(scale, scale)
      ctx.fillStyle = "#ffffff"
      ctx.fillRect(0, 0, width, height)
      ctx.drawImage(img, 0, 0, width, height)

      canvas.toBlob((blob) => {
        if (blob) {
          const downloadUrl = URL.createObjectURL(blob)
          const link = document.createElement("a")
          link.href = downloadUrl
          link.download = filename
          link.click()
          URL.revokeObjectURL(downloadUrl)
        }
        URL.revokeObjectURL(url)
        resolve()
      }, "image/png")
    }

    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve()
    }

    img.src = url
  })
}
