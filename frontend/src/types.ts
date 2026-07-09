// 對應後端 FastAPI 的回傳結構

export interface StockSearchResult {
  stock_id: string
  stock_name: string
  industry_category?: string
  type?: string
}

export interface MonthRevenue {
  available: boolean
  year?: number
  month?: number
  revenue?: number
  yoy_pct?: number | null
  mom_pct?: number | null
}

export interface Valuation {
  available: boolean
  date?: string
  per?: number | null
  pbr?: number | null
  dividend_yield?: number | null
}

export interface Eps {
  available: boolean
  date?: string
  eps?: number
}

export interface Fundamental {
  month_revenue: MonthRevenue
  valuation: Valuation
  eps: Eps
}

export interface TechnicalSummary {
  available: boolean
  date?: string
  close?: number
  open?: number
  high?: number
  low?: number
  change?: number | null
  change_pct?: number | null
  volume?: number
  ma5?: number | null
  ma20?: number | null
  ma60?: number | null
}

export interface PricePoint {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  ma5?: number | null
  ma20?: number | null
  ma60?: number | null
}

export interface Institutional {
  available: boolean
  date?: string
  total_net_shares?: number
  by_investor?: Record<string, number>
}

export interface Margin {
  available: boolean
  date?: string
  margin_balance?: number | null
  short_balance?: number | null
}

export interface Chips {
  institutional: Institutional
  margin: Margin
}

export interface NewsItem {
  date: string
  title: string
  source?: string
  link?: string
  description?: string | null
}

export interface Overview {
  stock_id: string
  stock_name?: string
  industry_category?: string
  fundamental: Fundamental
  technical: TechnicalSummary
  chips: Chips
  news: NewsItem[]
}
