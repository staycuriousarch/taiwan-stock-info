// 數字格式化工具（台股慣用單位）

/** 大數字轉億/萬（用於營收、餘額）。 */
export function toReadable(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  const abs = Math.abs(n)
  if (abs >= 1e8) return `${(n / 1e8).toFixed(2)} 億`
  if (abs >= 1e4) return `${(n / 1e4).toFixed(1)} 萬`
  return n.toLocaleString('zh-TW')
}

/** 千分位整數（張數、成交量）。 */
export function toInt(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  return Math.round(n).toLocaleString('zh-TW')
}

/** 一般數值，保留位數。 */
export function toFixed(n: number | null | undefined, digits = 2): string {
  if (n == null || Number.isNaN(n)) return '—'
  return n.toFixed(digits)
}

/** 百分比（帶正負號）。 */
export function toPct(n: number | null | undefined, digits = 2): string {
  if (n == null || Number.isNaN(n)) return '—'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(digits)}%`
}

/** 台股慣例：紅漲綠跌。回傳 CSS class 名稱。 */
export function trendClass(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n) || n === 0) return 'flat'
  return n > 0 ? 'up' : 'down'
}

/** 三大法人英文代號 → 中文。 */
const INVESTOR_NAMES: Record<string, string> = {
  Foreign_Investor: '外資',
  Foreign_Dealer_Self: '外資自營',
  Investment_Trust: '投信',
  Dealer_self: '自營商(自行)',
  Dealer_Hedging: '自營商(避險)',
  Dealer: '自營商',
}

export function investorName(key: string): string {
  return INVESTOR_NAMES[key] ?? key
}
