import { useState } from 'react'
import SearchBar from './components/SearchBar'
import StockView from './components/StockView'
import { getOverview, getTechnical } from './api/client'
import type { Overview, PricePoint, StockSearchResult } from './types'

export default function App() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [series, setSeries] = useState<PricePoint[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSelect(stock: StockSearchResult) {
    setLoading(true)
    setError(null)
    try {
      // 同時抓四面向摘要與 K 線序列
      const [ov, tech] = await Promise.all([
        getOverview(stock.stock_id),
        getTechnical(stock.stock_id),
      ])
      setOverview(ov)
      setSeries(tech.series)
    } catch (e) {
      setError(e instanceof Error ? e.message : '查詢失敗')
      setOverview(null)
      setSeries([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="brand">📈 台股資訊查詢</h1>
        <SearchBar onSelect={handleSelect} />
      </header>

      <main className="app-main">
        {loading && <div className="status">查詢中…</div>}
        {error && <div className="status error">⚠ {error}</div>}
        {!loading && !error && !overview && (
          <div className="status hint">輸入股票代碼或公司名稱開始查詢，例如 2330、台積電、鴻海</div>
        )}
        {!loading && overview && <StockView overview={overview} series={series} />}
      </main>

      <footer className="app-footer">
        資料來源：FinMind · 僅供參考，不構成投資建議
      </footer>
    </div>
  )
}
