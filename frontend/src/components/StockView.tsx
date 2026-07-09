import type { Overview, PricePoint } from '../types'
import {
  investorName,
  toFixed,
  toInt,
  toPct,
  toReadable,
  trendClass,
} from '../format'
import KLineChart from './KLineChart'

interface Props {
  overview: Overview
  series: PricePoint[]
}

export default function StockView({ overview, series }: Props) {
  return (
    <div className="stock-view">
      <PriceHeader overview={overview} />
      <div className="cards">
        <TechnicalCard overview={overview} series={series} />
        <FundamentalCard overview={overview} />
        <ChipsCard overview={overview} />
        <NewsCard overview={overview} />
      </div>
    </div>
  )
}

function PriceHeader({ overview }: { overview: Overview }) {
  const t = overview.technical
  const cls = trendClass(t.change)
  return (
    <div className="price-header">
      <div className="title">
        <h1>{overview.stock_name ?? overview.stock_id}</h1>
        <span className="code-badge">{overview.stock_id}</span>
        {overview.industry_category && <span className="industry-badge">{overview.industry_category}</span>}
      </div>
      {t.available ? (
        <div className={`quote ${cls}`}>
          <span className="close">{toFixed(t.close)}</span>
          <span className="change">
            {toFixed(t.change)} ({toPct(t.change_pct)})
          </span>
          <span className="asof">{t.date}</span>
        </div>
      ) : (
        <div className="quote flat">無報價資料</div>
      )}
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <h2 className="card-title">{title}</h2>
      {children}
    </section>
  )
}

function Stat({ label, value, cls }: { label: string; value: string; cls?: string }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className={`stat-value ${cls ?? ''}`}>{value}</span>
    </div>
  )
}

function TechnicalCard({ overview, series }: { overview: Overview; series: PricePoint[] }) {
  const t = overview.technical
  return (
    <Card title="技術面">
      {t.available ? (
        <>
          <div className="stat-grid">
            <Stat label="開盤" value={toFixed(t.open)} />
            <Stat label="最高" value={toFixed(t.high)} />
            <Stat label="最低" value={toFixed(t.low)} />
            <Stat label="成交量(股)" value={toInt(t.volume)} />
            <Stat label="MA5" value={toFixed(t.ma5)} />
            <Stat label="MA20" value={toFixed(t.ma20)} />
            <Stat label="MA60" value={toFixed(t.ma60)} />
          </div>
          {series.length > 0 ? (
            <KLineChart series={series} />
          ) : (
            <p className="empty">無K線資料</p>
          )}
        </>
      ) : (
        <p className="empty">無技術面資料</p>
      )}
    </Card>
  )
}

function FundamentalCard({ overview }: { overview: Overview }) {
  const { month_revenue: rev, valuation: val, eps } = overview.fundamental
  return (
    <Card title="基本面">
      <h3 className="sub">月營收</h3>
      {rev.available ? (
        <div className="stat-grid">
          <Stat label={`${rev.year}/${rev.month} 營收`} value={toReadable(rev.revenue)} />
          <Stat label="年增(YoY)" value={toPct(rev.yoy_pct)} cls={trendClass(rev.yoy_pct)} />
          <Stat label="月增(MoM)" value={toPct(rev.mom_pct)} cls={trendClass(rev.mom_pct)} />
        </div>
      ) : (
        <p className="empty">無月營收資料</p>
      )}
      <h3 className="sub">估值</h3>
      {val.available ? (
        <div className="stat-grid">
          <Stat label="本益比(PER)" value={toFixed(val.per)} />
          <Stat label="股價淨值比(PBR)" value={toFixed(val.pbr)} />
          <Stat label="殖利率" value={toPct(val.dividend_yield)} />
          {eps.available && <Stat label={`EPS (${eps.date})`} value={toFixed(eps.eps)} />}
        </div>
      ) : (
        <p className="empty">無估值資料</p>
      )}
    </Card>
  )
}

function ChipsCard({ overview }: { overview: Overview }) {
  const { institutional: inst, margin } = overview.chips
  return (
    <Card title="籌碼面">
      <h3 className="sub">三大法人買賣超（{inst.date ?? '—'}，單位：股）</h3>
      {inst.available && inst.by_investor ? (
        <div className="stat-grid">
          {Object.entries(inst.by_investor).map(([k, v]) => (
            <Stat key={k} label={investorName(k)} value={toInt(v)} cls={trendClass(v)} />
          ))}
          <Stat label="合計" value={toInt(inst.total_net_shares)} cls={trendClass(inst.total_net_shares)} />
        </div>
      ) : (
        <p className="empty">無法人資料</p>
      )}
      <h3 className="sub">融資融券（{margin.date ?? '—'}）</h3>
      {margin.available ? (
        <div className="stat-grid">
          <Stat label="融資餘額(張)" value={toInt(margin.margin_balance)} />
          <Stat label="融券餘額(張)" value={toInt(margin.short_balance)} />
        </div>
      ) : (
        <p className="empty">無融資券資料</p>
      )}
    </Card>
  )
}

function NewsCard({ overview }: { overview: Overview }) {
  return (
    <Card title="消息面">
      {overview.news.length > 0 ? (
        <ul className="news-list">
          {overview.news.map((n, i) => (
            <li key={i}>
              <a href={n.link} target="_blank" rel="noreferrer">
                {n.title}
              </a>
              <span className="news-meta">
                {n.source ?? ''} · {n.date}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">近期無相關新聞</p>
      )}
    </Card>
  )
}
