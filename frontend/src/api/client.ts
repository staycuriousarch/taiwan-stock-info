// 呼叫後端 API。開發時透過 Vite proxy 代理 /api → FastAPI(127.0.0.1:8000)
import type { Overview, PricePoint, StockSearchResult, TechnicalSummary } from '../types'

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export function searchStocks(q: string): Promise<{ query: string; results: StockSearchResult[] }> {
  return getJSON(`/api/search?q=${encodeURIComponent(q)}`)
}

export function getOverview(stockId: string): Promise<Overview> {
  return getJSON(`/api/stock/${encodeURIComponent(stockId)}/overview`)
}

export function getTechnical(
  stockId: string,
): Promise<{ summary: TechnicalSummary; series: PricePoint[] }> {
  return getJSON(`/api/stock/${encodeURIComponent(stockId)}/technical`)
}
