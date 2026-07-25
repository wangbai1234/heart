/**
 * Client-side port of the SS09 GM bubble splitter
 * (backend/heart/ss09_story/prompt.py :: _preclean_gm_text + split_gm_text).
 *
 * WHY a port: during a streaming turn the server emits raw `text_delta` frames
 * first, then the split `message_bubble` frames only after generation finishes.
 * Rendering the raw deltas as one grey blob and then swapping to bubbles is the
 * jarring "先小字、再刷新成气泡" symptom. Instead we run the SAME splitting logic
 * here on the accumulating stream text, so correct 旁白/对话/action bubbles show
 * live and the final server `message_bubble` frames land on identical structure
 * (no visible jump).
 *
 * This MUST stay behaviourally in sync with the Python source: streaming, the
 * opening turn, and a reload all render from the same contract.
 */

export type StoryBubbleKind = 'narration' | 'dialogue' | 'action'

export interface ParsedBubble {
  kind: StoryBubbleKind
  npcName: string | null
  content: string
}

// **角色名** at the start of a line, capturing name + the rest.
const NPC_LINE_RE = /^\s*\*\*([^*\n]{1,24})\*\*[:：]?\s*(.*)$/
// A narration prefix.
const NARRATION_PREFIX_RE = /^\s*【旁白】\s*([\s\S]*)$/
// Quote characters: ASCII " + Chinese curly “ ” + corner 「 」.
const QUOTE_STRIP_RE = /^["“”「]|["“”」]$/g

// ── off-contract markup normalisation (mirrors _preclean_gm_text) ──
const LATEX_TEXT_RE = /\\text\{([^{}]*)\}/g
const LATEX_TEXTCOLOR_RE = /\\textcolor\{[^{}]*\}\{([^{}]*)\}/g
const LATEX_COLORBOX_RE = /\\colorbox\{[^{}]*\}\{([^{}]*)\}/g
const LATEX_DELIM_RE = /\\[()[\]]/g
const CODE_FENCE_LINE_RE = /^[ \t　]*```[^\n]*$/gm
const DANMU_PREFIX_RE = /^([ \t　]*)【弹幕】[ \t　]*/gm
const HR_LINE_RE = /^[ \t　]*[-—*=＝─]{3,}[ \t　]*$/gm

function precleanGmText(text: string): string {
  if (!text) return text
  let out = text
  // 1. Unwrap LaTeX \colorbox speech bubbles → curly-quoted dialogue.
  out = out.replace(LATEX_TEXT_RE, '$1')
  for (let i = 0; i < 3; i++) {
    const next = out.replace(LATEX_TEXTCOLOR_RE, '$1')
    if (next === out) break
    out = next
  }
  for (let i = 0; i < 3; i++) {
    const next = out.replace(LATEX_COLORBOX_RE, '“$1”')
    if (next === out) break
    out = next
  }
  out = out.replace(LATEX_DELIM_RE, '')
  // 2. Drop markdown code-fence lines (```text 心理活动 wrappers).
  out = out.replace(CODE_FENCE_LINE_RE, '')
  // 3. Strip a leading 【弹幕】 marker, keeping its text as narration.
  out = out.replace(DANMU_PREFIX_RE, '$1')
  // 4. Drop pure horizontal-rule separator lines.
  out = out.replace(HR_LINE_RE, '')
  return out
}

/** Split a single line into ordered action/dialogue/narration segments, or
 *  null when the line is pure narration (caller buffers it). */
function classifyStructuredLine(stripped: string): ParsedBubble[] | null {
  // 1. **角色名** dialogue (highest priority, takes the whole line).
  const npcMatch = NPC_LINE_RE.exec(stripped)
  if (npcMatch) {
    const content = npcMatch[2].trim().replace(QUOTE_STRIP_RE, '')
    return [{ kind: 'dialogue', npcName: npcMatch[1].trim(), content }]
  }

  // 2. 【旁白】 prefix → pure narration; let the caller strip it.
  if (NARRATION_PREFIX_RE.test(stripped)) return null

  // 3. Scan for inline （action） and “dialogue” spans, preserving order.
  const bubbles: ParsedBubble[] = []
  let pos = 0
  let narrationBuf = ''
  let hasStructured = false

  const flushNarration = () => {
    const t = narrationBuf.trim()
    if (t) bubbles.push({ kind: 'narration', npcName: null, content: t })
    narrationBuf = ''
  }

  while (pos < stripped.length) {
    const rest = stripped.slice(pos)
    const actionMatch = /^（([^）]+)）/.exec(rest)
    if (actionMatch) {
      flushNarration()
      bubbles.push({ kind: 'action', npcName: null, content: actionMatch[1].trim() })
      hasStructured = true
      pos += actionMatch[0].length
      continue
    }
    const dialogueMatch = /^["“”「]([^"“”」]+)["“”」]/.exec(
      rest,
    )
    if (dialogueMatch) {
      flushNarration()
      bubbles.push({ kind: 'dialogue', npcName: null, content: dialogueMatch[1].trim() })
      hasStructured = true
      pos += dialogueMatch[0].length
      continue
    }
    narrationBuf += stripped[pos]
    pos += 1
  }
  flushNarration()

  return hasStructured ? bubbles : null
}

/** Split a GM response into ordered bubbles. Degrades to a single narration
 *  bubble when no structure is recognised (never returns raw markup). */
export function splitGmText(text: string): ParsedBubble[] {
  const raw = precleanGmText(text ?? '').trim()
  if (!raw) return []

  const bubbles: ParsedBubble[] = []
  let narrationBuf: string[] = []

  const flushNarration = () => {
    const content = narrationBuf.join('\n').trim()
    if (content) bubbles.push({ kind: 'narration', npcName: null, content })
    narrationBuf = []
  }

  for (const line of raw.split('\n')) {
    const stripped = line.trim()
    if (!stripped) {
      narrationBuf.push('')
      continue
    }
    const structured = classifyStructuredLine(stripped)
    if (structured !== null) {
      flushNarration()
      bubbles.push(...structured)
      continue
    }
    const narrMatch = NARRATION_PREFIX_RE.exec(stripped)
    const content = narrMatch ? narrMatch[1].trim() : stripped
    if (content) narrationBuf.push(content)
  }
  flushNarration()

  if (bubbles.length === 0) return [{ kind: 'narration', npcName: null, content: raw }]
  return bubbles
}
