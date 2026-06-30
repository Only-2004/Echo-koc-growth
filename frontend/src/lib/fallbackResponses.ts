/**
 * T42: 前端 fallback 响应注册表
 *
 * 当后端 LLM 不可用时，提供按 scene 索引的兜底文案。
 * 与后端 backend/agents/_fallback/responses.json 对齐。
 */

import type { SourceTag } from '../types/agents'

export interface FallbackMessage {
  text: string
  sources: SourceTag[]
  suggestions?: string[]
}

const fallbackByScene: Record<string, FallbackMessage> = {
  home: {
    text: '欢迎回来！你的账号最近表现不错。今天想做什么？可以继续选题、复盘新视频，或者看看画像更新。\n\n[数据驱动]',
    sources: ['数据驱动'],
    suggestions: ['帮我选下一个题', '复盘最近的视频', '看看我的画像'],
  },
  onboard: {
    text: '我正在分析你的账号数据。请继续回答我的问题，帮助我建立你的 KOC 画像。\n\n[数据驱动]',
    sources: ['数据驱动'],
    suggestions: ['继续对话', '跳过这一步'],
  },
  profile: {
    text: '你的画像正在不断完善中。目前确定项、个性化项和待探索项都有了初步内容。想展开聊聊哪个方向？\n\n[画像驱动]',
    sources: ['画像驱动'],
    suggestions: ['展开待探索项', '更新画像', '回到首页'],
  },
  ideate: {
    text: '基于你当前的画像，我建议优先做和「考研生活」相关的美食内容——这个方向既有受众基础，又有差异化空间。\n\n[画像驱动]',
    sources: ['画像驱动'],
    suggestions: ['帮我评估一个选题', '看看趋势数据', '回到首页'],
  },
  retro: {
    text: '从最近的复盘来看，你的核心发现是：食堂实拍内容的留存率最高，考研相关的互动率最高。建议下一条内容把这两个元素结合起来。\n\n[数据驱动]',
    sources: ['数据驱动'],
    suggestions: ['深入分析留存', '看看受众变化', '开始下一个选题'],
  },
}

/**
 * 按 scene 获取 fallback 响应。
 * 找不到时返回通用兜底。
 */
export function getFallbackForScene(scene: string): FallbackMessage {
  return (
    fallbackByScene[scene] ?? {
      text: '抱歉，AI 服务暂时不可用，请稍后再试。\n\n[数据驱动]',
      sources: ['数据驱动'] as SourceTag[],
      suggestions: ['重试', '回到首页'],
    }
  )
}
