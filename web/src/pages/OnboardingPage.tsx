import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'

const steps = [
  {
    image: '/assets/backgrounds/引导页1背景图.png',
    title: '我是 yuoyuo，会陪你聊心事。',
    description: '我会记得你说过的话，理解你的情绪。',
  },
  {
    image: '/assets/backgrounds/引导页2背景图.png',
    title: '你的对话只属于你。',
    description: '数据加密存储，端到端可审计。',
  },
  {
    image: '/assets/backgrounds/引导页3背景图.png',
    title: '在爱发电赞助即可解锁会员。',
    description: '支持微信 / 支付宝；赞助后获取兑换码，回到这里输入即可激活。',
  },
]

export function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(0)
  const navigate = useNavigate()
  const { setHasSeenOnboarding } = useAppStore()

  const isLast = currentStep === steps.length - 1

  const handleNext = () => {
    if (isLast) {
      setHasSeenOnboarding(true)
      navigate('/login', { replace: true })
    } else {
      setCurrentStep((s) => s + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep((s) => s - 1)
    }
  }

  const step = steps[currentStep]

  return (
    <div className="relative w-full h-full flex flex-col bg-[var(--color-surface)]">
      {/* Back button */}
      {currentStep > 0 && (
        <button
          onClick={handleBack}
          className="absolute top-[calc(var(--safe-top)+8px)] left-5 z-10 w-[44px] h-[44px] flex items-center justify-center"
        >
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
      )}

      {/* Safe area spacer */}
      <div style={{ height: 'var(--safe-top)' }} />

      {/* Illustration — larger, top-centered */}
      <div className="flex-1 flex items-center justify-center px-6 pt-4 pb-4">
        <img
          key={currentStep}
          src={step.image}
          alt={step.title}
          className="w-full max-w-[360px] max-h-[60%] object-contain animate-[fade-in-up_280ms_var(--ease-standard)]"
        />
      </div>

      {/* Bottom content */}
      <div className="px-6 pb-6" style={{ paddingBottom: 'calc(32px + var(--safe-bottom))' }}>
        <h2 className="text-[22px] font-semibold text-[var(--color-ink)] text-center mb-3 leading-[1.3]">
          {step.title}
        </h2>
        <p className="text-[15px] text-[var(--color-text-secondary)] text-center mb-6 leading-[1.6]">
          {step.description}
        </p>

        {/* Legal links on step 2 */}
        {currentStep === 1 && (
          <p className="text-center text-[12px] text-[var(--color-text-muted)] mb-4">
            <Link to="/legal/terms" className="underline">用户协议</Link>
            {' · '}
            <Link to="/legal/privacy" className="underline">隐私政策</Link>
          </p>
        )}

        {/* Page dots */}
        <div className="flex justify-center gap-2 mb-6">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`rounded-full transition-all duration-300 ${
                i === currentStep
                  ? 'w-6 h-2 bg-[var(--color-primary)]'
                  : 'w-2 h-2 bg-[var(--color-glass-55)]'
              }`}
            />
          ))}
        </div>

        {/* Primary button */}
        <button
          onClick={handleNext}
          className="w-full py-4 rounded-full bg-gradient-to-r from-[#FFB7C5] to-[#FF8FAB] text-white text-[17px] font-semibold shadow-[0_8px_24px_-4px_rgba(255,143,171,0.35)] active:scale-[0.97] transition-transform"
        >
          {isLast ? '开始体验' : '下一步'}
        </button>

        {/* Redeem link on last step */}
        {isLast && (
          <button
            onClick={() => {
              setHasSeenOnboarding(true)
              navigate('/redeem')
            }}
            className="w-full text-center text-[14px] text-[var(--color-ink)] py-3 mt-2 active:opacity-60"
          >
            我已有兑换码 →
          </button>
        )}
      </div>
    </div>
  )
}
