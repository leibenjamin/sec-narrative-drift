import { useEffect } from "react"

type PageMetadataProps = {
  title: string
  description: string
}

const DESCRIPTION_SELECTOR = 'meta[name="description"]'

function getDescriptionMetaTag(): HTMLMetaElement {
  const existing = document.head.querySelector<HTMLMetaElement>(DESCRIPTION_SELECTOR)
  if (existing) return existing

  const created = document.createElement("meta")
  created.name = "description"
  document.head.appendChild(created)
  return created
}

export default function PageMetadata({ title, description }: PageMetadataProps) {
  useEffect(() => {
    document.title = title
    const meta = getDescriptionMetaTag()
    meta.setAttribute("content", description)
  }, [description, title])

  return null
}
