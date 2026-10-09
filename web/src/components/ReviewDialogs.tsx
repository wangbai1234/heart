import { useTranslation } from 'react-i18next'
import { uiText } from '../i18n/text'
import { NoticeDialog } from './ui/NoticeDialog'
import type { ReviewUpdateDTO } from '../services/api'

/**
 * 角色审核结果弹窗 — shown once per terminal result (approved / rejected) that
 * the user hasn't confirmed yet. Confirming acks the result server-side so it
 * never re-fires. Not auto-dismissed: the user must read and confirm.
 */
export function ReviewResultDialog({
  item,
  onConfirm,
}: {
  item: ReviewUpdateDTO | null
  onConfirm: () => void
}) {
  useTranslation()
  const open = item !== null
  const approved = item?.review_status === 'approved'
  return (
    <NoticeDialog
      open={open}
      onClose={onConfirm}
      title={approved ? uiText('more72') : uiText('more73')}
    >
      {approved ? (
        <>
          「{item?.display_name}{uiText('more74')}<br />
          {uiText('more75')}</>
      ) : (
        <>
          「{item?.display_name}{uiText('more76')}{item?.review_reason ? (
            <>
              <br />
              {uiText('more77')}{item.review_reason}
            </>
          ) : null}
          <br />
          {uiText('more78')}</>
      )}
    </NoticeDialog>
  )
}
