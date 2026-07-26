/**
 * Resize + re-encode an image File as WebP.
 *
 * Used by the avatar upload path in ProfileEditPage AND CreateCharacterPage —
 * both need the compressed output small enough that, if the backend has to
 * fall back to a base64 data URL (S3 not configured), the resulting string
 * fits under CharacterDraft.avatar_url max_length=200000 chars (~130 KB raw).
 *
 * On any decode failure returns the original file so the upload still tries.
 */
export function compressImage(file: File, maxSize: number, quality = 0.85): Promise<File> {
  return new Promise((resolve) => {
    const objectUrl = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(objectUrl)
      const canvas = document.createElement('canvas')
      let { width, height } = img
      if (width > maxSize || height > maxSize) {
        if (width > height) {
          height = (height / width) * maxSize
          width = maxSize
        } else {
          width = (width / height) * maxSize
          height = maxSize
        }
      }
      canvas.width = width
      canvas.height = height
      canvas.getContext('2d')!.drawImage(img, 0, 0, width, height)
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const webpName = file.name.replace(/\.[^.]+$/, '.webp')
            resolve(new File([blob], webpName, { type: 'image/webp' }))
          } else {
            resolve(file)
          }
        },
        'image/webp',
        quality,
      )
    }
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      resolve(file)
    }
    img.src = objectUrl
  })
}

/**
 * Compress an image until it fits under `targetBytes`, degrading gracefully
 * instead of rejecting the user's upload.
 *
 * The old behaviour hard-rejected anything still over the cap after a single
 * 800px/0.8 pass ("封面图太大了，请换一张更小的图片") — unreasonable, since a
 * normal phone photo is several MB and users won't hand-shrink it. Instead we
 * step the WebP quality down, then the max dimension down, re-encoding until the
 * result is under budget. If even the smallest attempt overshoots we return that
 * smallest attempt (best effort) rather than blocking the upload — the backend
 * still enforces its own 8MB hard limit.
 */
export async function compressImageToTarget(
  file: File,
  targetBytes: number,
  { startSize = 800, minSize = 320 }: { startSize?: number; minSize?: number } = {},
): Promise<File> {
  // (maxSize, quality) ladder from best→smallest. Quality drops first (cheap,
  // preserves framing), then dimensions.
  const ladder: Array<[number, number]> = [
    [startSize, 0.8],
    [startSize, 0.65],
    [startSize, 0.5],
    [640, 0.6],
    [480, 0.6],
    [minSize, 0.55],
  ]

  let smallest: File | null = null
  for (const [maxSize, quality] of ladder) {
    const out = await compressImage(file, maxSize, quality).catch(() => null)
    if (!out) continue
    if (out.size <= targetBytes) return out
    if (!smallest || out.size < smallest.size) smallest = out
  }
  // Everything overshot — hand back the smallest we produced (or the original if
  // every encode failed) and let the backend be the final gatekeeper.
  return smallest ?? file
}
