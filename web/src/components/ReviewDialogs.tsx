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
  const open = item !== null
  const approved = item?.review_status === 'approved'
  return (
    <NoticeDialog
      open={open}
      onClose={onConfirm}
      title={approved ? '角色审核通过' : '角色审核未通过'}
    >
      {approved ? (
        <>
          「{item?.display_name}」已通过审核
          <br />
          角色已公开，可通过链接分享
        </>
      ) : (
        <>
          「{item?.display_name}」未通过审核
          {item?.review_reason ? (
            <>
              <br />
              原因：{item.review_reason}
            </>
          ) : null}
          <br />
          可修改后重新提交
        </>
      )}
    </NoticeDialog>
  )
}
