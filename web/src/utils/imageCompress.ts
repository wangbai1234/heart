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
