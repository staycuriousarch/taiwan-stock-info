import { useEffect, useRef } from 'react'
import {
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createChart,
  type IChartApi,
  type UTCTimestamp,
} from 'lightweight-charts'
import type { PricePoint } from '../types'

// 台股慣例：紅漲綠跌
const UP = '#d93a3a'
const DOWN = '#12a150'

interface Props {
  series: PricePoint[]
}

export default function KLineChart({ series }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el || series.length === 0) return

    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { color: 'transparent' },
        textColor: '#4b5563',
        fontFamily: 'inherit',
      },
      grid: {
        vertLines: { color: 'rgba(0,0,0,0.05)' },
        horzLines: { color: 'rgba(0,0,0,0.05)' },
      },
      rightPriceScale: { borderColor: 'rgba(0,0,0,0.1)' },
      timeScale: { borderColor: 'rgba(0,0,0,0.1)', timeVisible: false },
      crosshair: { mode: 0 },
    })
    chartRef.current = chart

    const toTime = (d: string) => (d.slice(0, 10) as unknown) as UTCTimestamp

    // K 線
    const candle = chart.addSeries(CandlestickSeries, {
      upColor: UP,
      downColor: DOWN,
      borderUpColor: UP,
      borderDownColor: DOWN,
      wickUpColor: UP,
      wickDownColor: DOWN,
    })
    candle.setData(
      series.map((p) => ({
        time: toTime(p.date),
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      })),
    )

    // 均線
    const maConfigs: { key: keyof PricePoint; color: string; title: string }[] = [
      { key: 'ma5', color: '#f59e0b', title: 'MA5' },
      { key: 'ma20', color: '#3b82f6', title: 'MA20' },
      { key: 'ma60', color: '#a855f7', title: 'MA60' },
    ]
    for (const cfg of maConfigs) {
      const line = chart.addSeries(LineSeries, {
        color: cfg.color,
        lineWidth: 1,
        title: cfg.title,
        priceLineVisible: false,
        lastValueVisible: false,
      })
      line.setData(
        series
          .filter((p) => p[cfg.key] != null)
          .map((p) => ({ time: toTime(p.date), value: p[cfg.key] as number })),
      )
    }

    // 成交量（底部疊圖）
    const volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    })
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })
    volume.setData(
      series.map((p) => ({
        time: toTime(p.date),
        value: p.volume,
        color: p.close >= p.open ? 'rgba(217,58,58,0.4)' : 'rgba(18,161,80,0.4)',
      })),
    )

    chart.timeScale().fitContent()

    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [series])

  return <div className="kline-chart" ref={containerRef} />
}
