import type { ReactElement } from 'react'
import { escapeHtml } from './escapeHtml'

/**
 * Parse rich opening format with <scene>, <plot>, <dialogue> tags.
 * Returns JSX elements with styled spans for each segment type.
 */
export function parseRichOpening(content: string): ReactElement[] {
  // Regex to match <scene>...</scene>, <plot>...</plot>, <dialogue>...</dialogue>
  // Captures tag type and inner content
  const tagRegex = /<(scene|plot|dialogue)>(.*?)<\/\1>/gs
  const segments: ReactElement[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = tagRegex.exec(content)) !== null) {
    // Add any plain text before this tag
    if (match.index > lastIndex) {
      const plainText = content.slice(lastIndex, match.index).trim()
      if (plainText) {
        segments.push(
          <span key={`plain-${lastIndex}`}>
            {escapeHtml(plainText)}
          </span>
        )
      }
    }

    const tagType = match[1]
    const innerContent = match[2].trim()
    const escapedContent = escapeHtml(innerContent)

    // Style based on tag type
    if (tagType === 'scene') {
      // Scene: italic, muted color
      segments.push(
        <span key={`scene-${match.index}`} className="italic opacity-60">
          {escapedContent}
        </span>
      )
    } else if (tagType === 'plot') {
      // Plot: regular text
      segments.push(
        <span key={`plot-${match.index}`}>
          {escapedContent}
        </span>
      )
    } else if (tagType === 'dialogue') {
      // Dialogue: heavier weight
      segments.push(
        <span key={`dialogue-${match.index}`} className="font-medium">
          {escapedContent}
        </span>
      )
    }

    lastIndex = match.index + match[0].length
  }

  // Add any remaining plain text after the last tag
  if (lastIndex < content.length) {
    const remaining = content.slice(lastIndex).trim()
    if (remaining) {
      segments.push(
        <span key={`plain-${lastIndex}`}>
          {escapeHtml(remaining)}
        </span>
      )
    }
  }

  return segments.length > 0 ? segments : [<span key="plain">{escapeHtml(content)}</span>]
}
