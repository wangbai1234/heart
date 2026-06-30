/**
 * web/src/preview/Home.tsx
 * Pixel-perfect reconstruction of 09_home.png
 * Source: web/design/source/phase2_screens/09_home.png
 */

import type { FC, ReactNode } from 'react'

/* ─── Inline SVG icons ──────────────────────────────────────────────────── */

function SignalIcon() {
  return (
    <svg width="17" height="12" viewBox="0 0 17 12" fill="none">
      <rect x="0"  y="8" width="3" height="4" rx="0.5" fill="#3A3A4A" opacity="0.85"/>
      <rect x="4"  y="5.5" width="3" height="6.5" rx="0.5" fill="#3A3A4A" opacity="0.85"/>
      <rect x="8"  y="3" width="3" height="9" rx="0.5" fill="#3A3A4A" opacity="0.85"/>
      <rect x="12" y="0" width="3" height="12" rx="0.5" fill="#3A3A4A" opacity="0.85"/>
    </svg>
  )
}

function WifiIcon() {
  return (
    <svg width="16" height="12" viewBox="0 0 16 12" fill="none">
      <path d="M8 9.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Z" fill="#3A3A4A" opacity="0.85"/>
      <path d="M4.1 7.1A5.4 5.4 0 0 1 8 5.5c1.5 0 2.9.6 3.9 1.6" stroke="#3A3A4A" strokeWidth="1.4" strokeLinecap="round" opacity="0.85"/>
      <path d="M1.3 4.3A9.1 9.1 0 0 1 8 2c2.5 0 4.8 1 6.7 2.3" stroke="#3A3A4A" strokeWidth="1.4" strokeLinecap="round" opacity="0.85"/>
    </svg>
  )
}

function BatteryIcon() {
  return (
    <svg width="25" height="12" viewBox="0 0 25 12" fill="none">
      <rect x="0.5" y="0.5" width="21" height="11" rx="3.5" stroke="#3A3A4A" strokeOpacity="0.35"/>
      <rect x="2" y="2" width="16" height="8" rx="2" fill="#3A3A4A" opacity="0.85"/>
      <path d="M22.5 4.5v3a1.5 1.5 0 0 0 0-3Z" fill="#3A3A4A" opacity="0.4"/>
    </svg>
  )
}

function GiftIcon({ color }: { color: string }) {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="9" width="20" height="13" rx="2" stroke={color} strokeWidth="1.6" strokeLinejoin="round"/>
      <path d="M2 9h20v4H2V9Z" stroke={color} strokeWidth="1.6" strokeLinejoin="round"/>
      <line x1="12" y1="9" x2="12" y2="22" stroke={color} strokeWidth="1.6" strokeLinecap="round"/>
      <path d="M12 9C12 9 9 7 9 5C9 3.3 10.3 2 12 2C13.7 2 15 3.3 15 5C15 7 12 9 12 9Z" stroke={color} strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M12 9C12 9 15 7 15 5C15 3.3 13.7 2 12 2C10.3 2 9 3.3 9 5C9 7 12 9 12 9Z" stroke={color} strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  )
}

function PersonIcon({ color }: { color: string }) {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" stroke={color} strokeWidth="1.7" strokeLinecap="round"/>
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke={color} strokeWidth="1.7" strokeLinecap="round"/>
    </svg>
  )
}

function GearIcon({ color }: { color: string }) {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="3" stroke={color} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
        stroke={color} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function HomeIconFilled() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H15v-6H9v6H4a1 1 0 0 1-1-1V9.5Z"
        fill="#FF6E8A" stroke="#FF6E8A" strokeWidth="0.5" strokeLinejoin="round"/>
    </svg>
  )
}

function ChatBubbleIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z"
        stroke="#9B9BAE" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function CharacterNavIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" stroke="#9B9BAE" strokeWidth="1.7"/>
      <path d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7" stroke="#9B9BAE" strokeWidth="1.7" strokeLinecap="round"/>
    </svg>
  )
}

function SettingsNavIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="3" stroke="#9B9BAE" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
        stroke="#9B9BAE" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

/* ─── Glass Heart ───────────────────────────────────────────────────────── */

function GlassHeart() {
  /* viewBox 0 0 108 110 — heart body ends ~y100, tiny tail down to y110 */
  return (
    <div
      style={{
        width: 150,
        height: 152,
        position: 'relative',
        filter: 'drop-shadow(0 10px 32px rgba(240, 80, 180, 0.60))',
      }}
    >
      <svg viewBox="0 0 108 110" width="150" height="152" xmlns="http://www.w3.org/2000/svg">
        <defs>
          {/* Horizontal gradient: hot-pink stays dominant through center, periwinkle on far right only */}
          <linearGradient id="hg-main" x1="0%" y1="45%" x2="100%" y2="55%">
            <stop offset="0%"   stopColor="#FF0E58" />
            <stop offset="30%"  stopColor="#FF4A9A" />
            <stop offset="55%"  stopColor="#E878E0" />
            <stop offset="76%"  stopColor="#9A98DC" />
            <stop offset="100%" stopColor="#8090C4" />
          </linearGradient>

          {/* Glass highlight — upper-left, large bright oval */}
          <radialGradient id="hg-hi" cx="34%" cy="22%" r="55%">
            <stop offset="0%"   stopColor="rgba(255,255,255,0.94)" />
            <stop offset="30%"  stopColor="rgba(255,255,255,0.44)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </radialGradient>

          {/* Depth shadow — gentle, keeps bottom lavender not dark-purple */}
          <radialGradient id="hg-depth" cx="50%" cy="88%" r="52%">
            <stop offset="0%"   stopColor="rgba(90, 50, 160, 0.20)" />
            <stop offset="100%" stopColor="rgba(90, 50, 160, 0)" />
          </radialGradient>

          {/* Outer glow — warm rose-pink */}
          <filter id="hg-glow" x="-32%" y="-32%" width="164%" height="164%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="7" result="blur"/>
            <feFlood floodColor="#FF4898" floodOpacity="0.60" result="fc"/>
            <feComposite in="fc" in2="blur" operator="in" result="glow"/>
            <feMerge><feMergeNode in="glow"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* Heart body + small speech-bubble tail at bottom */}
        <path
          d="M54 22
             C54 15, 43 5, 30 8
             C14 11, 4 25, 4 40
             C4 68, 30 84, 54 102
             C78 84, 104 68, 104 40
             C104 25, 94 11, 78 8
             C65 5, 54 15, 54 22 Z"
          fill="url(#hg-main)"
          filter="url(#hg-glow)"
        />

        {/* Glass highlight */}
        <path
          d="M54 22
             C54 15, 43 5, 30 8
             C14 11, 4 25, 4 40
             C4 68, 30 84, 54 102
             C78 84, 104 68, 104 40
             C104 25, 94 11, 78 8
             C65 5, 54 15, 54 22 Z"
          fill="url(#hg-hi)"
        />

        {/* Depth shadow */}
        <path
          d="M54 22
             C54 15, 43 5, 30 8
             C14 11, 4 25, 4 40
             C4 68, 30 84, 54 102
             C78 84, 104 68, 104 40
             C104 25, 94 11, 78 8
             C65 5, 54 15, 54 22 Z"
          fill="url(#hg-depth)"
        />

        {/* Colored border */}
        <path
          d="M54 22
             C54 15, 43 5, 30 8
             C14 11, 4 25, 4 40
             C4 68, 30 84, 54 102
             C78 84, 104 68, 104 40
             C104 25, 94 11, 78 8
             C65 5, 54 15, 54 22 Z"
          fill="none"
          stroke="rgba(200, 160, 245, 0.5)"
          strokeWidth="1.0"
        />

        {/* Speech-bubble tail — tiny downward point below heart */}
        <path
          d="M49 100 L54 110 L59 100"
          fill="url(#hg-main)"
          stroke="rgba(200, 160, 245, 0.4)"
          strokeWidth="0.8"
          strokeLinejoin="round"
        />

        {/* Primary glint — large bright oval, upper-left lobe */}
        <ellipse
          cx="36" cy="30"
          rx="14" ry="8"
          fill="rgba(255,255,255,0.82)"
          transform="rotate(-24 36 30)"
        />

        {/* Secondary glint — right lobe */}
        <ellipse
          cx="74" cy="25"
          rx="6.5" ry="3.8"
          fill="rgba(255,255,255,0.55)"
          transform="rotate(-14 74 25)"
        />

        {/* Tiny tertiary glint — bottom of left lobe */}
        <ellipse
          cx="24" cy="60"
          rx="5" ry="2.5"
          fill="rgba(255,255,255,0.28)"
          transform="rotate(-8 24 60)"
        />

        {/* Inner rim highlight arc */}
        <path
          d="M54 22 C54 15, 43 5, 30 8 C18 11, 7 20, 5 33"
          fill="none"
          stroke="rgba(255,255,255,0.50)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>
    </div>
  )
}

/* ─── Hero Card Sky Background ──────────────────────────────────────────── */

function HeroSky({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `
          radial-gradient(ellipse 110px 88px at 50% 20%, rgba(255,255,255,0.96) 0%, rgba(255,248,220,0.55) 35%, transparent 62%),
          radial-gradient(ellipse 230px 175px at 96% 14%, rgba(255,195,95,0.92) 0%, rgba(255,175,80,0.55) 38%, transparent 62%),
          radial-gradient(ellipse 185px 140px at 6%  40%, rgba(195,170,255,0.68) 0%, transparent 56%),
          radial-gradient(ellipse 150px 110px at 92% 62%, rgba(255,175,200,0.58) 0%, transparent 50%),
          radial-gradient(ellipse 125px 95px at 18%  80%, rgba(205,185,255,0.45) 0%, transparent 56%),
          radial-gradient(ellipse 105px 75px at 72%  76%, rgba(255,165,210,0.42) 0%, transparent 50%),
          linear-gradient(
            158deg,
            #6A5EA8 0%,
            #8070BC 8%,
            #9882C0 18%,
            #B498C2 30%,
            #D0B0AA 44%,
            #E4BCA8 56%,
            #E8B2B8 70%,
            #DEA6BE 85%,
            #D292B4 100%
          )
        `,
      }}
    >
      {children}
    </div>
  )
}

/* ─── Avatar ────────────────────────────────────────────────────────────── */

interface AvatarProps {
  gradient: string
  size: number
  ring?: string
}

function Avatar({ gradient, size, ring }: AvatarProps) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: gradient,
        flexShrink: 0,
        ...(ring ? {
          boxShadow: `0 0 0 2.5px ${ring}`,
        } : {}),
      }}
    />
  )
}

/* ─── Quick Action Card ─────────────────────────────────────────────────── */

interface ActionCardProps {
  icon: ReactNode
  label: string
}

function ActionCard({ icon, label }: ActionCardProps) {
  return (
    <div
      style={{
        flex: 1,
        backgroundColor: 'rgba(255,255,255,0.92)',
        borderRadius: 20,
        boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        paddingTop: 14,
        paddingBottom: 14,
        gap: 7,
      }}
    >
      {icon}
      <span
        style={{
          fontSize: 13,
          color: '#3A3A4A',
          fontWeight: 400,
          letterSpacing: '0.01em',
        }}
      >
        {label}
      </span>
    </div>
  )
}

/* ─── Chat List Item ─────────────────────────────────────────────────────── */

interface ChatListItemProps {
  avatarGradient: string
  avatarRing?: string
  name: string
  preview: string
  time: string
  unread?: boolean
}

function ChatListItem({ avatarGradient, avatarRing, name, preview, time, unread }: ChatListItemProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        paddingTop: 14,
        paddingBottom: 14,
        borderBottom: '1px solid rgba(0,0,0,0.04)',
      }}
    >
      <Avatar gradient={avatarGradient} size={56} ring={avatarRing ?? '#E0C0D8'} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 16, fontWeight: 600, color: '#2A2A3A' }}>{name}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, color: '#9B9BAE' }}>{time}</span>
            {unread && (
              <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#FF6E8A', flexShrink: 0 }} />
            )}
          </div>
        </div>
        <p
          style={{
            fontSize: 14,
            color: '#9B9BAE',
            lineHeight: 1.5,
            margin: 0,
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical' as const,
            whiteSpace: 'pre-line',
          }}
        >
          {preview}
        </p>
      </div>
    </div>
  )
}

/* ─── Bottom Nav Tab ────────────────────────────────────────────────────── */

interface NavTabProps {
  icon: ReactNode
  label: string
  active?: boolean
}

function NavTab({ icon, label, active }: NavTabProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 3,
        flex: 1,
        paddingTop: 8,
        paddingBottom: 2,
        position: 'relative',
      }}
    >
      {icon}
      <span
        style={{
          fontSize: 10,
          fontWeight: active ? 600 : 400,
          color: active ? '#FF6E8A' : '#9B9BAE',
          letterSpacing: '0.01em',
        }}
      >
        {label}
      </span>
      {active && (
        <div
          style={{
            width: 4,
            height: 4,
            borderRadius: '50%',
            backgroundColor: '#FF6E8A',
            marginTop: 1,
          }}
        />
      )}
    </div>
  )
}

/* ─── Home Page ─────────────────────────────────────────────────────────── */

export const Home: FC = () => {
  return (
    /* Outer: full viewport, flex-column so nav is always pinned to bottom */
    <div
      style={{
        width: '100%',
        height: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#FFE8EC',
        fontFamily: '"PingFang SC", "HarmonyOS Sans SC", -apple-system, system-ui, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale' as const,
        overflow: 'hidden',
      }}
    >
    {/* Scrollable content area — grows to fill all space above nav */}
    <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
      {/* ── Status Bar ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingLeft: 20,
          paddingRight: 20,
          paddingTop: 14,
          paddingBottom: 6,
        }}
      >
        <span style={{ fontSize: 15, fontWeight: 600, color: '#2A2A3A', letterSpacing: '-0.01em' }}>
          9:41
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <SignalIcon />
          <WifiIcon />
          <BatteryIcon />
        </div>
      </div>

      {/* ── Top Bar ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingLeft: 20,
          paddingRight: 20,
          paddingTop: 4,
          paddingBottom: 12,
        }}
      >
        <h1
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: '#2A2A3A',
            letterSpacing: '0.02em',
            margin: 0,
            fontFamily: '"SF Pro Rounded", -apple-system, system-ui, sans-serif',
          }}
        >
          yuoyuo
        </h1>
        <Avatar
          gradient="radial-gradient(circle at 38% 38%, #C0B0DC, #7060A8)"
          size={40}
          ring="rgba(255,180,210,0.6)"
        />
      </div>

      {/* ── Hero Card ── */}
      <div
        style={{
          marginLeft: 16,
          marginRight: 16,
          borderRadius: 24,
          overflow: 'hidden',
          position: 'relative',
          height: 296,
          boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
        }}
      >
        {/* Sky background */}
        <HeroSky>
          {/* Bottom frosted overlay for text readability */}
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: '58%',
              background: 'linear-gradient(to top, rgba(252,238,245,0.94) 0%, rgba(252,235,244,0.72) 32%, rgba(252,232,242,0.38) 62%, transparent 100%)',
              backdropFilter: 'blur(1.5px)',
              WebkitBackdropFilter: 'blur(1.5px)',
            }}
          />
        </HeroSky>

        {/* Heart orb — centered in upper portion */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <div style={{ marginTop: 16 }}>
            <GlassHeart />
          </div>

          {/* Companion info */}
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              paddingLeft: 20,
              paddingRight: 20,
              paddingBottom: 18,
            }}
          >
            <h2
              style={{
                fontSize: 22,
                fontWeight: 600,
                color: '#2A2A3A',
                margin: 0,
                marginBottom: 4,
                textAlign: 'center',
              }}
            >
              神无月凛
            </h2>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <p
                style={{
                  fontSize: 13,
                  color: '#7A7A8E',
                  margin: 0,
                  letterSpacing: '0.01em',
                }}
              >
                刚刚和你聊过 · 心情：温柔
              </p>
              {/* Start chat button */}
              <button
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  paddingLeft: 16,
                  paddingRight: 16,
                  paddingTop: 9,
                  paddingBottom: 9,
                  borderRadius: 999,
                  border: '1.5px solid rgba(255,130,160,0.55)',
                  backgroundColor: 'rgba(255,255,255,0.72)',
                  color: '#FF5A80',
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: 'pointer',
                  backdropFilter: 'blur(8px)',
                  WebkitBackdropFilter: 'blur(8px)',
                  letterSpacing: '0.01em',
                  whiteSpace: 'nowrap',
                  boxShadow: '0 2px 8px rgba(255,100,140,0.15)',
                }}
              >
                开始聊天 →
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Quick Actions ── */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          marginLeft: 16,
          marginRight: 16,
          marginTop: 14,
        }}
      >
        <ActionCard
          icon={<GiftIcon color="#FF8A9A" />}
          label="兑换会员"
        />
        <ActionCard
          icon={<PersonIcon color="#9B8FD9" />}
          label="切换角色"
        />
        <ActionCard
          icon={<GearIcon color="#6B9FD9" />}
          label="设置"
        />
      </div>

      {/* ── Recent Section ── */}
      <div
        style={{
          marginLeft: 16,
          marginRight: 16,
          marginTop: 20,
        }}
      >
        {/* Section header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 4,
          }}
        >
          <h3
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: '#2A2A3A',
              margin: 0,
              letterSpacing: '0.01em',
            }}
          >
            最近的……
          </h3>
          <span
            style={{
              fontSize: 13,
              color: '#9B9BAE',
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            查看全部
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M5 3l4 4-4 4" stroke="#9B9BAE" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </span>
        </div>

        {/* Chat list */}
        <ChatListItem
          avatarGradient="radial-gradient(circle at 38% 32%, #9880C8, #4A3080)"
          avatarRing="#B8A0D8"
          name="神无月凛"
          preview={"今天过得怎么样呀？\n有没有遇到什么开心的事~"}
          time="22:18"
          unread
        />
        <ChatListItem
          avatarGradient="radial-gradient(circle at 40% 35%, #D4B8E8, #9070B8)"
          avatarRing="#C8A8DC"
          name="桃乐丝"
          preview={"晚安呀，记得多喝水，明天见~\n我会在这里等你哦。"}
          time="昨天"
          unread
        />
      </div>

      {/* Bottom padding so last item isn't flush against nav */}
      <div style={{ height: 8 }} />
    </div>{/* end scrollable area */}

      {/* ── Bottom Navigation Bar — natural flow, always at bottom of flex ── */}
      <div
        style={{
          flexShrink: 0,
          backgroundColor: 'rgba(255,255,255,0.97)',
          borderTop: '1px solid rgba(0,0,0,0.07)',
          display: 'flex',
          alignItems: 'flex-start',
          paddingBottom: 20,
        }}
      >
        <NavTab icon={<HomeIconFilled />}   label="首页" active />
        <NavTab icon={<ChatBubbleIcon />}   label="聊天" />
        <NavTab icon={<CharacterNavIcon />} label="角色" />
        <NavTab icon={<SettingsNavIcon />}  label="设置" />
      </div>
    </div>
  )
}
