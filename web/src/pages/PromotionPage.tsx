import { useEffect, useId, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppPageContent, AppPageShell } from '../components/ui/AppPageShell'
import { TabBar } from '../components/ui/TabBar'
import { getPromotionStatus, submitPromotion, type PromotionStatus, type PromotionSubmission } from '../services/api'
import { useToastStore } from '../stores/toastStore'

const PLATFORM_LABELS = { douyin: '抖音', xiaohongshu: '小红书' } as const
const MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024

export function PromotionPage() {
  const [data, setData] = useState<PromotionStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState<'ambassador' | 'creator'>('ambassador')
  const [platform, setPlatform] = useState<'douyin' | 'xiaohongshu'>('douyin')
  const [postUrl, setPostUrl] = useState('')
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [fileInputVersion, setFileInputVersion] = useState(0)
  const [milestoneSource, setMilestoneSource] = useState<PromotionSubmission | null>(null)
  const [likesCount, setLikesCount] = useState('')
  const showToast = useToastStore((state) => state.show)
  const navigate = useNavigate()

  const refresh = async () => {
    try {
      setData(await getPromotionStatus())
    } catch {
      showToast('福利数据加载失败', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refresh() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const resetFile = () => {
    setFile(null)
    setFileInputVersion((value) => value + 1)
  }

  const selectFile = (nextFile: File | null) => {
    if (!nextFile) {
      resetFile()
      return
    }
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(nextFile.type)) {
      showToast('截图仅支持 JPG、PNG、WebP', 'info')
      resetFile()
      return
    }
    if (nextFile.size > MAX_SCREENSHOT_BYTES) {
      showToast('截图不能超过 8MB', 'info')
      resetFile()
      return
    }
    setFile(nextFile)
  }

  const changeMode = (nextMode: 'ambassador' | 'creator') => {
    setMode(nextMode)
    setMilestoneSource(null)
    resetFile()
  }

  const submit = async () => {
    if (!data || data.today_remaining <= 0) return showToast('今日提交次数已用完', 'info')
    if (mode === 'ambassador' && !file) return showToast('请上传安利截图', 'info')
    if (mode === 'creator' && !postUrl.trim()) return showToast('请粘贴作品链接', 'info')
    setBusy(true)
    try {
      await submitPromotion({
        taskType: mode,
        platform,
        file,
        postUrl: mode === 'creator' ? postUrl.trim() : undefined,
        title: title.trim() || undefined,
      })
      showToast('已提交审核，通过后奖励自动到账', 'success')
      resetFile()
      setPostUrl('')
      setTitle('')
      await refresh()
    } catch (error) {
      showToast(error instanceof Error ? error.message : '提交失败', 'error')
    } finally {
      setBusy(false)
    }
  }

  const submitLikes = async () => {
    if (!milestoneSource || !likesCount || Number(likesCount) < 0) return showToast('请填写当前点赞数', 'info')
    if (!file) return showToast('请上传最新点赞截图', 'info')
    setBusy(true)
    try {
      await submitPromotion({
        taskType: 'likes',
        platform: milestoneSource.platform,
        file,
        postUrl: milestoneSource.post_url ?? '',
        sourceSubmissionId: milestoneSource.id,
        likesCount: Number(likesCount),
      })
      showToast('点赞核验已提交', 'success')
      setMilestoneSource(null)
      setLikesCount('')
      resetFile()
      await refresh()
    } catch (error) {
      showToast(error instanceof Error ? error.message : '提交失败', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppPageShell className="app-atmosphere">
      <div className="relative z-10 flex h-full flex-col bg-transparent">
        <div style={{ height: 'var(--safe-top)' }} />
        <AppPageContent className="flex h-[58px] shrink-0 items-center justify-between px-4 sm:px-5">
          <div>
            <p className="text-[11px] font-semibold text-[var(--color-primary-600)]">福利中心 · 重点活动</p>
            <h1 className="text-[23px] font-bold text-[var(--color-ink)]">安利与创作福利</h1>
          </div>
          <div className="border-l-2 border-[var(--color-primary-400)] pl-2 text-right">
            <strong className="block text-[15px] text-[var(--color-ink)]">{data?.today_remaining ?? '--'}/5</strong>
            <span className="text-[10px] text-[var(--color-text-muted)]">今日剩余</span>
          </div>
        </AppPageContent>

        <AppPageContent className="min-h-0 flex-1 overflow-y-auto px-4 pb-[116px] pt-3 sm:px-5">
          <section className="border-y border-[var(--color-divider)] py-5">
            <div className="border-l-4 border-[var(--color-primary-500)] pl-4">
              <p className="text-[11px] font-bold text-[var(--color-primary-600)]">YUOYUO CREATOR CLUB</p>
              <h2 className="mt-1 text-[22px] font-bold leading-[1.35] text-[var(--color-ink)]">分享真实体验，奖励累计发放</h2>
              <p className="mt-2 text-[12px] leading-relaxed text-[var(--color-text-secondary)]">每日安利、原创作品和点赞里程碑独立核验，通过后自动到账。</p>
            </div>
            <div className="mt-5 grid grid-cols-3 divide-x divide-[var(--color-divider)] text-center">
              <RewardMetric value="+20 币" label="每日安利" />
              <RewardMetric value="+100 币" label="原创通过" />
              <RewardMetric value="2 档 VIP" label="累计领取" />
            </div>
          </section>

          <section className="mt-5 rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] p-4 shadow-[var(--shadow-soft)]">
            <div className="grid grid-cols-2 rounded-[8px] bg-[var(--color-page-soft)] p-1" role="tablist">
              <TaskTab active={mode === 'ambassador'} onClick={() => changeMode('ambassador')}>每日安利 · 20 币</TaskTab>
              <TaskTab active={mode === 'creator'} onClick={() => changeMode('creator')}>原创作品 · 100 币</TaskTab>
            </div>

            {mode === 'ambassador' ? <AmbassadorGuide /> : <CreatorGuide />}

            <div className="mt-6 border-t border-[var(--color-divider)] pt-5">
              <p className="mb-2 text-[12px] font-semibold text-[var(--color-ink)]">发布平台</p>
              <div className="grid grid-cols-2 overflow-hidden rounded-[8px] border border-[var(--color-divider)]">
                {(Object.keys(PLATFORM_LABELS) as Array<keyof typeof PLATFORM_LABELS>).map((key) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setPlatform(key)}
                    className={`h-10 text-[13px] font-semibold transition first:border-r first:border-[var(--color-divider)] ${platform === key ? 'bg-[var(--color-primary-100)] text-[var(--color-primary-700)]' : 'bg-transparent text-[var(--color-text-secondary)]'}`}
                  >
                    {PLATFORM_LABELS[key]}
                  </button>
                ))}
              </div>
            </div>

            {mode === 'ambassador' ? (
              <div className="mt-5 border-t border-[var(--color-divider)] pt-5">
                <p className="text-[11px] font-bold text-[var(--color-primary-600)]">提交材料</p>
                <h3 className="mt-1 text-[15px] font-semibold text-[var(--color-ink)]">上传 1 张完整安利截图</h3>
                <p className="mt-1 text-[12px] leading-relaxed text-[var(--color-text-muted)]">截图中需同时看清发布平台、安利内容和 yuoyuo 关键词。</p>
                <ScreenshotUpload key={`ambassador-${fileInputVersion}`} file={file} onFile={selectFile} title="上传安利截图" required />
              </div>
            ) : (
              <div className="mt-5 border-t border-[var(--color-divider)] pt-5">
                <p className="text-[11px] font-bold text-[var(--color-primary-600)]">提交材料</p>
                <h3 className="mt-1 text-[15px] font-semibold text-[var(--color-ink)]">粘贴公开作品链接</h3>
                <p className="mt-1 text-[12px] leading-relaxed text-[var(--color-text-muted)]">审核人员会复制链接打开作品，请确认链接有效且无需关注即可查看。</p>
                <input
                  value={postUrl}
                  onChange={(event) => setPostUrl(event.target.value)}
                  placeholder="粘贴抖音或小红书作品链接"
                  className="mt-4 h-[46px] w-full rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-soft)]/45 px-3 text-[14px] text-[var(--color-ink)] outline-none placeholder:text-[var(--color-text-placeholder)] focus:border-[var(--color-primary-400)]"
                />
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="作品标题（可选）"
                  className="mt-2 h-[46px] w-full rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-soft)]/45 px-3 text-[14px] text-[var(--color-ink)] outline-none placeholder:text-[var(--color-text-placeholder)] focus:border-[var(--color-primary-400)]"
                />
                <ScreenshotUpload key={`creator-${fileInputVersion}`} file={file} onFile={selectFile} title="上传作品截图（可选）" />
                <p className="mt-5 text-[11px] font-bold text-[var(--color-primary-600)]">作品通过后可继续领取</p>
                <div className="mt-2 divide-y divide-[var(--color-divider)] border-y border-[var(--color-divider)]">
                  <MilestoneRow value="300 赞" reward="额外领取 29 元档 VIP" />
                  <MilestoneRow value="1000 赞" reward="再领取 69 元档 VIP 30 天" />
                </div>
                <p className="mt-3 text-[11px] leading-relaxed text-[var(--color-text-muted)]">作品审核通过后，在“我的提交”找到该作品并提交最新点赞数与截图。两档奖励累计发放。</p>
              </div>
            )}

            <button
              disabled={busy || loading}
              onClick={() => void submit()}
              className="mt-5 h-[48px] w-full rounded-[8px] bg-[var(--color-primary-500)] text-[15px] font-semibold text-white shadow-[var(--shadow-btn)] disabled:opacity-50"
            >
              {busy ? '提交中…' : '提交审核'}
            </button>
          </section>

          {milestoneSource && (
            <section className="mt-5 rounded-[8px] border border-[var(--color-primary-300)] bg-[var(--color-page-surface)] p-4 shadow-[var(--shadow-soft)]">
              <h2 className="text-[16px] font-semibold text-[var(--color-ink)]">提交点赞里程碑核验</h2>
              <p className="mt-1 truncate text-[12px] text-[var(--color-text-muted)]">{milestoneSource.title || milestoneSource.post_url}</p>
              <input
                inputMode="numeric"
                value={likesCount}
                onChange={(event) => setLikesCount(event.target.value.replace(/\D/g, ''))}
                placeholder="当前点赞数"
                className="mt-4 h-[46px] w-full rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-soft)]/45 px-3 text-[14px] text-[var(--color-ink)] outline-none placeholder:text-[var(--color-text-placeholder)] focus:border-[var(--color-primary-400)]"
              />
              <ScreenshotUpload key={`milestone-${fileInputVersion}`} file={file} onFile={selectFile} title="上传最新点赞截图" required />
              <div className="mt-4 grid grid-cols-2 gap-2">
                <button type="button" onClick={() => { setMilestoneSource(null); resetFile() }} className="h-[44px] rounded-[8px] bg-[var(--color-page-soft)] text-[13px] text-[var(--color-ink)]">取消</button>
                <button type="button" disabled={busy} onClick={() => void submitLikes()} className="h-[44px] rounded-[8px] bg-[var(--color-primary-500)] text-[13px] font-semibold text-white disabled:opacity-50">提交核验</button>
              </div>
            </section>
          )}

          <section className="mt-6">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-semibold text-[var(--color-ink)]">我的提交</h2>
              <button type="button" onClick={() => void refresh()} className="text-[12px] font-semibold text-[var(--color-primary-600)]">刷新</button>
            </div>
            <div className="mt-2 divide-y divide-[var(--color-divider)] border-y border-[var(--color-divider)]">
              {(data?.submissions ?? []).map((item) => (
                <SubmissionRow
                  key={item.id}
                  item={item}
                  onMilestone={() => {
                    setMilestoneSource(item)
                    setLikesCount('')
                    resetFile()
                  }}
                />
              ))}
              {!data?.submissions.length && <p className="py-8 text-center text-[13px] text-[var(--color-text-muted)]">还没有提交记录</p>}
            </div>
          </section>

          <section className="mt-6 border-t border-[var(--color-divider)] pt-4">
            <div className="flex items-center justify-between">
              <h2 className="text-[14px] font-semibold text-[var(--color-ink)]">更多福利</h2>
              <span className="text-[11px] text-[var(--color-text-muted)]">邀请、抽奖与佣金</span>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {([['invite', '邀请'], ['lottery', '抽奖'], ['commission', '佣金']] as const).map(([key, label]) => (
                <button key={key} type="button" onClick={() => navigate(`/rewards?view=${key}`)} className="h-[42px] rounded-[8px] border border-[var(--color-divider)] bg-[var(--color-page-surface)] text-[13px] text-[var(--color-ink)]">{label}</button>
              ))}
            </div>
          </section>
        </AppPageContent>
        <TabBar />
      </div>
    </AppPageShell>
  )
}

function AmbassadorGuide() {
  return (
    <div className="mt-5">
      <RewardSummary eyebrow="每日安利任务" value="+20 币" description="每条有效安利审核通过后自动到账" />
      <GuideHeading title="怎么完成" />
      <div className="mt-1 divide-y divide-[var(--color-divider)]">
        <GuideStep number="01" title="发布真实安利">
          在抖音或小红书分享你使用 yuoyuo 的真实体验，可发布评论、图文或动态，内容中需明确出现“yuoyuo”。
        </GuideStep>
        <GuideStep number="02" title="保留完整截图">
          截图需看清发布平台、完整安利内容和 yuoyuo 关键词。请勿裁掉关键信息，也不要提交他人的内容。
        </GuideStep>
        <GuideStep number="03" title="上传并等待审核">
          回到本页选择对应平台并上传截图。审核通过后，20 币自动发放到余额。
        </GuideStep>
      </div>
      <RuleNote lines={[
        '抖音与小红书合计每日最多提交 5 次',
        '重复截图、无关内容或无法辨认的截图不发奖',
        '每次安利请使用自然、真实且不同的表达',
      ]} />
    </div>
  )
}

function CreatorGuide() {
  return (
    <div className="mt-5">
      <RewardSummary eyebrow="原创作品任务" value="+100 币" description="每篇有效原创作品审核通过后自动到账" />
      <GuideHeading title="发布要求" />
      <div className="mt-1 divide-y divide-[var(--color-divider)]">
        <GuideStep number="01" title="创作公开作品">
          在抖音或小红书发布原创图文或视频，正文、话题或画面中需明确出现“yuoyuo”。
        </GuideStep>
        <GuideStep number="02" title="分享真实使用体验">
          内容需围绕 yuoyuo 展开，例如角色互动、聊天记录、好用的人设指令、功能体验或创意玩法。
        </GuideStep>
        <GuideStep number="03" title="复制链接回来提交">
          作品发布后复制公开链接，在下方粘贴并提交审核；作品截图可一并上传，便于快速核验。
        </GuideStep>
      </div>
      <div className="mt-4 border-y border-[var(--color-divider)] py-3">
        <p className="text-[12px] font-semibold text-[var(--color-ink)]">推荐选题</p>
        <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1.5 text-[11px] leading-relaxed text-[var(--color-text-secondary)]">
          <span>角色聊天实录</span><span>·</span><span>原创人设分享</span><span>·</span>
          <span>功能体验</span><span>·</span><span>创意玩法</span><span>·</span><span>使用心得</span>
        </div>
      </div>
      <RuleNote lines={[
        '作品需保持公开，至少到审核完成后再调整可见范围',
        '同一作品只能领取 1 次原创奖励，请勿重复提交',
        '搬运、抄袭或与 yuoyuo 无关的内容不发奖',
      ]} />
    </div>
  )
}

function RewardSummary({ eyebrow, value, description }: { eyebrow: string; value: string; description: string }) {
  return (
    <div className="border-l-4 border-[var(--color-primary-500)] bg-[var(--color-primary-50)]/45 px-4 py-3.5">
      <p className="text-[11px] font-semibold text-[var(--color-text-secondary)]">{eyebrow}</p>
      <div className="mt-1 flex items-baseline justify-between gap-3">
        <strong className="shrink-0 text-[25px] font-bold text-[var(--color-primary-600)]">{value}</strong>
        <span className="text-right text-[11px] leading-relaxed text-[var(--color-text-secondary)]">{description}</span>
      </div>
    </div>
  )
}

function GuideHeading({ title }: { title: string }) {
  return (
    <div className="mt-5 flex items-center gap-2">
      <span className="h-4 w-[3px] bg-[var(--color-primary-500)]" aria-hidden="true" />
      <h3 className="text-[15px] font-semibold text-[var(--color-ink)]">{title}</h3>
    </div>
  )
}

function GuideStep({ number, title, children }: { number: string; title: string; children: string }) {
  return (
    <div className="grid grid-cols-[30px_minmax(0,1fr)] gap-2 py-3.5">
      <span className="pt-0.5 text-[11px] font-bold text-[var(--color-primary-600)]">{number}</span>
      <div>
        <h4 className="text-[14px] font-semibold text-[var(--color-ink)]">{title}</h4>
        <p className="mt-1 text-[12px] leading-[1.75] text-[var(--color-text-secondary)]">{children}</p>
      </div>
    </div>
  )
}

function RuleNote({ lines }: { lines: string[] }) {
  return (
    <div className="mt-3 border-l-2 border-[var(--color-secondary)] bg-[var(--color-page-soft)]/60 px-3 py-3">
      <p className="text-[12px] font-semibold text-[var(--color-ink)]">审核说明</p>
      <ul className="mt-1.5 space-y-1 text-[11px] leading-relaxed text-[var(--color-text-secondary)]">
        {lines.map((line) => <li key={line}>· {line}</li>)}
      </ul>
    </div>
  )
}

function TaskTab({ active, onClick, children }: { active: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`h-10 rounded-[6px] text-[13px] font-semibold transition ${active ? 'bg-[var(--color-page-surface)] text-[var(--color-ink)] shadow-[var(--shadow-soft)]' : 'text-[var(--color-text-muted)]'}`}
    >
      {children}
    </button>
  )
}

function RewardMetric({ value, label }: { value: string; label: string }) {
  return (
    <div className="px-1">
      <strong className="block text-[17px] font-bold text-[var(--color-ink)]">{value}</strong>
      <span className="mt-0.5 block text-[10px] text-[var(--color-text-muted)]">{label}</span>
    </div>
  )
}

function MilestoneRow({ value, reward }: { value: string; reward: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-3">
      <strong className="text-[14px] text-[var(--color-primary-600)]">{value}</strong>
      <span className="text-right text-[12px] text-[var(--color-text-secondary)]">{reward}</span>
    </div>
  )
}

function ScreenshotUpload({ file, onFile, title, required = false }: {
  file: File | null
  onFile: (file: File | null) => void
  title: string
  required?: boolean
}) {
  const inputId = useId()
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const nextUrl = URL.createObjectURL(file)
    setPreviewUrl(nextUrl)
    return () => URL.revokeObjectURL(nextUrl)
  }, [file])

  return (
    <label
      htmlFor={inputId}
      className="mt-3 flex min-h-[108px] cursor-pointer items-center gap-3 rounded-[8px] border border-dashed border-[var(--color-primary-300)] bg-[var(--color-primary-50)]/45 px-4 py-3 transition active:opacity-80"
    >
      <input
        id={inputId}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(event) => onFile(event.target.files?.[0] ?? null)}
        className="sr-only"
        required={required}
      />
      {previewUrl ? (
        <img src={previewUrl} alt="已选择的截图预览" className="h-[76px] w-[76px] shrink-0 rounded-[6px] object-cover" />
      ) : (
        <span className="flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-[8px] bg-[var(--color-page-surface)] text-[var(--color-primary-600)] shadow-[var(--shadow-soft)]" aria-hidden="true">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 14v5h14v-5"/></svg>
        </span>
      )}
      <span className="min-w-0 flex-1">
        <strong className="block text-[14px] text-[var(--color-ink)]">{file ? '截图已选择' : title}{required && !file ? ' *' : ''}</strong>
        <span className="mt-1 block truncate text-[11px] text-[var(--color-text-secondary)]">{file ? file.name : '点击选择手机相册或本地截图'}</span>
        <span className="mt-1 block text-[10px] text-[var(--color-text-muted)]">JPG、PNG、WebP，最大 8MB{file ? ' · 点击可更换' : ''}</span>
      </span>
    </label>
  )
}

function SubmissionRow({ item, onMilestone }: { item: PromotionSubmission; onMilestone: () => void }) {
  const task = item.task_type === 'ambassador' ? '安利截图' : item.task_type === 'creator' ? '原创作品' : '点赞核验'
  const status = { pending: '审核中', approved: '已通过', needs_info: '待补充', rejected: '未通过' }[item.status]
  return (
    <div className="flex items-center justify-between gap-3 py-3">
      <div className="min-w-0">
        <p className="truncate text-[14px] text-[var(--color-ink)]">{task} · {PLATFORM_LABELS[item.platform]}</p>
        <p className="mt-1 text-[11px] text-[var(--color-text-muted)]">{item.review_reason || (item.reward_coins ? `已发放 ${item.reward_coins} 币` : '等待人工审核')}</p>
        {item.task_type === 'creator' && item.status === 'approved' && !(item.milestone_300_granted && item.milestone_1000_granted) && (
          <button type="button" onClick={onMilestone} className="mt-2 text-[12px] font-semibold text-[var(--color-primary-600)]">提交最新点赞数</button>
        )}
      </div>
      <span className={`shrink-0 text-[12px] ${item.status === 'approved' ? 'text-[var(--color-success)]' : item.status === 'rejected' ? 'text-[var(--color-error)]' : 'text-[var(--color-text-secondary)]'}`}>{status}</span>
    </div>
  )
}
