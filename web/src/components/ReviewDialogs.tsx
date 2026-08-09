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
          「{item?.display_name}」已通过审核并公开
          <br />
          奖励 100 yuoyuo币 已到账
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

/**
 * 发布激励弹窗 — shown once per day to users who have no approved characters yet.
 * Explains the publish reward so they're nudged to create + publish.
 */
export function PublishIncentiveDialog({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  return (
    <NoticeDialog open={open} onClose={onClose} title="公开角色，领取奖励">
      创建并公开角色，审核通过即得 100 yuoyuo币
      <br />
      累计通过 5 个角色，再送一个月进阶版会员
    </NoticeDialog>
  )
}
