import { useParams } from 'react-router-dom'
import { SharedMemoriesDialog } from '../components/SharedMemoriesDialog'
import { useSafeBack } from '../hooks/useSafeBack'

/** Bookmarkable access to the same private dialog used by relationship upgrades. */
export function SharedMemoriesPage() {
  const { id = '' } = useParams<{ id: string }>()
  const back = useSafeBack(`/character/${encodeURIComponent(id)}`)
  return <SharedMemoriesDialog characterId={id} open onClose={back} />
}
