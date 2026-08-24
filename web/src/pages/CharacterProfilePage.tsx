import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import type { CharacterProfileDTO } from '../services/api'
import { useCharactersStore } from '../stores/charactersStore'
import { useCompanionsStore } from '../stores/companionsStore'
import { useAppStore } from '../stores/appStore'
import { useFavoritesStore } from '../stores/favoritesStore'
import { useToastStore } from '../stores/toastStore'
import { DEFAULT_COVER } from '../data/uiContent'
import { stageWithIntimacy, isColdWar, intimacyPercent, stageLabel, stageOrderIndex } from '../utils/relationship'
import { buildShareLink } from '../utils/characterShare'
import { useSafeBack } from '../hooks/useSafeBack'
import { CHARACTER_UI_CONFIGS, type CharacterTheme } from '../data/characterUIConfig'
import { JiYuProfile, LiShenProfile, ChengXuProfile, LilithProfile, GuBeichenProfile, QinXiaoProfile, JiangYuezeProfile, JiangYeProfile, GuXingzhouProfile, LiJueProfile, ShenYichenProfile, ShenYuchuanProfile, LuoFeiProfile, PeiTinglanProfile, FuMingxiuProfile, XizeProfile, JiangLiProfile, PeiJueProfile, HuoChengProfile, ZhouJinProfile, BaiQinghuanProfile, ChengZhiProfile, LuTingshengProfile, GuNanqiaoProfile, YunZhiProfile, SuWanProfile, LinXiaomanProfile, LuZhaoProfile, SuYueyaoProfile, HuoShiyuProfile, SuNianProfile, SuYunProfile, GuQingwanProfile, GuXingmianProfile, SongYeProfile, VitoRosettiProfile, XieCiProfile, ShenLiaoProfile, LuWenjingProfile, JiangRanProfile, GuYanliProfile, XuZhihanProfile, LinyuanManorProfile, FreeMuseProfile, QingyuBandProfile, GuiBaiProfile, YinCiProfile, HeZhuoProfile, WenYiningProfile, WeiHengProfile, QiFeiProfile, ShiyanProfile, ChuRanProfile, HeLinchuanProfile, WenYanqingProfile, CenLiProfile, XieTingyunProfile, XuQichiProfile, XieMingluanProfile, QiWangProfile, YanWujiuProfile, LiYaoProfile, TangJingzhouProfile, PeiZhaoyeProfile } from '../components/characterProfiles'
import type { ComponentType } from 'react'
import { BlockRenderer } from '../components/profileBlocks/BlockRenderer'
import { CustomHtmlRenderer } from '../components/profileBlocks/CustomHtmlRenderer'

/** 关系路线的 6 个可视节点（ACQUAINTANCE/FRIEND 合归「靠近」）。 */
const ROUTE_NODES = ['STRANGER', 'FRIEND', 'CONFIDANT', 'ROMANTIC_INTEREST', 'LOVER', 'BONDED'] as const

/** Bespoke 详情页组件 registry（iframe-isolated rich profile） */
const BESPOKE_PROFILES: Record<string, ComponentType<{ profile: CharacterProfileDTO }>> = {
  ji_yu: JiYuProfile,
  li_shen: LiShenProfile,
  cheng_xu: ChengXuProfile,
  lilith: LilithProfile,
  gu_beichen: GuBeichenProfile,
  qin_xiao: QinXiaoProfile,
  jiang_yueze: JiangYuezeProfile,
  jiang_ye: JiangYeProfile,
  gu_xingzhou: GuXingzhouProfile,
  li_jue: LiJueProfile,
  shen_yichen: ShenYichenProfile,
  shen_yuchuan: ShenYuchuanProfile,
  luo_fei: LuoFeiProfile,
  pei_tinglan: PeiTinglanProfile,
  fu_mingxiu: FuMingxiuProfile,
  xize: XizeProfile,
  jiang_li: JiangLiProfile,
  pei_jue: PeiJueProfile,
  huo_cheng: HuoChengProfile,
  zhou_jin: ZhouJinProfile,
  bai_qinghuan: BaiQinghuanProfile,
  cheng_zhi: ChengZhiProfile,
  lu_tingsheng: LuTingshengProfile,
  gu_nanqiao: GuNanqiaoProfile,
  yun_zhi: YunZhiProfile,
  su_wan: SuWanProfile,
  lin_xiaoman: LinXiaomanProfile,
  lu_zhao: LuZhaoProfile,
  su_yueyao: SuYueyaoProfile,
  huo_shiyu: HuoShiyuProfile,
  su_nian: SuNianProfile,
  su_yun: SuYunProfile,
  gu_qingwan: GuQingwanProfile,
  gu_xingmian: GuXingmianProfile,
  song_ye: SongYeProfile,
  vito_rosetti: VitoRosettiProfile,
  xie_ci: XieCiProfile,
  shen_liao: ShenLiaoProfile,
  lu_wenjing: LuWenjingProfile,
  jiang_ran: JiangRanProfile,
  gu_yanli: GuYanliProfile,
  xu_zhihan: XuZhihanProfile,
  linyuan_manor: LinyuanManorProfile,
  free_muse: FreeMuseProfile,
  qingyu_band: QingyuBandProfile,
  gui_bai: GuiBaiProfile,
  yin_ci: YinCiProfile,
  he_zhuo: HeZhuoProfile,
  wenyining: WenYiningProfile,
  wei_heng: WeiHengProfile,
  qi_fei: QiFeiProfile,
  shiyan: ShiyanProfile,
  churan: ChuRanProfile,
  he_linchuan: HeLinchuanProfile,
  wen_yanqing: WenYanqingProfile,
  cen_li: CenLiProfile,
  xie_tingyun: XieTingyunProfile,
  xu_qichi: XuQichiProfile,
  xie_mingluan: XieMingluanProfile,
  qi_wang: QiWangProfile,
  yan_wujiu: YanWujiuProfile,
  li_yao: LiYaoProfile,
  tang_jingzhou: TangJingzhouProfile,
  pei_zhaoye: PeiZhaoyeProfile,
}

/** Chrome 视觉调色盘 registry（React 外层chrome，非 iframe 内层） */
export type ChromePalette = {
  bg: string
  coverBg: string
  scrimGradient: string
  nameColor: string
  ageColor: string
  taglineColor: string
  chipActiveBg: string
  chipActiveBorder: string
  chipActiveText: string
  chipInactiveBg: string
  chipInactiveBorder: string
  chipInactiveText: string
  ctaGradient: string
  ctaShadow: string
}

const CHROME_PALETTES: Record<string, ChromePalette> = {
  ji_yu: {
    bg: '#171019',
    coverBg: '#1B1320',
    scrimGradient: 'linear-gradient(to top,#171019 6%,rgba(23,16,25,.4) 40%,transparent 100%)',
    nameColor: '#ECE2E7',
    ageColor: '#B4A4AF',
    taglineColor: '#E08298',
    chipActiveBg: 'rgba(194,74,99,.08)',
    chipActiveBorder: 'rgba(194,74,99,.32)',
    chipActiveText: '#E08298',
    chipInactiveBg: 'white/5',
    chipInactiveBorder: 'white/10',
    chipInactiveText: '#B4A4AF',
    ctaGradient: 'linear-gradient(105deg,#C24A63,#9C3A55)',
    ctaShadow: '0 10px 26px rgba(194,74,99,0.32)',
  },
  li_shen: {
    bg: '#0F0B0D',
    coverBg: '#1A1315',
    scrimGradient: 'linear-gradient(to top,#0F0B0D 6%,rgba(15,11,13,.4) 40%,transparent 100%)',
    nameColor: '#EDE3E5',
    ageColor: '#B8A8AB',
    taglineColor: '#D85B74',
    chipActiveBg: 'rgba(184,58,82,.08)',
    chipActiveBorder: 'rgba(184,58,82,.32)',
    chipActiveText: '#D85B74',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#B8A8AB',
    ctaGradient: 'linear-gradient(105deg,#B83A52,#8C2D3E)',
    ctaShadow: '0 10px 26px rgba(184,58,82,0.38)',
  },
  cheng_xu: {
    bg: '#13151A',
    coverBg: '#1B1D22',
    scrimGradient: 'linear-gradient(to top,#13151A 6%,rgba(19,21,26,.4) 40%,transparent 100%)',
    nameColor: '#EDE8E3',
    ageColor: '#B8AFA7',
    taglineColor: '#EAA968',
    chipActiveBg: 'rgba(208,138,78,.12)',
    chipActiveBorder: 'rgba(208,138,78,.32)',
    chipActiveText: '#EAA968',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#B8AFA7',
    ctaGradient: 'linear-gradient(105deg,#D08A4E,#B8743A)',
    ctaShadow: '0 10px 26px rgba(208,138,78,0.36)',
  },
  lilith: {
    bg: '#0D0A0E',
    coverBg: '#1A0F16',
    scrimGradient: 'linear-gradient(to top,#0D0A0E 6%,rgba(13,10,14,.4) 40%,transparent 100%)',
    nameColor: '#EDE7E3',
    ageColor: '#B39A90',
    taglineColor: '#E4C482',
    chipActiveBg: 'rgba(212,165,87,.12)',
    chipActiveBorder: 'rgba(212,165,87,.32)',
    chipActiveText: '#E4C482',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#B39A90',
    ctaGradient: 'linear-gradient(105deg,#B8294B,#8C1F38)',
    ctaShadow: '0 10px 26px rgba(184,41,75,0.4)',
  },
  gu_beichen: {
    bg: '#0C0C0E',
    coverBg: '#141312',
    scrimGradient: 'linear-gradient(to top,#0C0C0E 6%,rgba(12,12,14,.4) 40%,transparent 100%)',
    nameColor: '#F2EDE6',
    ageColor: '#9A938A',
    taglineColor: '#C4937D',
    chipActiveBg: 'rgba(196,147,125,.1)',
    chipActiveBorder: 'rgba(196,147,125,.34)',
    chipActiveText: '#C4937D',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#9A938A',
    ctaGradient: 'linear-gradient(105deg,#C4937D,#9C6E58)',
    ctaShadow: '0 10px 26px rgba(196,147,125,0.32)',
  },
  qin_xiao: {
    bg: '#0B0908',
    coverBg: '#170F0D',
    scrimGradient: 'linear-gradient(to top,#0B0908 6%,rgba(11,9,8,.4) 40%,transparent 100%)',
    nameColor: '#ECE2DB',
    ageColor: '#948A82',
    taglineColor: '#D98A4A',
    chipActiveBg: 'rgba(217,138,74,.1)',
    chipActiveBorder: 'rgba(217,138,74,.34)',
    chipActiveText: '#D98A4A',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#948A82',
    ctaGradient: 'linear-gradient(105deg,#B82A2A,#8A1F1F)',
    ctaShadow: '0 10px 26px rgba(184,42,42,0.38)',
  },
  jiang_yueze: {
    bg: '#0A0C10',
    coverBg: '#12161C',
    scrimGradient: 'linear-gradient(to top,#0A0C10 6%,rgba(10,12,16,.4) 40%,transparent 100%)',
    nameColor: '#E2E8F0',
    ageColor: '#8B95A1',
    taglineColor: '#7FB0CE',
    chipActiveBg: 'rgba(51,96,126,.16)',
    chipActiveBorder: 'rgba(127,176,206,.32)',
    chipActiveText: '#9FC4DC',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#8B95A1',
    ctaGradient: 'linear-gradient(105deg,#33607E,#274A63)',
    ctaShadow: '0 10px 26px rgba(51,96,126,0.36)',
  },
  jiang_ye: {
    bg: '#16171B',
    coverBg: '#1E2025',
    scrimGradient: 'linear-gradient(to top,#16171B 6%,rgba(22,23,27,.4) 40%,transparent 100%)',
    nameColor: '#F2F0EC',
    ageColor: '#9AA0A8',
    taglineColor: '#FF8C42',
    chipActiveBg: 'rgba(255,140,66,.12)',
    chipActiveBorder: 'rgba(255,140,66,.34)',
    chipActiveText: '#FFB37A',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#9AA0A8',
    ctaGradient: 'linear-gradient(105deg,#FF8C42,#E86E1F)',
    ctaShadow: '0 10px 26px rgba(255,140,66,0.34)',
  },
  gu_xingzhou: {
    bg: '#080A0B',
    coverBg: '#101616',
    scrimGradient: 'linear-gradient(to top,#080A0B 6%,rgba(8,10,11,.4) 40%,transparent 100%)',
    nameColor: '#E6EFEE',
    ageColor: '#8A9A98',
    taglineColor: '#5AC8B4',
    chipActiveBg: 'rgba(90,200,180,.12)',
    chipActiveBorder: 'rgba(90,200,180,.34)',
    chipActiveText: '#7FD8C6',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#8A9A98',
    ctaGradient: 'linear-gradient(105deg,#2E9E8C,#1F7566)',
    ctaShadow: '0 10px 26px rgba(46,158,140,0.34)',
  },
  li_jue: {
    bg: '#0A0A0B',
    coverBg: '#141312',
    scrimGradient: 'linear-gradient(to top,#0A0A0B 6%,rgba(10,10,11,.4) 40%,transparent 100%)',
    nameColor: '#EAE6E1',
    ageColor: '#9A928C',
    taglineColor: '#CB8A4A',
    chipActiveBg: 'rgba(168,50,50,.14)',
    chipActiveBorder: 'rgba(168,50,50,.34)',
    chipActiveText: '#D98A7A',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#9A928C',
    ctaGradient: 'linear-gradient(105deg,#A83232,#7E2020)',
    ctaShadow: '0 10px 26px rgba(168,50,50,0.36)',
  },
  shen_yichen: {
    bg: '#101018',
    coverBg: '#16161f',
    scrimGradient: 'linear-gradient(to top,#101018 6%,rgba(16,16,24,.4) 40%,transparent 100%)',
    nameColor: '#EAE2E6',
    ageColor: '#948A93',
    taglineColor: '#B892A3',
    chipActiveBg: 'rgba(140,106,122,.14)',
    chipActiveBorder: 'rgba(140,106,122,.36)',
    chipActiveText: '#C79FB0',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#948A93',
    ctaGradient: 'linear-gradient(105deg,#8C6A7A,#6B4F5C)',
    ctaShadow: '0 10px 26px rgba(140,106,122,0.34)',
  },
  shen_yuchuan: {
    bg: '#0A0E13',
    coverBg: '#101720',
    scrimGradient: 'linear-gradient(to top,#0A0E13 6%,rgba(10,14,19,.4) 40%,transparent 100%)',
    nameColor: '#E2EAF0',
    ageColor: '#849098',
    taglineColor: '#7FB4C8',
    chipActiveBg: 'rgba(91,143,163,.14)',
    chipActiveBorder: 'rgba(91,143,163,.36)',
    chipActiveText: '#8FBFD2',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#849098',
    ctaGradient: 'linear-gradient(105deg,#5B8FA3,#3F6C7E)',
    ctaShadow: '0 10px 26px rgba(91,143,163,0.36)',
  },
  luo_fei: {
    bg: '#16090F',
    coverBg: '#1F0E16',
    scrimGradient: 'linear-gradient(to top,#16090F 6%,rgba(22,9,15,.4) 40%,transparent 100%)',
    nameColor: '#EDE0E4',
    ageColor: '#9A828B',
    taglineColor: '#C77E92',
    chipActiveBg: 'rgba(140,90,107,.16)',
    chipActiveBorder: 'rgba(140,90,107,.38)',
    chipActiveText: '#CE8598',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#9A828B',
    ctaGradient: 'linear-gradient(105deg,#8C5A6B,#6B3E4C)',
    ctaShadow: '0 10px 26px rgba(140,90,107,0.38)',
  },
  pei_tinglan: {
    bg: '#14101A',
    coverBg: '#1B1624',
    scrimGradient: 'linear-gradient(to top,#14101A 6%,rgba(20,16,26,.4) 40%,transparent 100%)',
    nameColor: '#E8E2EE',
    ageColor: '#8F889A',
    taglineColor: '#B8A6C8',
    chipActiveBg: 'rgba(140,122,155,.16)',
    chipActiveBorder: 'rgba(140,122,155,.36)',
    chipActiveText: '#C2B2D0',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#8F889A',
    ctaGradient: 'linear-gradient(105deg,#8C7A9B,#675A75)',
    ctaShadow: '0 10px 26px rgba(140,122,155,0.34)',
  },
  fu_mingxiu: {
    bg: '#16120E',
    coverBg: '#1E1913',
    scrimGradient: 'linear-gradient(to top,#16120E 6%,rgba(22,18,14,.4) 40%,transparent 100%)',
    nameColor: '#EBE4DA',
    ageColor: '#988E80',
    taglineColor: '#C4B09A',
    chipActiveBg: 'rgba(155,138,122,.16)',
    chipActiveBorder: 'rgba(155,138,122,.36)',
    chipActiveText: '#CBB8A2',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#988E80',
    ctaGradient: 'linear-gradient(105deg,#9B8A7A,#75665A)',
    ctaShadow: '0 10px 26px rgba(155,138,122,0.34)',
  },
  xize: {
    bg: '#0F1319',
    coverBg: '#151B23',
    scrimGradient: 'linear-gradient(to top,#0F1319 6%,rgba(15,19,25,.4) 40%,transparent 100%)',
    nameColor: '#E4E8EE',
    ageColor: '#868E98',
    taglineColor: '#9AAAB8',
    chipActiveBg: 'rgba(107,122,140,.16)',
    chipActiveBorder: 'rgba(107,122,140,.36)',
    chipActiveText: '#A6B5C2',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#868E98',
    ctaGradient: 'linear-gradient(105deg,#6B7A8C,#4E5A69)',
    ctaShadow: '0 10px 26px rgba(107,122,140,0.34)',
  },
  jiang_li: {
    bg: '#150F11',
    coverBg: '#1E1518',
    scrimGradient: 'linear-gradient(to top,#150F11 6%,rgba(21,15,17,.4) 40%,transparent 100%)',
    nameColor: '#EDE2E2',
    ageColor: '#988486',
    taglineColor: '#D08A8A',
    chipActiveBg: 'rgba(169,107,107,.16)',
    chipActiveBorder: 'rgba(169,107,107,.38)',
    chipActiveText: '#CF9393',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#988486',
    ctaGradient: 'linear-gradient(105deg,#A96B6B,#824F4F)',
    ctaShadow: '0 10px 26px rgba(169,107,107,0.36)',
  },
  pei_jue: {
    bg: '#0a0a0c',
    coverBg: '#151517',
    scrimGradient: 'linear-gradient(180deg, rgba(10,10,12,0) 0%, rgba(10,10,12,0.7) 50%, rgba(10,10,12,0.95) 100%)',
    nameColor: '#e8ddd0',
    ageColor: '#b59b82',
    taglineColor: '#d4c4b0',
    chipActiveBg: 'rgba(195,68,58,0.2)',
    chipActiveBorder: 'rgba(195,68,58,0.32)',
    chipActiveText: '#c3443a',
    chipInactiveBg: 'rgba(248,242,250,0.06)',
    chipInactiveBorder: 'rgba(248,242,250,0.1)',
    chipInactiveText: '#998877',
    ctaGradient: 'linear-gradient(135deg, #c3443a 0%, #9a342b 100%)',
    ctaShadow: '0 4px 16px rgba(195,68,58,0.3)',
  },
  huo_cheng: {
    bg: '#1A1612',
    coverBg: '#2A2218',
    scrimGradient: 'linear-gradient(180deg, rgba(26,22,18,0) 0%, rgba(26,22,18,0.85) 70%, rgba(26,22,18,0.95) 100%)',
    nameColor: '#F5E6D3',
    ageColor: '#B39E8D',
    taglineColor: '#D4CFC8',
    chipActiveBg: '#D97843',
    chipActiveBorder: 'rgba(217,120,67,0.32)',
    chipActiveText: '#1A1612',
    chipInactiveBg: 'rgba(217,120,67,0.15)',
    chipInactiveBorder: 'rgba(217,120,67,0.2)',
    chipInactiveText: '#D4A882',
    ctaGradient: 'linear-gradient(135deg, #D97843 0%, #B85E2F 100%)',
    ctaShadow: '0 4px 16px rgba(217,120,67,0.35)',
  },
  zhou_jin: {
    bg: '#0a0a0d',
    coverBg: '#12121a',
    scrimGradient: 'linear-gradient(180deg, rgba(10,10,13,0) 0%, rgba(10,10,13,0.85) 65%, #0a0a0d 100%)',
    nameColor: '#eae5de',
    ageColor: '#dc3c48',
    taglineColor: '#b8aea6',
    chipActiveBg: 'rgba(220,60,72,0.15)',
    chipActiveBorder: 'rgba(220,60,72,0.32)',
    chipActiveText: '#dc7c82',
    chipInactiveBg: 'rgba(220,60,72,0.04)',
    chipInactiveBorder: 'rgba(220,60,72,0.1)',
    chipInactiveText: '#8a7670',
    ctaGradient: 'linear-gradient(135deg, #dc3c48 0%, #a82832 100%)',
    ctaShadow: '0 4px 16px rgba(220,60,72,0.3), 0 2px 8px rgba(220,60,72,0.2)',
  },
  bai_qinghuan: {
    bg: '#fdfcfa',
    coverBg: 'linear-gradient(165deg,#fdfcfa 0%,#f8f5f0 100%)',
    scrimGradient: 'linear-gradient(180deg,rgba(255,182,193,0.12),transparent)',
    nameColor: '#3a3330',
    ageColor: '#7a6f68',
    taglineColor: '#5a5350',
    chipActiveBg: 'rgba(255,182,193,0.25)',
    chipActiveBorder: 'rgba(255,182,193,0.32)',
    chipActiveText: '#6a4f4a',
    chipInactiveBg: 'rgba(255,182,193,0.08)',
    chipInactiveBorder: 'rgba(255,182,193,0.12)',
    chipInactiveText: '#9a8580',
    ctaGradient: 'linear-gradient(135deg,#d89098,#c77f8a)',
    ctaShadow: '0 4px 12px rgba(216,144,152,0.25)',
  },
  cheng_zhi: {
    bg: '#f8f6f3',
    coverBg: '#4A9B9B',
    scrimGradient: 'linear-gradient(180deg, rgba(74,155,155,0) 0%, rgba(74,155,155,0.85) 100%)',
    nameColor: '#ffffff',
    ageColor: '#e8f5f5',
    taglineColor: '#f0f8f8',
    chipActiveBg: '#4A9B9B',
    chipActiveBorder: 'rgba(74,155,155,0.32)',
    chipActiveText: '#ffffff',
    chipInactiveBg: 'rgba(74,155,155,0.15)',
    chipInactiveBorder: 'rgba(74,155,155,0.2)',
    chipInactiveText: '#3a7a7a',
    ctaGradient: 'linear-gradient(135deg, #4A9B9B 0%, #3a8a8a 100%)',
    ctaShadow: '0 4px 12px rgba(74,155,155,0.3)',
  },
  lu_tingsheng: {
    bg: '#ebe5d8',
    coverBg: '#d9ccb8',
    scrimGradient: 'linear-gradient(to bottom, rgba(235,229,216,0), rgba(235,229,216,0.95))',
    nameColor: '#3a342c',
    ageColor: '#8b5a47',
    taglineColor: '#5c5449',
    chipActiveBg: 'rgba(157,58,50,0.12)',
    chipActiveBorder: 'rgba(157,58,50,0.4)',
    chipActiveText: '#9d3a32',
    chipInactiveBg: 'rgba(157,58,50,0.04)',
    chipInactiveBorder: 'rgba(157,58,50,0.15)',
    chipInactiveText: '#8b5a47',
    ctaGradient: 'linear-gradient(135deg, #9d3a32, #b84a3f)',
    ctaShadow: '0 4px 12px rgba(157,58,50,0.3)',
  },
  gu_nanqiao: {
    bg: '#f9fafb',
    coverBg: '#e8f2fb',
    scrimGradient: 'linear-gradient(to bottom, rgba(249,250,251,0), rgba(249,250,251,0.95))',
    nameColor: '#2c3e50',
    ageColor: '#7a95b0',
    taglineColor: '#546e7a',
    chipActiveBg: 'rgba(90,155,213,0.15)',
    chipActiveBorder: 'rgba(90,155,213,0.4)',
    chipActiveText: '#5a9bd5',
    chipInactiveBg: 'rgba(90,155,213,0.05)',
    chipInactiveBorder: 'rgba(90,155,213,0.2)',
    chipInactiveText: '#90a4b7',
    ctaGradient: 'linear-gradient(135deg, #5a9bd5, #7ab3e8)',
    ctaShadow: '0 4px 12px rgba(90,155,213,0.3)',
  },
  yun_zhi: {
    bg: 'radial-gradient(ellipse at top, #1a1d28, #0d0f15)',
    coverBg: '#15181f',
    scrimGradient: 'linear-gradient(to bottom, rgba(13,15,21,0), rgba(13,15,21,0.95))',
    nameColor: '#f0f4f8',
    ageColor: '#a9c0dc',
    taglineColor: '#b5c4d4',
    chipActiveBg: 'rgba(169,192,220,0.12)',
    chipActiveBorder: 'rgba(169,192,220,0.35)',
    chipActiveText: '#a9c0dc',
    chipInactiveBg: 'rgba(169,192,220,0.04)',
    chipInactiveBorder: 'rgba(169,192,220,0.15)',
    chipInactiveText: 'rgba(169,192,220,0.6)',
    ctaGradient: 'linear-gradient(135deg, #a9c0dc, #c5d6e8)',
    ctaShadow: '0 4px 16px rgba(169,192,220,0.25)',
  },
  su_wan: {
    bg: '#fffaf0',
    coverBg: '#fff8dc',
    scrimGradient: 'linear-gradient(to bottom, rgba(255,250,240,0), rgba(255,250,240,0.95))',
    nameColor: '#3d2b28',
    ageColor: '#8b7355',
    taglineColor: '#6a5647',
    chipActiveBg: 'rgba(212,165,116,0.15)',
    chipActiveBorder: 'rgba(212,165,116,0.4)',
    chipActiveText: '#d4a574',
    chipInactiveBg: 'rgba(212,165,116,0.05)',
    chipInactiveBorder: 'rgba(212,165,116,0.2)',
    chipInactiveText: '#c4a57b',
    ctaGradient: 'linear-gradient(135deg, #d4a574, #e0b88a)',
    ctaShadow: '0 4px 12px rgba(212,165,116,0.3)',
  },
  lin_xiaoman: {
    bg: '#fff9e6',
    coverBg: '#f8fbff',
    scrimGradient: 'linear-gradient(to bottom, rgba(255,249,230,0), rgba(255,249,230,0.95))',
    nameColor: '#2c3e50',
    ageColor: '#7a8a9a',
    taglineColor: '#546070',
    chipActiveBg: 'rgba(255,154,86,0.15)',
    chipActiveBorder: 'rgba(255,154,86,0.4)',
    chipActiveText: '#ff9a56',
    chipInactiveBg: 'rgba(255,154,86,0.05)',
    chipInactiveBorder: 'rgba(255,154,86,0.2)',
    chipInactiveText: '#ffa873',
    ctaGradient: 'linear-gradient(135deg, #ff9a56, #ffb678)',
    ctaShadow: '0 4px 12px rgba(255,154,86,0.3)',
  },
  lu_zhao: {
    bg: '#0d0d0f',
    coverBg: '#1a1a1c',
    scrimGradient: 'linear-gradient(to bottom, rgba(13,13,15,0), rgba(13,13,15,0.95))',
    nameColor: '#f5f5f5',
    ageColor: '#c9c9c9',
    taglineColor: '#e0e0e0',
    chipActiveBg: 'rgba(220,53,69,0.15)',
    chipActiveBorder: 'rgba(220,53,69,0.4)',
    chipActiveText: '#dc3545',
    chipInactiveBg: 'rgba(220,53,69,0.05)',
    chipInactiveBorder: 'rgba(220,53,69,0.2)',
    chipInactiveText: '#dc7882',
    ctaGradient: 'linear-gradient(135deg, #dc3545, #c82333)',
    ctaShadow: '0 4px 12px rgba(220,53,69,0.4)',
  },
  su_yueyao: {
    bg: '#fffaf5',
    coverBg: '#fff8f0',
    scrimGradient: 'linear-gradient(to bottom, rgba(255,250,245,0), rgba(255,250,245,0.95))',
    nameColor: '#3d2b28',
    ageColor: '#8b7a70',
    taglineColor: '#6a5a50',
    chipActiveBg: 'rgba(232,122,102,0.15)',
    chipActiveBorder: 'rgba(232,122,102,0.4)',
    chipActiveText: '#e87a66',
    chipInactiveBg: 'rgba(232,122,102,0.05)',
    chipInactiveBorder: 'rgba(232,122,102,0.2)',
    chipInactiveText: '#c89080',
    ctaGradient: 'linear-gradient(135deg, #e87a66, #f0a090)',
    ctaShadow: '0 4px 12px rgba(232,122,102,0.3)',
  },
  huo_shiyu: {
    bg: '#0f1419',
    coverBg: '#1a2332',
    scrimGradient: 'linear-gradient(to bottom, rgba(15,20,25,0), rgba(15,20,25,0.95))',
    nameColor: '#c8d4e0',
    ageColor: '#8a9aaa',
    taglineColor: '#a0b0c0',
    chipActiveBg: 'rgba(96,165,250,0.15)',
    chipActiveBorder: 'rgba(96,165,250,0.4)',
    chipActiveText: '#60a5fa',
    chipInactiveBg: 'rgba(96,165,250,0.05)',
    chipInactiveBorder: 'rgba(96,165,250,0.2)',
    chipInactiveText: '#7dd3fc',
    ctaGradient: 'linear-gradient(135deg, #60a5fa, #3b82f6)',
    ctaShadow: '0 4px 12px rgba(96,165,250,0.3)',
  },
  su_nian: {
    bg: '#fff9e6',
    coverBg: '#fffacd',
    scrimGradient: 'linear-gradient(to bottom, rgba(255,249,230,0), rgba(255,249,230,0.95))',
    nameColor: '#3d2818',
    ageColor: '#8b7355',
    taglineColor: '#6a5a47',
    chipActiveBg: 'rgba(255,159,64,0.15)',
    chipActiveBorder: 'rgba(255,159,64,0.4)',
    chipActiveText: '#ff9f40',
    chipInactiveBg: 'rgba(255,159,64,0.05)',
    chipInactiveBorder: 'rgba(255,159,64,0.2)',
    chipInactiveText: '#ffb84d',
    ctaGradient: 'linear-gradient(135deg, #ff9f40, #ffb84d)',
    ctaShadow: '0 4px 12px rgba(255,159,64,0.3)',
  },
  su_yun: {
    bg: '#0d0d0d',
    coverBg: '#1a1a1a',
    scrimGradient: 'linear-gradient(to bottom, rgba(13,13,13,0), rgba(13,13,13,0.95))',
    nameColor: '#f4e8d0',
    ageColor: '#c4af8f',
    taglineColor: '#d4bfa0',
    chipActiveBg: 'rgba(212,175,143,0.15)',
    chipActiveBorder: 'rgba(212,175,143,0.4)',
    chipActiveText: '#d4af8f',
    chipInactiveBg: 'rgba(212,175,143,0.05)',
    chipInactiveBorder: 'rgba(212,175,143,0.2)',
    chipInactiveText: '#a8957a',
    ctaGradient: 'linear-gradient(135deg, #d4af8f, #c4a080)',
    ctaShadow: '0 4px 12px rgba(212,175,143,0.3)',
  },
  gu_qingwan: {
    bg: '#f5f1ed',
    coverBg: '#ebe7e3',
    scrimGradient: 'linear-gradient(to bottom, rgba(245,241,237,0), rgba(245,241,237,0.95))',
    nameColor: '#1a1614',
    ageColor: '#6a5e58',
    taglineColor: '#4a3e38',
    chipActiveBg: 'rgba(122,157,143,0.15)',
    chipActiveBorder: 'rgba(122,157,143,0.4)',
    chipActiveText: '#7a9d8f',
    chipInactiveBg: 'rgba(122,157,143,0.05)',
    chipInactiveBorder: 'rgba(122,157,143,0.2)',
    chipInactiveText: '#8aada0',
    ctaGradient: 'linear-gradient(135deg, #7a9d8f, #8aada0)',
    ctaShadow: '0 4px 12px rgba(122,157,143,0.3)',
  },
  gu_xingmian: {
    bg: '#0f1419',
    coverBg: '#1a1f24',
    scrimGradient: 'linear-gradient(to bottom, rgba(15,20,25,0), rgba(15,20,25,0.95))',
    nameColor: '#c8ccd4',
    ageColor: '#8a8e96',
    taglineColor: '#a0a4ac',
    chipActiveBg: 'rgba(224,184,114,0.15)',
    chipActiveBorder: 'rgba(224,184,114,0.4)',
    chipActiveText: '#e0b872',
    chipInactiveBg: 'rgba(224,184,114,0.05)',
    chipInactiveBorder: 'rgba(224,184,114,0.2)',
    chipInactiveText: '#c8a862',
    ctaGradient: 'linear-gradient(135deg, #e0b872, #d0a862)',
    ctaShadow: '0 4px 12px rgba(224,184,114,0.3)',
  },
  song_ye: {
    bg: '#f8f8f6',
    coverBg: '#f0f0ee',
    scrimGradient: 'linear-gradient(to bottom, rgba(248,248,246,0), rgba(248,248,246,0.95))',
    nameColor: '#2a2a2a',
    ageColor: '#6a6a6a',
    taglineColor: '#4a4a4a',
    chipActiveBg: 'rgba(230,126,34,0.15)',
    chipActiveBorder: 'rgba(230,126,34,0.4)',
    chipActiveText: '#e67e22',
    chipInactiveBg: 'rgba(230,126,34,0.05)',
    chipInactiveBorder: 'rgba(230,126,34,0.2)',
    chipInactiveText: '#d35400',
    ctaGradient: 'linear-gradient(135deg, #e67e22, #d35400)',
    ctaShadow: '0 4px 12px rgba(230,126,34,0.3)',
  },
  vito_rosetti: {
    bg: '#1a1412',
    coverBg: '#2a2220',
    scrimGradient: 'linear-gradient(to bottom, rgba(26,20,18,0), rgba(26,20,18,0.95))',
    nameColor: '#d4c4b8',
    ageColor: '#a49488',
    taglineColor: '#b4a498',
    chipActiveBg: 'rgba(184,134,11,0.15)',
    chipActiveBorder: 'rgba(184,134,11,0.4)',
    chipActiveText: '#b8860b',
    chipInactiveBg: 'rgba(184,134,11,0.05)',
    chipInactiveBorder: 'rgba(184,134,11,0.2)',
    chipInactiveText: '#a8760b',
    ctaGradient: 'linear-gradient(135deg, #b8860b, #987010)',
    ctaShadow: '0 4px 12px rgba(184,134,11,0.3)',
  },
  xie_ci: {
    bg: '#3a3a3c',
    coverBg: '#2a2a2c',
    scrimGradient: 'linear-gradient(to bottom, rgba(58,58,60,0), rgba(58,58,60,0.95))',
    nameColor: '#e8e8e8',
    ageColor: '#b8b8b8',
    taglineColor: '#c8c8c8',
    chipActiveBg: 'rgba(232,93,60,0.15)',
    chipActiveBorder: 'rgba(232,93,60,0.4)',
    chipActiveText: '#e85d3c',
    chipInactiveBg: 'rgba(232,93,60,0.05)',
    chipInactiveBorder: 'rgba(232,93,60,0.2)',
    chipInactiveText: '#c84d2c',
    ctaGradient: 'linear-gradient(135deg, #e85d3c, #c84d2c)',
    ctaShadow: '0 4px 12px rgba(232,93,60,0.3)',
  },
  shen_liao: {
    bg: '#1e2024',
    coverBg: '#2a2d32',
    scrimGradient: 'linear-gradient(to bottom, rgba(30,32,36,0), rgba(30,32,36,0.95))',
    nameColor: '#ffaa55',
    ageColor: '#c88844',
    taglineColor: '#e09955',
    chipActiveBg: 'rgba(255,136,51,0.15)',
    chipActiveBorder: 'rgba(255,136,51,0.4)',
    chipActiveText: '#ff8833',
    chipInactiveBg: 'rgba(255,136,51,0.05)',
    chipInactiveBorder: 'rgba(255,136,51,0.2)',
    chipInactiveText: '#e07733',
    ctaGradient: 'linear-gradient(135deg, #ff8833, #e07733)',
    ctaShadow: '0 4px 12px rgba(255,136,51,0.3)',
  },
  lu_wenjing: {
    bg: '#12151a',
    coverBg: '#1a1d22',
    scrimGradient: 'linear-gradient(to bottom, rgba(18,21,26,0), rgba(18,21,26,0.95))',
    nameColor: '#c8d8e8',
    ageColor: '#8a9aaa',
    taglineColor: '#a0b0c0',
    chipActiveBg: 'rgba(110,170,200,0.15)',
    chipActiveBorder: 'rgba(110,170,200,0.4)',
    chipActiveText: '#6eaac8',
    chipInactiveBg: 'rgba(110,170,200,0.05)',
    chipInactiveBorder: 'rgba(110,170,200,0.2)',
    chipInactiveText: '#8ab8d8',
    ctaGradient: 'linear-gradient(135deg, #6eaac8, #5a9ab8)',
    ctaShadow: '0 4px 12px rgba(110,170,200,0.3)',
  },
  jiang_ran: {
    bg: '#2a2624',
    coverBg: '#3a3632',
    scrimGradient: 'linear-gradient(to bottom, rgba(42,38,36,0), rgba(42,38,36,0.95))',
    nameColor: '#f5b88a',
    ageColor: '#c58a5a',
    taglineColor: '#e8a58a',
    chipActiveBg: 'rgba(210,105,80,0.15)',
    chipActiveBorder: 'rgba(210,105,80,0.4)',
    chipActiveText: '#d26950',
    chipInactiveBg: 'rgba(210,105,80,0.05)',
    chipInactiveBorder: 'rgba(210,105,80,0.2)',
    chipInactiveText: '#c25940',
    ctaGradient: 'linear-gradient(135deg, #d26950, #c25940)',
    ctaShadow: '0 4px 12px rgba(210,105,80,0.3)',
  },
  gu_yanli: {
    bg: '#0d1410',
    coverBg: '#1a2420',
    scrimGradient: 'linear-gradient(to bottom, rgba(13,20,16,0), rgba(13,20,16,0.95))',
    nameColor: '#d4d8d5',
    ageColor: '#a4a8a5',
    taglineColor: '#b4b8b5',
    chipActiveBg: 'rgba(184,153,93,0.15)',
    chipActiveBorder: 'rgba(184,153,93,0.4)',
    chipActiveText: '#b8995d',
    chipInactiveBg: 'rgba(184,153,93,0.05)',
    chipInactiveBorder: 'rgba(184,153,93,0.2)',
    chipInactiveText: '#a8894d',
    ctaGradient: 'linear-gradient(135deg, #b8995d, #a8894d)',
    ctaShadow: '0 4px 12px rgba(184,153,93,0.3)',
  },
  xu_zhihan: {
    bg: '#f8f9fa',
    coverBg: '#e8e9ea',
    scrimGradient: 'linear-gradient(to bottom, rgba(248,249,250,0), rgba(248,249,250,0.95))',
    nameColor: '#2c3338',
    ageColor: '#6c7378',
    taglineColor: '#4c5358',
    chipActiveBg: 'rgba(90,122,159,0.15)',
    chipActiveBorder: 'rgba(90,122,159,0.4)',
    chipActiveText: '#5a7a9f',
    chipInactiveBg: 'rgba(90,122,159,0.05)',
    chipInactiveBorder: 'rgba(90,122,159,0.2)',
    chipInactiveText: '#7a9abf',
    ctaGradient: 'linear-gradient(135deg, #5a7a9f, #4a6a8f)',
    ctaShadow: '0 4px 12px rgba(90,122,159,0.3)',
  },
  linyuan_manor: {
    bg: '#14181c',
    coverBg: '#1a2026',
    scrimGradient: 'linear-gradient(to top,#14181c 6%,rgba(20,24,28,.4) 40%,transparent 100%)',
    nameColor: '#e4e8ec',
    ageColor: '#9aa6b3',
    taglineColor: '#b4bcc5',
    chipActiveBg: 'rgba(107,122,140,0.28)',
    chipActiveBorder: 'rgba(107,122,140,0.5)',
    chipActiveText: '#d4dae0',
    chipInactiveBg: 'rgba(107,122,140,0.1)',
    chipInactiveBorder: 'rgba(107,122,140,0.24)',
    chipInactiveText: '#9aa6b3',
    ctaGradient: 'linear-gradient(135deg, #6B7A8C, #55636f)',
    ctaShadow: '0 4px 14px rgba(107,122,140,0.35)',
  },
  free_muse: {
    bg: '#0a0d12',
    coverBg: '#12161d',
    scrimGradient: 'linear-gradient(to top,#0a0d12 6%,rgba(10,13,18,.4) 40%,transparent 100%)',
    nameColor: '#dbe3ea',
    ageColor: '#95a1ad',
    taglineColor: '#aeb8c2',
    chipActiveBg: 'rgba(143,165,184,0.26)',
    chipActiveBorder: 'rgba(143,165,184,0.5)',
    chipActiveText: '#d4dde5',
    chipInactiveBg: 'rgba(143,165,184,0.09)',
    chipInactiveBorder: 'rgba(143,165,184,0.22)',
    chipInactiveText: '#95a1ad',
    ctaGradient: 'linear-gradient(135deg, #8FA5B8, #7089a0)',
    ctaShadow: '0 4px 14px rgba(143,165,184,0.35)',
  },
  qingyu_band: {
    bg: '#15181f',
    coverBg: '#1c2029',
    scrimGradient: 'linear-gradient(to top,#15181f 6%,rgba(21,24,31,.4) 40%,transparent 100%)',
    nameColor: '#e6ebf0',
    ageColor: '#9aa6b3',
    taglineColor: '#b2bbc5',
    chipActiveBg: 'rgba(224,169,109,0.24)',
    chipActiveBorder: 'rgba(224,169,109,0.5)',
    chipActiveText: '#e8c79f',
    chipInactiveBg: 'rgba(143,165,184,0.1)',
    chipInactiveBorder: 'rgba(143,165,184,0.24)',
    chipInactiveText: '#9aa6b3',
    ctaGradient: 'linear-gradient(135deg, #8FA5B8, #E0A96D)',
    ctaShadow: '0 4px 14px rgba(224,169,109,0.3)',
  },
  gui_bai: {
    bg: '#0c1012',
    coverBg: '#141a1c',
    scrimGradient: 'linear-gradient(to top,#0c1012 6%,rgba(12,16,18,.4) 40%,transparent 100%)',
    nameColor: '#e8e0d4',
    ageColor: '#a0a898',
    taglineColor: '#c4b898',
    chipActiveBg: 'rgba(168,176,152,.1)',
    chipActiveBorder: 'rgba(168,176,152,.34)',
    chipActiveText: '#c4b898',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#a0a898',
    ctaGradient: 'linear-gradient(105deg,#a8b098,#8a9880)',
    ctaShadow: '0 10px 26px rgba(168,176,152,0.32)',
  },
  yin_ci: {
    bg: '#0b0909',
    coverBg: '#161010',
    scrimGradient: 'linear-gradient(to top,#0b0909 6%,rgba(11,9,9,.4) 40%,transparent 100%)',
    nameColor: '#e0d4d0',
    ageColor: '#908480',
    taglineColor: '#c84040',
    chipActiveBg: 'rgba(184,48,48,.1)',
    chipActiveBorder: 'rgba(184,48,48,.34)',
    chipActiveText: '#d85050',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#908480',
    ctaGradient: 'linear-gradient(105deg,#b83030,#8a2020)',
    ctaShadow: '0 10px 26px rgba(184,48,48,0.38)',
  },
  he_zhuo: {
    bg: '#11100e',
    coverBg: '#1a1816',
    scrimGradient: 'linear-gradient(to top,#11100e 6%,rgba(17,16,14,.4) 40%,transparent 100%)',
    nameColor: '#ede4d8',
    ageColor: '#8a8078',
    taglineColor: '#c49448',
    chipActiveBg: 'rgba(196,148,72,.1)',
    chipActiveBorder: 'rgba(196,148,72,.34)',
    chipActiveText: '#d4a458',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#8a8078',
    ctaGradient: 'linear-gradient(105deg,#c49448,#a07830)',
    ctaShadow: '0 10px 26px rgba(196,148,72,0.34)',
  },
  wenyining: {
    bg: '#fbf4f6',
    coverBg: '#f3e6ee',
    scrimGradient: 'linear-gradient(to top,#fbf4f6 6%,rgba(251,244,246,.4) 40%,transparent 100%)',
    nameColor: '#7a3f68',
    ageColor: '#a88098',
    taglineColor: '#b06898',
    chipActiveBg: 'rgba(196,138,180,.18)',
    chipActiveBorder: 'rgba(176,104,152,.36)',
    chipActiveText: '#8a4f78',
    chipInactiveBg: 'rgba(176,104,152,.07)',
    chipInactiveBorder: 'rgba(176,104,152,.16)',
    chipInactiveText: '#a06890',
    ctaGradient: 'linear-gradient(105deg,#c48ab4,#9a5586)',
    ctaShadow: '0 10px 26px rgba(154,85,134,0.28)',
  },
  wei_heng: {
    bg: '#0e1319',
    coverBg: '#161e28',
    scrimGradient: 'linear-gradient(to top,#0e1319 6%,rgba(14,19,25,.4) 40%,transparent 100%)',
    nameColor: '#dce6f0',
    ageColor: '#7a8ea0',
    taglineColor: '#8fb4d8',
    chipActiveBg: 'rgba(122,158,196,.12)',
    chipActiveBorder: 'rgba(122,158,196,.36)',
    chipActiveText: '#9fc0dc',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#7a8ea0',
    ctaGradient: 'linear-gradient(105deg,#5b7fa3,#3f5c78)',
    ctaShadow: '0 10px 26px rgba(91,127,163,0.36)',
  },
  qi_fei: {
    bg: '#0b0808',
    coverBg: '#170e0f',
    scrimGradient: 'linear-gradient(to top,#0b0808 6%,rgba(11,8,8,.4) 40%,transparent 100%)',
    nameColor: '#f0e0dc',
    ageColor: '#9a7a7c',
    taglineColor: '#e04850',
    chipActiveBg: 'rgba(216,64,72,.12)',
    chipActiveBorder: 'rgba(216,64,72,.36)',
    chipActiveText: '#f0686e',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#9a7a7c',
    ctaGradient: 'linear-gradient(105deg,#d8404a,#a02830)',
    ctaShadow: '0 10px 26px rgba(216,64,72,0.4)',
  },
  shiyan: {
    bg: '#0c1420',
    coverBg: '#111c2c',
    scrimGradient: 'linear-gradient(to top,#0c1420 6%,rgba(12,20,32,.4) 40%,transparent 100%)',
    nameColor: '#eef2f6',
    ageColor: '#7e93a8',
    taglineColor: '#e6d3a6',
    chipActiveBg: 'rgba(224,196,140,.12)',
    chipActiveBorder: 'rgba(224,196,140,.36)',
    chipActiveText: '#f0dcac',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#7e93a8',
    ctaGradient: 'linear-gradient(105deg,#6f8db0,#3f5a7a)',
    ctaShadow: '0 10px 26px rgba(120,150,185,0.4)',
  },
  churan: {
    bg: '#0a0a0c',
    coverBg: '#150f11',
    scrimGradient: 'linear-gradient(to top,#0a0a0c 6%,rgba(10,10,12,.4) 40%,transparent 100%)',
    nameColor: '#ece6ea',
    ageColor: '#9a7a80',
    taglineColor: '#e4485a',
    chipActiveBg: 'rgba(228,56,64,.12)',
    chipActiveBorder: 'rgba(228,56,64,.36)',
    chipActiveText: '#ff6a70',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#9a7a80',
    ctaGradient: 'linear-gradient(105deg,#d83440,#901c26)',
    ctaShadow: '0 10px 26px rgba(228,56,64,0.42)',
  },
  he_linchuan: {
    bg: '#10140f',
    coverBg: '#171d14',
    scrimGradient: 'linear-gradient(to top,#10140f 6%,rgba(16,20,15,.38) 42%,transparent 100%)',
    nameColor: '#fff4dc',
    ageColor: '#9fa98e',
    taglineColor: '#e7be68',
    chipActiveBg: 'rgba(231,190,104,.12)',
    chipActiveBorder: 'rgba(231,190,104,.38)',
    chipActiveText: '#f2ce7c',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#9fa98e',
    ctaGradient: 'linear-gradient(105deg,#b58a37,#657b45)',
    ctaShadow: '0 10px 26px rgba(181,138,55,.38)',
  },
  wen_yanqing: {
    bg: '#e9efeb',
    coverBg: '#cbdad6',
    scrimGradient: 'linear-gradient(to top,#e9efeb 6%,rgba(233,239,235,.38) 42%,transparent 100%)',
    nameColor: '#1e3033',
    ageColor: '#718885',
    taglineColor: '#9d5f4f',
    chipActiveBg: 'rgba(179,110,90,.1)',
    chipActiveBorder: 'rgba(179,110,90,.34)',
    chipActiveText: '#8f4f40',
    chipInactiveBg: 'rgba(255,255,255,.42)',
    chipInactiveBorder: 'rgba(58,83,81,.15)',
    chipInactiveText: '#58706d',
    ctaGradient: 'linear-gradient(105deg,#a86452,#527a75)',
    ctaShadow: '0 10px 26px rgba(82,122,117,.28)',
  },
  cen_li: {
    bg: '#10191d',
    coverBg: '#18252a',
    scrimGradient: 'linear-gradient(to top,#10191d 6%,rgba(16,25,29,.4) 42%,transparent 100%)',
    nameColor: '#edf3f4',
    ageColor: '#8fa6ae',
    taglineColor: '#d7aa55',
    chipActiveBg: 'rgba(215,170,85,.12)',
    chipActiveBorder: 'rgba(215,170,85,.36)',
    chipActiveText: '#e6c071',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(143,166,174,.2)',
    chipInactiveText: '#9bb0b6',
    ctaGradient: 'linear-gradient(105deg,#b88c3f,#547581)',
    ctaShadow: '0 10px 26px rgba(84,117,129,.34)',
  },
  xie_tingyun: {
    bg: '#171512',
    coverBg: '#211f1a',
    scrimGradient: 'linear-gradient(to top,#171512 6%,rgba(23,21,18,.4) 42%,transparent 100%)',
    nameColor: '#eee6d9',
    ageColor: '#8d9d92',
    taglineColor: '#c49a64',
    chipActiveBg: 'rgba(183,139,86,.12)',
    chipActiveBorder: 'rgba(183,139,86,.36)',
    chipActiveText: '#d0aa78',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(124,157,145,.2)',
    chipInactiveText: '#9aa89e',
    ctaGradient: 'linear-gradient(105deg,#9d7041,#506f66)',
    ctaShadow: '0 10px 26px rgba(86,91,61,.34)',
  },
  xu_qichi: {
    bg: '#111913',
    coverBg: '#1a251c',
    scrimGradient: 'linear-gradient(to top,#111913 6%,rgba(17,25,19,.4) 42%,transparent 100%)',
    nameColor: '#e8eee2',
    ageColor: '#8fa184',
    taglineColor: '#a7c58e',
    chipActiveBg: 'rgba(145,180,120,.12)',
    chipActiveBorder: 'rgba(145,180,120,.36)',
    chipActiveText: '#aed194',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(207,138,122,.2)',
    chipInactiveText: '#b69890',
    ctaGradient: 'linear-gradient(105deg,#76965e,#a45f55)',
    ctaShadow: '0 10px 26px rgba(118,150,94,.34)',
  },
  xie_mingluan: {
    bg: '#190f12',
    coverBg: '#25171b',
    scrimGradient: 'linear-gradient(to top,#190f12 6%,rgba(25,15,18,.42) 42%,transparent 100%)',
    nameColor: '#eee3df',
    ageColor: '#aa8f89',
    taglineColor: '#d06464',
    chipActiveBg: 'rgba(200,82,82,.13)',
    chipActiveBorder: 'rgba(200,82,82,.38)',
    chipActiveText: '#df7777',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(199,164,98,.2)',
    chipInactiveText: '#b2a080',
    ctaGradient: 'linear-gradient(105deg,#b33d47,#9f783a)',
    ctaShadow: '0 10px 26px rgba(179,61,71,.38)',
  },
  qi_wang: {
    bg: '#101415',
    coverBg: '#182022',
    scrimGradient: 'linear-gradient(to top,#101415 6%,rgba(16,20,21,.4) 42%,transparent 100%)',
    nameColor: '#e8ebe7',
    ageColor: '#7d9794',
    taglineColor: '#cf6557',
    chipActiveBg: 'rgba(189,79,66,.13)',
    chipActiveBorder: 'rgba(189,79,66,.38)',
    chipActiveText: '#dc7569',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(110,163,158,.2)',
    chipInactiveText: '#8cadab',
    ctaGradient: 'linear-gradient(105deg,#a43d37,#4f817d)',
    ctaShadow: '0 10px 26px rgba(164,61,55,.36)',
  },
  yan_wujiu: {
    bg: '#130f10',
    coverBg: '#1f1919',
    scrimGradient: 'linear-gradient(to top,#130f10 6%,rgba(19,15,16,.42) 42%,transparent 100%)',
    nameColor: '#ebe7df',
    ageColor: '#978c78',
    taglineColor: '#d0544a',
    chipActiveBg: 'rgba(189,62,53,.13)',
    chipActiveBorder: 'rgba(189,62,53,.38)',
    chipActiveText: '#dd6b62',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(156,135,92,.2)',
    chipInactiveText: '#a89c81',
    ctaGradient: 'linear-gradient(105deg,#a83230,#796537)',
    ctaShadow: '0 10px 26px rgba(168,50,48,.38)',
  },
  li_yao: {
    bg: '#141217',
    coverBg: '#211d25',
    scrimGradient: 'linear-gradient(to top,#141217 6%,rgba(20,18,23,.4) 42%,transparent 100%)',
    nameColor: '#f0e8ee',
    ageColor: '#9c8c99',
    taglineColor: '#ef6c96',
    chipActiveBg: 'rgba(228,82,128,.13)',
    chipActiveBorder: 'rgba(228,82,128,.38)',
    chipActiveText: '#f07ba0',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(114,166,214,.2)',
    chipInactiveText: '#92acd0',
    ctaGradient: 'linear-gradient(105deg,#d84175,#537fb2)',
    ctaShadow: '0 10px 26px rgba(216,65,117,.38)',
  },
  tang_jingzhou: {
    bg: '#111318',
    coverBg: '#1a1e25',
    scrimGradient: 'linear-gradient(to top,#111318 6%,rgba(17,19,24,.4) 42%,transparent 100%)',
    nameColor: '#edf0f2',
    ageColor: '#89919d',
    taglineColor: '#f183aa',
    chipActiveBg: 'rgba(240,111,158,.13)',
    chipActiveBorder: 'rgba(240,111,158,.38)',
    chipActiveText: '#f695b7',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(104,200,188,.2)',
    chipInactiveText: '#83c5bd',
    ctaGradient: 'linear-gradient(105deg,#de5b8d,#3c9e94)',
    ctaShadow: '0 10px 26px rgba(222,91,141,.36)',
  },
  pei_zhaoye: {
    bg: '#101418',
    coverBg: '#182027',
    scrimGradient: 'linear-gradient(to top,#101418 6%,rgba(16,20,24,.4) 42%,transparent 100%)',
    nameColor: '#e8ecef',
    ageColor: '#82929c',
    taglineColor: '#74aabc',
    chipActiveBg: 'rgba(93,150,167,.14)',
    chipActiveBorder: 'rgba(93,150,167,.4)',
    chipActiveText: '#84b8c7',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(192,108,115,.2)',
    chipInactiveText: '#bd8e93',
    ctaGradient: 'linear-gradient(105deg,#4f8999,#a24f58)',
    ctaShadow: '0 10px 26px rgba(79,137,153,.36)',
  },
}

type Theme = { accent: string; deep: string; deep2: string; hero: string }
/** 按角色标签选主题（fallback，优先用 characterUIConfig）。 */
function pickTheme(tags: string[]): Theme {
  const s = tags.join(' ')
  if (/病娇|悬疑|危险|黑暗|禁忌|救赎|执念|偏执/.test(s))
    return { accent: '#B08A4F', deep: '#1b1420', deep2: '#0e0a11', hero: '#EDE3D4' }
  if (/霸总|占有|强势|追妻|热恋|独占|野性|禁欲/.test(s))
    return { accent: '#C9506A', deep: '#271521', deep2: '#150a0f', hero: '#F0DCE0' }
  return { accent: '#FF8FAB', deep: '#2a2029', deep2: '#191320', hero: '#F3E4EA' }
}

/**
 * 角色档案页 (Nimoo-style rich profile) at /character/:id.
 *
 * Full-bleed cover → 关于TA (tagline + tag chips + intimacy + gradient「和Ta聊天」)
 * → scroll into 叙引 card (archetype badge · name · accented one-liner · intro ·
 * personality axes). Per product direction: NO 评论 / 脉络 tabs. A share button
 * (top-right of the cover) copies the profile link for link-reachable
 * characters (public / unlisted+approved), so 「链接可见」 can actually spread.
 *
 * All copy comes from the public profile API, which deliberately never exposes
 * internal persona (core_wound / core_fear …). Missing fields degrade to
 * empty and simply don't render.
 */
export function CharacterProfilePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const safeBack = useSafeBack('/character')
  // Arriving straight from a creation flow (quick/workshop): the wizard is still
  // in the history stack, so a plain back would drop the user back into it.
  // Route them to the creation hub instead. See QuickConfirmPage / WorkshopCreatePage.
  const fromCreate = (location.state as { fromCreate?: boolean } | null)?.fromCreate === true
  const goBack = fromCreate ? () => navigate('/create', { replace: true }) : safeBack
  const { id = '' } = useParams<{ id: string }>()
  const setCharacter = useAppStore((s) => s.setCharacter)
  const companions = useCompanionsStore((s) => s.companions)
  const loadCompanions = useCompanionsStore((s) => s.load)
  const loadProfile = useCharactersStore((s) => s.loadProfile)
  const storeCharacters = useCharactersStore((s) => s.characters)
  const showToast = useToastStore((s) => s.show)
  const { toggle: toggleFavorite, has: isFavorite } = useFavoritesStore()

  // Seed synchronously from the store cache so a re-entry paints instantly with
  // no spinner (system covers/copy never change). A cold entry starts null and
  // fetches below.
  const [profile, setProfile] = useState<CharacterProfileDTO | null>(
    () => useCharactersStore.getState().profileById[id] ?? null,
  )
  const [error, setError] = useState(false)
  const [aboutExpanded, setAboutExpanded] = useState(false)
  // ji_yu 封面：默认只露上 3/4，点击展开看全图
  const [coverExpanded, setCoverExpanded] = useState(false)
  const [coverFullH, setCoverFullH] = useState(0)

  useEffect(() => {
    // Quick creation updates the catalog store, but the companion store may
    // still contain the pre-creation snapshot. Refresh it on every detail-page
    // entry so the new character's default relationship state is available.
    void loadCompanions(true)
  }, [loadCompanions])

  useEffect(() => {
    let alive = true
    const cached = useCharactersStore.getState().profileById[id]
    // Show cache immediately (or blank for a cold id); never flash a spinner
    // over already-good data.
    setProfile(cached ?? null)
    setError(false)
    loadProfile(id)
      .then((p) => {
        if (alive && p) setProfile(p)
        else if (alive && !p && !cached) setError(true)
      })
    return () => {
      alive = false
    }
  }, [id, loadProfile])

  const companion = useMemo(
    () => companions.find((c) => c.character_id === id),
    [companions, id],
  )
  const chatted = !!companion && companion.companion_status !== 'locked'
  // /api/companions intentionally returns a default STRANGER/0 relationship
  // for visible characters without a relationship_states row. Keep the UI
  // stable during the first fetch (and resilient to a temporarily empty
  // response) by rendering that same initial state locally.
  const relationshipStage = companion?.relationship_stage ?? 'STRANGER'
  const intimacy = companion?.intimacy ?? 0

  // 优先用角色专属 UI 配置(themе + 关系提示),缺省再退回按标签选色。
  const uiConfig = CHARACTER_UI_CONFIGS[id]
  const theme = useMemo<Theme>(
    () => (uiConfig?.theme as CharacterTheme) ?? pickTheme(profile?.tags ?? []),
    [uiConfig, profile?.tags],
  )
  const routeHint = uiConfig?.relationshipHints ?? {
    STRANGER: '第一次照面，你还只是个陌生人',
    FRIEND: '话变多了，Ta开始留意你的情绪',
    CONFIDANT: '有些话，Ta只想说给你听',
    ROMANTIC_INTEREST: '心跳藏不住了，关系差一步',
    LOVER: '你成了Ta生活里绕不开的人',
    BONDED: '再没有谁能替代此刻的彼此',
  }

  // Cover-less characters fall back to the shared background image (product
  // direction 2026-07-25) rather than a blurred avatar placeholder.
  const cover = profile?.cover_url || DEFAULT_COVER
  const hasRealCover = Boolean(profile?.cover_url)

  const openChat = () => {
    setCharacter(id)
    navigate(`/chat/${id}`)
  }

  // Shareability: a private character 404s for anyone but its owner, so never
  // offer a link for one. We only *know* the visibility for characters in the
  // caller's own catalog (own UGC + public). A character reached purely by link
  // that isn't in the store must be public/unlisted+approved to have loaded at
  // all — so default to shareable when the store has no row for it.
  const storeChar = useMemo(
    () => storeCharacters.find((c) => c.id === id),
    [storeCharacters, id],
  )
  const shareable = !storeChar || storeChar.visibility !== 'private'
  const approved = !storeChar || storeChar.is_builtin || storeChar.review_status === 'approved'

  async function handleShare() {
    const url = buildShareLink(id)
    try {
      await navigator.clipboard.writeText(url)
      showToast(
        approved ? '链接已复制，分享给好友即可访问' : '链接已复制，审核通过后好友即可访问',
        'success',
      )
    } catch {
      showToast(url, 'info')
    }
  }

  if (error) {
    return (
      <div className="relative w-full h-full flex flex-col items-center justify-center gap-3 bg-[var(--color-bg-page)]">
        <span className="text-[15px] text-[var(--color-text-secondary)]">角色不存在或已下架</span>
        <button
          onClick={() => navigate('/character')}
          className="h-[38px] px-5 rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] text-[14px] text-[var(--color-ink)]"
        >
          返回
        </button>
      </div>
    )
  }

  // 角色有 bespoke iframe 详情页则走 bespoke 分支，否则走 generic template
  const BespokeProfile = profile ? BESPOKE_PROFILES[id] : null

  // Batch 2: 配色三级链 - 内置硬编码 → UGC 自选 → 默认盘
  // 保持内置优先级在前，CHROME_PALETTES 命中时行为完全不变（零回归）
  const DEFAULT_PALETTE: ChromePalette = {
    bg: '#171019',
    coverBg: '#1B1320',
    scrimGradient: 'linear-gradient(to top,#171019 6%,rgba(23,16,25,.4) 40%,transparent 100%)',
    nameColor: '#ECE2E7',
    ageColor: '#B4A4AF',
    taglineColor: '#E08298',
    chipActiveBg: 'rgba(194,74,99,.08)',
    chipActiveBorder: 'rgba(194,74,99,.32)',
    chipActiveText: '#E08298',
    chipInactiveBg: 'rgba(255,255,255,.05)',
    chipInactiveBorder: 'rgba(255,255,255,.1)',
    chipInactiveText: '#B4A4AF',
    ctaGradient: 'linear-gradient(105deg,#C24A63,#9C3A55)',
    ctaShadow: '0 10px 26px rgba(194,74,99,0.32)',
  }
  const chrome = CHROME_PALETTES[id] ?? profile?.ui_chrome ?? DEFAULT_PALETTE

  if (profile && BespokeProfile && CHROME_PALETTES[id]) {
    return (
      <div className="relative w-full h-full overflow-y-auto" style={{ background: chrome.bg }}>
        {/* ── 封面 hero（默认露上 3/4，点击展开全图）── */}
        <div
          className="relative w-full overflow-hidden cursor-pointer"
          style={{
            background: chrome.coverBg,
            height: coverFullH ? (coverExpanded ? coverFullH : Math.round(coverFullH * 0.75)) : undefined,
            transition: 'height .38s cubic-bezier(.4,0,.2,1)'
          }}
          onClick={() => coverFullH && setCoverExpanded((v) => !v)}
          role="button"
          aria-label={coverExpanded ? '收起封面' : '展开完整封面'}
        >
          {profile.cover_url && (
            <img
              src={profile.cover_url}
              alt={profile.display_name || '季屿'}
              className="block w-full h-auto"
              ref={(el) => {
                if (el && el.complete && el.offsetHeight) setCoverFullH(el.offsetHeight)
              }}
              onLoad={(e) => setCoverFullH(e.currentTarget.offsetHeight)}
            />
          )}
          <div className="absolute inset-x-0 bottom-0 h-[45%] pointer-events-none" style={{ background: chrome.scrimGradient }} />
          {coverFullH > 0 && (
            <div className="absolute bottom-3 right-3 z-10 text-[11px] text-white/70 bg-black/35 backdrop-blur-[6px] rounded-full px-3 py-1 pointer-events-none">
              {coverExpanded ? '收起' : '点击看全图'}
            </div>
          )}
          <button onClick={goBack} aria-label="返回" className="absolute left-4 z-10 w-[38px] h-[38px] rounded-full bg-black/30 backdrop-blur-[8px] flex items-center justify-center active:scale-[0.95] transition-transform" style={{ top: 'calc(var(--safe-top) + 8px)' }}>
            <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="10,2 2,10 10,18" /></svg>
          </button>
          {shareable && (
            <button onClick={handleShare} aria-label="分享角色" className="absolute right-4 z-10 w-[38px] h-[38px] rounded-full bg-black/30 backdrop-blur-[8px] flex items-center justify-center active:scale-[0.95] transition-transform" style={{ top: 'calc(var(--safe-top) + 8px)' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><line x1="8.59" y1="13.51" x2="15.42" y2="17.49" /><line x1="15.41" y1="6.51" x2="8.59" y2="10.49" /></svg>
            </button>
          )}
        </div>

        {/* 名字块 */}
        <div className="relative -mt-[50px] px-[22px] z-[3]">
          <h1 className="text-[34px] font-semibold leading-[1.1]" style={{ fontFamily: '"Songti SC","STSong","Noto Serif SC",Georgia,serif', color: chrome.nameColor }}>
            {profile.display_name || '季屿'}
            {profile.age_range && <span className="text-[12px] ml-2.5 align-middle" style={{ color: chrome.ageColor }}>{profile.age_range}</span>}
          </h1>
          {profile.tagline && <p className="text-[16px] mt-2.5 leading-[1.7] italic" style={{ fontFamily: '"Songti SC","STSong","Noto Serif SC",Georgia,serif', color: chrome.taglineColor }}>{profile.tagline}</p>}
          {profile.tags.length > 0 && (
            <div className="flex flex-wrap gap-[7px] mt-3.5">
              {profile.tags.slice(0, 6).map((t, i) => (
                <span
                  key={t}
                  className="text-[12px] px-3 py-[5px] rounded-full border"
                  style={i < 2
                    ? { color: chrome.chipActiveText, borderColor: chrome.chipActiveBorder, background: chrome.chipActiveBg }
                    : { color: chrome.chipInactiveText, borderColor: chrome.chipInactiveBorder, background: chrome.chipInactiveBg }
                  }
                >{t}</span>
              ))}
            </div>
          )}
        </div>

        {/* 动态 CTA（收藏 + 亲密度 + 开始聊天）——封面下方，nimoo 式内联 */}
        <div className="px-[22px] mt-5">
          <div className="flex items-center gap-3">
            {profile && (
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between text-[12px] text-[#B4A4AF]">
                  <span>
                    {isColdWar(relationshipStage)
                      ? '闹别扭'
                      : stageWithIntimacy(relationshipStage, intimacy)}
                  </span>
                </div>
                <div className="mt-1.5 h-[6px] w-full rounded-full bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[#C24A63]"
                    style={{ width: `${intimacyPercent(intimacy)}%` }}
                  />
                </div>
              </div>
            )}
            <button
              onClick={() => toggleFavorite(id)}
              className="shrink-0 w-[48px] h-[48px] rounded-full bg-white/5 border border-white/10 flex items-center justify-center active:scale-[0.96] transition-transform"
              aria-label={isFavorite(id) ? '取消收藏' : '收藏'}
            >
              {isFavorite(id) ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="#FF6B9D" stroke="#FF6B9D" strokeWidth="1.5">
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ECE2E7" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                </svg>
              )}
            </button>
            <button
              onClick={openChat}
              className={`h-[48px] rounded-full text-white text-[16px] font-semibold active:scale-[0.97] transition-transform ${
                chatted ? 'px-7' : 'flex-1'
              }`}
              style={{
                background: chrome.ctaGradient,
                boxShadow: chrome.ctaShadow,
              }}
            >
              和 Ta 聊天
            </button>
          </div>
        </div>

        {/* bespoke 叙事内容（iframe） */}
        <div className="mt-6">
          <BespokeProfile profile={profile} />
        </div>
      </div>
    )
  }

  // 高级 HTML 模式：创作者已自排详情页，系统不再叠加模板化的「关于TA / 叙引」
  // 内容块（职责重叠会视觉割裂）。「关系路线」是玩法组件（聊过才出现、承载关系
  // 进度），与 HTML 排版不冲突，保留。
  const hasCustomHtml = !!(profile && profile.custom_html && profile.custom_html.trim())

  return (
    <div
      className="relative w-full h-full overflow-y-auto bg-[var(--color-bg-page)]"
      style={
        {
          '--chrome-bg': chrome.bg,
          '--chrome-name-color': chrome.nameColor,
          '--chrome-age-color': chrome.ageColor,
          '--chrome-tagline-color': chrome.taglineColor,
          '--chrome-cta-gradient': chrome.ctaGradient,
          '--chrome-cta-shadow': chrome.ctaShadow,
          '--chrome-chip-active-bg': chrome.chipActiveBg,
          '--chrome-chip-active-border': chrome.chipActiveBorder,
          '--chrome-chip-active-text': chrome.chipActiveText,
          '--chrome-chip-inactive-bg': chrome.chipInactiveBg,
          '--chrome-chip-inactive-border': chrome.chipInactiveBorder,
          '--chrome-chip-inactive-text': chrome.chipInactiveText,
        } as React.CSSProperties
      }
    >
      {/* ── Cover ── 有真实封面时：默认露上 3/4，点击展开全图（对齐内置角色）；
          无封面回退到共享背景图时保持固定高度裁切。 */}
      <div
        className="relative w-full overflow-hidden"
        style={
          hasRealCover
            ? {
                height: coverFullH ? (coverExpanded ? coverFullH : Math.round(coverFullH * 0.75)) : undefined,
                transition: 'height .38s cubic-bezier(.4,0,.2,1)',
                cursor: coverFullH ? 'pointer' : undefined,
              }
            : undefined
        }
        onClick={hasRealCover ? () => coverFullH && setCoverExpanded((v) => !v) : undefined}
        role={hasRealCover ? 'button' : undefined}
        aria-label={hasRealCover ? (coverExpanded ? '收起封面' : '展开完整封面') : undefined}
      >
        {hasRealCover ? (
          <img
            src={cover}
            alt={profile?.display_name ?? ''}
            className="block w-full h-auto"
            ref={(el) => {
              if (el && el.complete && el.offsetHeight) setCoverFullH(el.offsetHeight)
            }}
            onLoad={(e) => setCoverFullH(e.currentTarget.offsetHeight)}
          />
        ) : (
          <div className="relative w-full h-[62vh] min-h-[380px]">
            <img src={cover} alt={profile?.display_name ?? ''} className="absolute inset-0 w-full h-full object-cover" />
          </div>
        )}
        {/* bottom fade into the sheet below */}
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[var(--color-bg-page)] via-[var(--color-bg-page)]/40 to-transparent pointer-events-none" />

        {hasRealCover && coverFullH > 0 && (
          <div className="absolute bottom-3 right-3 z-10 text-[11px] text-white/70 bg-black/35 backdrop-blur-[6px] rounded-full px-3 py-1 pointer-events-none">
            {coverExpanded ? '收起' : '点击看全图'}
          </div>
        )}

        {/* back + share buttons */}
        <div className="absolute left-0 top-0 z-10" style={{ height: 'var(--safe-top)' }} />
        <button
          onClick={(e) => { e.stopPropagation(); goBack() }}
          aria-label="返回"
          className="absolute left-4 z-10 w-[38px] h-[38px] rounded-full bg-black/30 backdrop-blur-[8px] flex items-center justify-center active:scale-[0.95] transition-transform"
          style={{ top: 'calc(var(--safe-top) + 8px)' }}
        >
          <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="10,2 2,10 10,18" />
          </svg>
        </button>
        {/* Share button — only for link-reachable characters (never private). */}
        {profile && shareable && (
          <button
            onClick={(e) => { e.stopPropagation(); handleShare() }}
            aria-label="分享角色"
            className="absolute right-4 z-10 w-[38px] h-[38px] rounded-full bg-black/30 backdrop-blur-[8px] flex items-center justify-center active:scale-[0.95] transition-transform"
            style={{ top: 'calc(var(--safe-top) + 8px)' }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3" />
              <circle cx="6" cy="12" r="3" />
              <circle cx="18" cy="19" r="3" />
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
            </svg>
          </button>
        )}
      </div>

      {/* ── 关于TA ── */}
      <div className="relative -mt-14 px-5 pb-4">
        <h1 className="text-[26px] font-bold leading-tight" style={{ color: chrome.nameColor }}>
          {profile?.display_name ?? '　'}
        </h1>
        {profile?.creator_name && (
          <p className="mt-1 text-[12px] text-[var(--color-text-muted)]">by @{profile.creator_name}</p>
        )}

        {profile?.age_range && (
          <span
            className="mt-2 inline-flex h-[24px] items-center rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] px-3 text-[12px] font-medium tabular-nums"
            style={{ color: chrome.ageColor }}
          >
            {profile.age_range} 岁
          </span>
        )}

        {profile?.tagline && (
          <p className="mt-3 text-[15px] leading-relaxed" style={{ color: chrome.taglineColor }}>
            {profile.tagline}
          </p>
        )}

        {profile && profile.tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {profile.tags.map((t) => (
              <span
                key={t}
                className="h-[26px] px-3 inline-flex items-center rounded-full text-[12px]"
                style={{
                  backgroundColor: chrome.chipInactiveBg,
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  borderColor: chrome.chipInactiveBorder,
                  color: chrome.chipInactiveText,
                }}
              >
                {t}
              </span>
            ))}
          </div>
        )}

        {/* intimacy + chat CTA */}
        <div className="mt-5 flex items-center gap-3">
          {profile && (
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between text-[12px] text-[var(--color-text-secondary)]">
                <span>
                  {isColdWar(relationshipStage)
                    ? '闹别扭'
                    : stageWithIntimacy(relationshipStage, intimacy)}
                </span>
              </div>
              <div className="mt-1.5 h-[6px] w-full rounded-full bg-[var(--color-glass-55)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--color-primary)]"
                  style={{ width: `${intimacyPercent(intimacy)}%` }}
                />
              </div>
            </div>
          )}
          {/* Favorite button — heart icon, left of 开始聊天 */}
          <button
            onClick={() => toggleFavorite(id)}
            className="shrink-0 w-[48px] h-[48px] rounded-full bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] flex items-center justify-center active:scale-[0.96] transition-transform"
            aria-label={isFavorite(id) ? '取消收藏' : '收藏'}
          >
            {isFavorite(id) ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="#FF6B9D" stroke="#FF6B9D" strokeWidth="1.5">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-ink)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
              </svg>
            )}
          </button>
          <button
            onClick={openChat}
            style={{
              background: chrome.ctaGradient,
              boxShadow: chrome.ctaShadow,
            }}
            className={`h-[48px] rounded-full text-white text-[16px] font-semibold active:scale-[0.97] transition-transform ${
              chatted ? 'px-7' : 'flex-1'
            }`}
          >
            开始聊天
          </button>
        </div>

        {/* 关于TA card — truncated intro（高级 HTML 模式下隐藏，交给创作者自排） */}
        {!hasCustomHtml && profile?.intro && (
          <div className="mt-5 rounded-[20px] bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] p-4">
            <div className="flex items-center gap-2 text-[13px] font-semibold" style={{ color: theme.accent }}>
              <span className="inline-block w-[3px] h-[14px] rounded-full" style={{ background: theme.accent }} />
              关于TA
            </div>
            <p
              className={`mt-3 text-[14px] leading-relaxed text-[var(--color-text-secondary)] whitespace-pre-wrap ${
                !aboutExpanded && 'line-clamp-4'
              }`}
            >
              {profile.intro}
            </p>
            {profile.intro.length > 120 && (
              <button
                onClick={() => setAboutExpanded((p) => !p)}
                className="mt-2 text-[13px] font-medium active:scale-[0.96] transition-transform"
                style={{ color: theme.accent }}
              >
                {aboutExpanded ? '收起' : '更多'}
              </button>
            )}
          </div>
        )}

        {/* UGC 详情页自定义区 —— 有 custom_html 优先，否则渲染 profile_blocks（批 6 互斥） */}
        {profile && profile.custom_html && profile.custom_html.trim() ? (
          <div className="mt-6 rounded-[20px] overflow-hidden bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] p-2">
            <CustomHtmlRenderer
              html={profile.custom_html}
              chrome={chrome}
              trustedEmbeddedStyles={profile.source === 'built_in'}
            />
          </div>
        ) : (
          profile && profile.profile_blocks && profile.profile_blocks.length > 0 && (
            <div className="mt-6 rounded-[20px] bg-[var(--color-glass-55)] border border-[var(--color-border-glass)] p-5">
              <BlockRenderer blocks={profile.profile_blocks} chrome={chrome} />
            </div>
          )
        )}

        {/* 关系路线 timeline — 6 nodes with current stage highlighted */}
        {chatted && companion && !isColdWar(companion.relationship_stage) && (
          <div className="mt-5 rounded-[20px] bg-[var(--color-glass-75)] border border-[var(--color-border-glass)] p-4">
            <div className="flex items-center gap-2 text-[13px] font-semibold" style={{ color: theme.accent }}>
              <span className="inline-block w-[3px] h-[14px] rounded-full" style={{ background: theme.accent }} />
              关系路线
            </div>
            <div className="mt-4 relative">
              {/* Progress connector line */}
              <div className="absolute top-[18px] left-[18px] right-[18px] h-[2px] bg-[var(--color-glass-55)]">
                <div
                  className="h-full transition-[width] duration-300"
                  style={{
                    width: `${(Math.max(0, stageOrderIndex(companion.relationship_stage)) / (ROUTE_NODES.length - 1)) * 100}%`,
                    background: theme.accent,
                  }}
                />
              </div>
              {/* Stage nodes */}
              <div className="relative flex justify-between">
                {ROUTE_NODES.map((stage, idx) => {
                  const reached = stageOrderIndex(companion.relationship_stage) >= idx
                  const isCurrent = companion.relationship_stage === stage || (stage === 'FRIEND' && companion.relationship_stage === 'ACQUAINTANCE')
                  return (
                    <div key={stage} className="flex flex-col items-center w-[60px]">
                      <div
                        className={`w-[36px] h-[36px] rounded-full flex items-center justify-center text-[13px] font-semibold transition-[background,color,box-shadow] duration-300 ${
                          isCurrent ? 'shadow-[0_0_12px_rgba(255,255,255,0.3)]' : ''
                        }`}
                        style={{
                          background: reached ? theme.accent : 'var(--color-glass-55)',
                          color: reached ? '#fff' : 'var(--color-text-muted)',
                        }}
                      >
                        {idx + 1}
                      </div>
                      <span className="mt-2 text-[12px] text-center leading-tight text-[var(--color-text-secondary)]">
                        {stageLabel(stage)}
                      </span>
                      {isCurrent && (
                        <span className="mt-1 text-[11px] text-center text-[var(--color-text-muted)] leading-snug">
                          {routeHint[stage as keyof typeof routeHint]}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── 叙引 dossier card (premium dark)（高级 HTML 模式下隐藏，交给创作者自排） ── */}
      {!hasCustomHtml && profile && (profile.one_liner || profile.archetype_label || profile.age_range || profile.tags.length > 0) && (
        <div
          className="mx-4 mb-4 rounded-[22px] border p-6 relative overflow-hidden"
          style={{
            background: `linear-gradient(135deg, ${theme.deep} 0%, ${theme.deep2} 100%)`,
            borderColor: theme.accent + '40',
          }}
        >
          {/* 叙引 header */}
          <div className="flex items-center gap-2 text-[13px] font-semibold" style={{ color: theme.accent }}>
            <span className="inline-block w-[3px] h-[14px] rounded-full" style={{ background: theme.accent }} />
            叙引
          </div>

          {/* Hero one-liner */}
          {profile.one_liner && (
            <div className="mt-5 flex gap-3">
              <span
                className="mt-1 shrink-0 w-[3px] self-stretch rounded-full"
                style={{ background: `linear-gradient(to bottom, ${theme.accent}, ${theme.accent}80)` }}
              />
              <p
                className="text-[18px] leading-relaxed font-serif"
                style={{ color: theme.hero, fontFamily: '"Songti SC", "Noto Serif SC", serif' }}
              >
                {profile.one_liner}
              </p>
            </div>
          )}

          {/* Identity namecard */}
          {(profile.archetype_label || profile.age_range || profile.tags.length > 0) && (
            <div className="mt-5 rounded-[16px] bg-white/5 border border-white/10 p-4">
              <div className="text-[12px] font-medium mb-3" style={{ color: theme.accent }}>
                身份档案
              </div>
              <div className="flex flex-wrap gap-2">
                {profile.archetype_label && (
                  <span
                    className="inline-flex h-[26px] items-center rounded-full px-3 text-[12px] font-medium"
                    style={{ background: theme.accent + '20', color: theme.accent }}
                  >
                    {profile.archetype_label}
                  </span>
                )}
                {profile.age_range && (
                  <span
                    className="inline-flex h-[26px] items-center rounded-full px-3 text-[12px] font-medium tabular-nums"
                    style={{ background: 'rgba(255,255,255,0.08)', color: '#D4C7BA' }}
                  >
                    {profile.age_range} 岁
                  </span>
                )}
                {profile.tags.slice(0, 3).map((t) => (
                  <span
                    key={t}
                    className="inline-flex h-[26px] items-center rounded-full px-3 text-[12px]"
                    style={{ background: 'rgba(255,255,255,0.08)', color: '#D4C7BA' }}
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 性格占比展示已按产品要求移除（用户不感兴趣） */}
        </div>
      )}


      <div style={{ height: 'var(--safe-bottom)' }} />
    </div>
  )
}
