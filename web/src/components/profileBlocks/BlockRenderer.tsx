import type { ChromePalette } from '../../pages/CharacterProfilePage'
import type { ProfileBlock } from '../../services/api'
import { DossierBlock } from './DossierBlock'
import { QuoteBlock } from './QuoteBlock'
import { TimelineBlock } from './TimelineBlock'
import { ObjectsBlock } from './ObjectsBlock'
import { ContrastBlock } from './ContrastBlock'
import { ProseBlock } from './ProseBlock'

interface BlockRendererProps {
  blocks: ProfileBlock[]
  chrome: ChromePalette
}

/** 统一分发区块渲染，不同 type 交界处加大间隔（quote 前后呼吸更多）。 */
export function BlockRenderer({ blocks, chrome }: BlockRendererProps) {
  return (
    <div className="flex flex-col gap-8">
      {blocks.map((block, i) => {
        const prev = i > 0 ? blocks[i - 1] : null
        const needsBreathing = block.type === 'quote' || prev?.type === 'quote'
        const gap = needsBreathing ? 'mt-6' : ''
        const key = `${block.type}-${i}`

        return (
          <div key={key} className={gap}>
            {block.type === 'dossier' && <DossierBlock block={block} chrome={chrome} />}
            {block.type === 'quote' && <QuoteBlock block={block} chrome={chrome} />}
            {block.type === 'timeline' && <TimelineBlock block={block} chrome={chrome} />}
            {block.type === 'objects' && <ObjectsBlock block={block} chrome={chrome} />}
            {block.type === 'contrast' && <ContrastBlock block={block} chrome={chrome} />}
            {block.type === 'prose' && <ProseBlock block={block} chrome={chrome} />}
          </div>
        )
      })}
    </div>
  )
}
