import { useRef, useState, type TouchEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'

const steps = [
  {
    image: '/assets/backgrounds/引导页1背景图_ext.png',
    title: '我是yuoyuo，\n独属于你的虚拟宇宙。',
    description: '我会记得你说过的话，理解你的情绪。',
    objectPosition: 'center 12%',
  },
  {
    image: '/assets/backgrounds/引导页2背景图_ext.png',
    title: '你的对话只属于你。',
    description: '数据加密存储，注销即记忆全部消散。',
    objectPosition: 'center 10%',
  },
  {
    image: '/assets/backgrounds/引导页3背景图_ext.png',
    title: '在爱发电赞助即可解锁会员。',
    description: '支持微信/支付宝；赞助后领取兑换码，回到这里输入即可激活。',
    objectPosition: 'center 14%',
  },
] as const

const SWIPE_THRESHOLD = 42

export function OnboardingPage() {
  const navigate = useNavigate()
  const { setHasSeenOnboarding } = useAppStore()
  const [currentStep, setCurrentStep] = useState(0)
  const touchStartX = useRef<number | null>(null)
  const touchStartY = useRef<number | null>(null)

  const isLast = currentStep === steps.length - 1

  const finishOnboarding = () => {
    setHasSeenOnboarding(true)
    navigate('/login', { replace: true })
  }

  const handleNext = () => {
    if (isLast) {
      finishOnboarding()
      return
    }
    setCurrentStep((step) => Math.min(step + 1, steps.length - 1))
  }

  const handleTouchStart = (event: TouchEvent<HTMLDivElement>) => {
    const touch = event.touches[0]
    touchStartX.current = touch.clientX
    touchStartY.current = touch.clientY
  }

  const handleTouchEnd = (event: TouchEvent<HTMLDivElement>) => {
    if (touchStartX.current == null || touchStartY.current == null) return

    const touch = event.changedTouches[0]
    const deltaX = touch.clientX - touchStartX.current
    const deltaY = touch.clientY - touchStartY.current

    touchStartX.current = null
    touchStartY.current = null

    if (Math.abs(deltaX) < SWIPE_THRESHOLD || Math.abs(deltaX) < Math.abs(deltaY)) return

    if (deltaX < 0) {
      setCurrentStep((step) => Math.min(step + 1, steps.length - 1))
      return
    }

    setCurrentStep((step) => Math.max(step - 1, 0))
  }

  return (
    <div className="relative isolate h-full overflow-hidden bg-[#FFF9F5]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,202,218,0.58),transparent_34%),radial-gradient(circle_at_bottom,rgba(255,234,228,0.92),transparent_46%),linear-gradient(180deg,#FFF9F6_0%,#FFFDFC_46%,#FFF9F7_100%)]" />
      <div className="absolute left-1/2 top-[8%] h-[220px] w-[220px] -translate-x-1/2 rounded-full bg-[rgba(255,183,197,0.22)] blur-[72px]" />
      <div className="absolute bottom-[18%] left-1/2 h-[280px] w-[280px] -translate-x-1/2 rounded-full bg-[rgba(255,232,221,0.9)] blur-[96px]" />

      <div
        className="relative z-10 flex h-full flex-col"
        style={{ paddingTop: 'var(--safe-top)' }}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <div className="relative flex-1 overflow-hidden">
          <div
            className="flex h-full transition-transform duration-500 ease-out"
            style={{
              width: `${steps.length * 100}%`,
              transform: `translateX(-${currentStep * (100 / steps.length)}%)`,
            }}
          >
            {steps.map((step) => (
              <section
                key={step.image}
                className="relative flex h-full shrink-0 flex-col"
                style={{ width: `${100 / steps.length}%` }}
              >
                <div className="relative h-[52vh] min-h-[380px] w-full overflow-hidden">
                  <img
                    src={step.image}
                    alt={step.title}
                    className="absolute inset-0 h-full w-full object-cover"
                    style={{
                      objectPosition: step.objectPosition,
                    }}
                  />
                  <div className="absolute inset-y-0 left-0 w-[9%] bg-gradient-to-r from-[#FFF9F6] via-[rgba(255,249,246,0.45)] to-transparent" />
                  <div className="absolute inset-y-0 right-0 w-[9%] bg-gradient-to-l from-[#FFF9F6] via-[rgba(255,249,246,0.45)] to-transparent" />
                  <div className="absolute inset-x-0 top-0 h-[12%] bg-gradient-to-b from-[rgba(255,249,245,0.38)] via-[rgba(255,249,245,0.16)] to-transparent" />
                  <div className="absolute inset-x-0 bottom-0 h-[56%] bg-gradient-to-b from-transparent via-[rgba(255,250,247,0.92)] to-[#FFF9F6]" />
                </div>

                <div className="relative mt-12 px-6 text-center">
                  <h1 className="whitespace-pre-line text-[20px] font-semibold leading-[1.38] tracking-[-0.03em] text-[#2E3348]">
                    {step.title}
                  </h1>
                  <p className="mx-auto mt-4 max-w-[286px] text-[14px] leading-[1.72] tracking-[-0.01em] text-[rgba(61,69,96,0.62)]">
                    {step.description}
                  </p>
                </div>
              </section>
            ))}
          </div>
        </div>

        <div
          className="relative z-20 px-4"
          style={{ paddingBottom: 'calc(4px + var(--safe-bottom))', marginTop: '-10px' }}
        >
          <div className="mb-2.5 flex justify-center gap-3">
            {steps.map((_, index) => (
              <span
                key={index}
                className={`h-[10px] rounded-full transition-all duration-300 ${
                  currentStep === index
                    ? 'w-[10px] bg-[#FF84A7] shadow-[0_4px_10px_rgba(255,132,167,0.28)]'
                    : 'w-[10px] bg-[rgba(255,194,206,0.55)]'
                }`}
              />
            ))}
          </div>

          <button
            onClick={handleNext}
            className={`h-[58px] w-full rounded-full text-[17px] font-medium tracking-[-0.02em] transition-transform active:scale-[0.985] ${
              isLast
                ? 'bg-gradient-to-r from-[#FF8FB0] to-[#FFB3B9] text-white shadow-[0_16px_30px_rgba(255,143,171,0.24)]'
                : 'border border-[rgba(255,168,188,0.68)] bg-[rgba(255,255,255,0.82)] text-[#FF91AD] shadow-[0_10px_26px_rgba(255,214,225,0.28)]'
            }`}
          >
            {isLast ? '开始体验' : '下一步'}
          </button>

          {isLast && (
            <button
              onClick={() => {
                setHasSeenOnboarding(true)
                navigate('/redeem')
              }}
              className="mt-4 w-full text-center text-[14px] font-medium text-[#FF89A7] transition-opacity active:opacity-70"
            >
              我有兑换码 →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
