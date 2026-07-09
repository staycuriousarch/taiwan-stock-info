import { useEffect, useRef, useState } from 'react'
import { searchStocks } from '../api/client'
import type { StockSearchResult } from '../types'

interface Props {
  onSelect: (stock: StockSearchResult) => void
}

export default function SearchBar({ onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StockSearchResult[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const boxRef = useRef<HTMLDivElement>(null)

  // debounce 查詢
  useEffect(() => {
    const q = query.trim()
    if (!q) {
      setResults([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const data = await searchStocks(q)
        setResults(data.results)
        setOpen(true)
        setActive(0)
      } catch {
        setResults([])
      }
    }, 250)
    return () => clearTimeout(timer)
  }, [query])

  // 點擊外部關閉下拉
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  function choose(stock: StockSearchResult) {
    onSelect(stock)
    setQuery(`${stock.stock_id} ${stock.stock_name}`)
    setOpen(false)
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || results.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => Math.min(a + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(a - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      choose(results[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="searchbar" ref={boxRef}>
      <input
        className="search-input"
        type="text"
        placeholder="輸入股票代碼或公司名稱，例如 2330 或 台積電"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length && setOpen(true)}
        onKeyDown={onKeyDown}
        autoFocus
      />
      {open && results.length > 0 && (
        <ul className="search-dropdown">
          {results.map((s, i) => (
            <li
              key={`${s.stock_id}-${i}`}
              className={i === active ? 'active' : ''}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => {
                e.preventDefault()
                choose(s)
              }}
            >
              <span className="code">{s.stock_id}</span>
              <span className="name">{s.stock_name}</span>
              {s.industry_category && <span className="industry">{s.industry_category}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
