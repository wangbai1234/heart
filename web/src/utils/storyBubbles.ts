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
 *
 * Pending-speaker rule (matches backend split_gm_text): a lone `**角色名**` line
 * with no 台词 does NOT emit an empty dialogue bubble — it is held as a pending
 * speaker and the next plain-prose line becomes that speaker's 台词. If the next
 * line is structured / 【旁白】 / end-of-text, the pending speaker is dropped
 * silently (never an empty oval). Live-stream transient: while streamText is
 * just `**贺听澜**` (or `**贺听澜**\n`) this returns `[]`, so the caller shows
 * TypingDots instead of an empty bubble; once the 台词 streams in it fills a
 * proper dialogue bubble with no visible jump.
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

// Inline （action） span, used to re-scan the text after a **角色名** marker.
const INLINE_ACTION_RE = /（([^）]+)）/g

/** Segment the text after a `**角色名**` marker into ordered bubbles.
 *  Mirrors backend prompt.py :: _split_npc_rest — inline （动作） becomes its own
 *  action bubble; every other span is that speaker's 台词 (dialogue). An empty
 *  rest yields a single empty-content dialogue bubble so the bare-speaker /
 *  pending-speaker path still recognises a lone `**角色名**` line. */
function splitNpcRest(name: string, rest: string): ParsedBubble[] {
  if (!rest) return [{ kind: 'dialogue', npcName: name, content: '' }]

  const bubbles: ParsedBubble[] = []
  const pushDialogue = (text: string) => {
    const t = text.trim().replace(QUOTE_STRIP_RE, '').trim()
    if (t) bubbles.push({ kind: 'dialogue', npcName: name, content: t })
  }

  let cursor = 0
  INLINE_ACTION_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = INLINE_ACTION_RE.exec(rest)) !== null) {
    pushDialogue(rest.slice(cursor, m.index))
    const inner = m[1].trim()
    if (inner) bubbles.push({ kind: 'action', npcName: null, content: inner })
    cursor = m.index + m[0].length
  }
  pushDialogue(rest.slice(cursor))

  if (bubbles.length === 0) return [{ kind: 'dialogue', npcName: name, content: '' }]
  return bubbles
}

/** Split a single line into ordered action/dialogue/narration segments, or
 *  null when the line is pure narration (caller buffers it). */
function classifyStructuredLine(stripped: string): ParsedBubble[] | null {
  // 1. **角色名** dialogue (highest priority, takes the whole line). The rest is
  //    re-scanned so an inline （动作） splits into its own action bubble instead
  //    of being swallowed into the speaker's dialogue bubble.
  const npcMatch = NPC_LINE_RE.exec(stripped)
  if (npcMatch) {
    return splitNpcRest(npcMatch[1].trim(), npcMatch[2].trim())
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

/** A lone `**角色名**` line: one named dialogue bubble with empty 台词. */
function isBareSpeaker(structured: ParsedBubble[] | null): boolean {
  return (
    structured !== null &&
    structured.length === 1 &&
    structured[0].kind === 'dialogue' &&
    !!structured[0].npcName &&
    structured[0].content.trim() === ''
  )
}

/** Split a GM response into ordered bubbles. Degrades to a single narration
 *  bubble when no structure is recognised (never returns raw markup). */
export function splitGmText(text: string): ParsedBubble[] {
  const raw = precleanGmText(text ?? '').trim()
  if (!raw) return []

  const bubbles: ParsedBubble[] = []
  let narrationBuf: string[] = []
  let pendingSpeaker: string | null = null
  let sawBareSpeaker = false

  const flushNarration = () => {
    const content = narrationBuf.join('\n').trim()
    if (content) bubbles.push({ kind: 'narration', npcName: null, content })
    narrationBuf = []
  }

  for (const line of raw.split('\n')) {
    const stripped = line.trim()
    if (!stripped) {
      // Blank lines survive between a pending speaker and its 台词.
      if (pendingSpeaker !== null) continue
      narrationBuf.push('')
      continue
    }
    const structured = classifyStructuredLine(stripped)
    if (isBareSpeaker(structured)) {
      // A prior pending speaker with no 台词 → drop it silently, not an empty bubble.
      pendingSpeaker = null
      flushNarration()
      pendingSpeaker = structured![0].npcName
      sawBareSpeaker = true
      continue
    }
    if (structured !== null) {
      pendingSpeaker = null
      flushNarration()
      bubbles.push(...structured)
      continue
    }
    const narrMatch = NARRATION_PREFIX_RE.exec(stripped)
    if (narrMatch !== null) {
      pendingSpeaker = null
      const content = narrMatch[1].trim()
      if (content) narrationBuf.push(content)
      continue
    }
    // Unmarked prose: attach EXACTLY the first plain line to a pending speaker.
    if (pendingSpeaker !== null) {
      bubbles.push({ kind: 'dialogue', npcName: pendingSpeaker, content: stripped })
      pendingSpeaker = null
      continue
    }
    narrationBuf.push(stripped)
  }
  flushNarration()

  // Pending speaker still set at EOF → dropped (emit nothing). Guard the
  // degradation fallback so a lone `**name**` never resurfaces as narration.
  if (bubbles.length === 0 && !sawBareSpeaker) {
    return [{ kind: 'narration', npcName: null, content: raw }]
  }
  return bubbles
}
