// RISA page 1 (Common Operational Picture), laid out in mm for A3 or A4 landscape.
// The worker opens this route in headless Chromium and prints it once
// window.__printReady is true. Same components as the screen, so the PDF matches.

import { useQuery } from '@tanstack/react-query'
import maplibregl, { type Map as MLMap } from 'maplibre-gl'
import QRCode from 'qrcode'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'
import { api, type Config, type Glance, type LayerT, type ProductT, type SiteFull, type Summary } from '../api'
import Legend from '../components/Legend'
import { useConfigData, useLayerData } from '../hooks'
import { legendData } from '../map/legend'
import MapView, { addProtocols, type LayerState } from '../map/MapView'
import { basemapStyle } from '../map/style'
import { brand } from '../theme'

declare global {
  interface Window { __printReady?: boolean; __printError?: string }
}

const PAGE = { A3: [420, 297], A4: [297, 210] } as const
const DPI = 300

export default function PrintPage() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const v = params.get('v')
  const preview = params.has('preview')
  const config = useConfigData()
  const q = useQuery({
    queryKey: ['print', id, v],
    queryFn: () => api<{ product: ProductT; site: SiteFull; summary: Summary | null }>(`/products/${id}${v ? `?v=${v}` : ''}`),
  })
  const live = useQuery({
    queryKey: ['print-summary', id],
    enabled: !!q.data && !q.data.summary,
    queryFn: () => {
      const vis = (q.data!.product.view.layers || []).filter((l) => l.visible).map((l) => l.id)
      return api<Summary>(`/sites/${q.data!.site.id}/summary?layers=${vis.join(',')}`)
    },
  })
  useEffect(() => {
    if (q.error) window.__printError = String(q.error)
  }, [q.error])
  if (!q.data) return null
  const summary = q.data.summary || live.data
  if (!summary) return null
  return <Page config={config} product={q.data.product} site={q.data.site} summary={summary} preview={preview} version={v} />
}

function Page({ config, product, site, summary, preview, version }: {
  config: Config; product: ProductT; site: SiteFull; summary: Summary; preview: boolean; version: string | null
}) {
  const [w, h] = PAGE[product.page_size] || PAGE.A3
  const view = product.view
  const viewLayers = view.layers || []
  const visible = new Set(viewLayers.filter((l) => l.visible).map((l) => l.id))
  const layers = site.layers.filter((l) => viewLayers.length ? visible.has(l.id) : l.visible_default)
  const state: Record<string, LayerState> = {}
  for (const l of site.layers) {
    const vl = viewLayers.find((x) => x.id === l.id)
    state[l.id] = { visible: vl ? vl.visible : l.visible_default, opacity: vl?.opacity ?? l.style.opacity ?? 1 }
  }
  const { data, loading } = useLayerData(layers)
  const legend = useMemo(() => legendData(layers, data), [layers, data])
  const basemap = config.basemaps.find((b) => b.id === view.basemap) || config.basemaps[0]
  const [mapReady, setMapReady] = useState(false)
  const [insetReady, setInsetReady] = useState(false)
  const [qr, setQr] = useState('')
  const [mapState, setMapState] = useState<{ zoom: number; lat: number; bearing: number; bounds?: [number, number, number, number] }>()
  const link = `${window.location.origin}/r/${site.response.slug}/${site.slug}`
  const rendered = version ? product.versions.find((x) => String(x.n) === version)?.rendered_at : null
  const date = new Date(rendered || Date.now())
  const sideW = product.page_size === 'A3' ? 82 : 66
  const baseFont = product.page_size === 'A3' ? 3.4 : 2.7 // mm

  useEffect(() => {
    QRCode.toDataURL(link, { margin: 0, width: 300, errorCorrectionLevel: 'M' }).then(setQr)
  }, [link])
  useEffect(() => {
    if (!mapReady || !insetReady || !qr || loading) return
    document.fonts.ready.then(() => setTimeout(() => (window.__printReady = true), 300))
  }, [mapReady, insetReady, qr, loading])
  useEffect(() => {
    // Never hang the worker: print what we have after 100 s
    const t = setTimeout(() => (window.__printReady = true), 100_000)
    return () => clearTimeout(t)
  }, [])

  const onIdle = (map: MLMap) => {
    if (loading) return
    const b = map.getBounds()
    setMapState({ zoom: map.getZoom(), lat: map.getCenter().lat, bearing: map.getBearing(), bounds: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()] })
    if (map.areTilesLoaded()) setMapReady(true)
  }
  const glance: Glance[] = summary.glance.map((g, i) => {
    const o = product.glance?.[i]
    return o ? { value: o.value || g.value, label: o.label || g.label, tbc: o.tbc } : g
  })
  const sources = product.sources || autoSources(layers, basemap?.attribution)

  return (
    <div style={{ width: `${w}mm`, height: `${h}mm`, display: 'grid', gridTemplateRows: 'auto 1fr auto', fontFamily: 'Inter, sans-serif', color: config.symbology.ink, background: '#fff', fontSize: `${baseFont}mm`, overflow: 'hidden' }}>
      <style>{`@page { size: ${product.page_size} landscape; margin: 0 } html, body, #root { margin: 0; height: auto; background: ${preview ? '#fff' : '#fff'} } * { -webkit-print-color-adjust: exact; print-color-adjust: exact }`}</style>
      {/* Header band */}
      <header style={{ display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: '2em', alignItems: 'center', padding: '0.9em 1.6em', background: brand.band, color: brand.bandInk }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6em', minWidth: '8em' }}>
          {product.authority ? (
            <>
              <span style={{ width: '2.4em', height: '2.4em', borderRadius: '50%', border: '0.15em solid currentColor', display: 'inline-block', opacity: 0.85 }} />
              <b style={{ fontSize: '0.85em', lineHeight: 1.15, maxWidth: '12em' }}>{product.authority}</b>
            </>
          ) : <b style={{ fontSize: '0.85em', opacity: 0.6 }}>RISA</b>}
        </div>
        <div style={{ minWidth: 0 }}>
          <h1 style={{ margin: 0, font: `700 2em/1.05 Inter, sans-serif` }}>{product.title}</h1>
          <p style={{ margin: '0.3em 0 0', fontSize: '0.9em', opacity: 0.85 }}>{[site.name, site.place, site.response.name].filter(Boolean).join(' · ')}</p>
        </div>
        <div style={{ display: 'grid', justifyItems: 'end', gap: '0.2em', fontSize: '0.8em' }}>
          <b style={{ padding: '0.2em 0.5em', background: brand.accent, color: brand.accentInk, borderRadius: 2 }}>{[product.code, product.version_label].filter(Boolean).join(' · ')}</b>
          <span>{date.toLocaleString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
          <span>{site.response.glide || 'Page 1'}</span>
        </div>
      </header>

      {/* Map and side panel */}
      <div style={{ display: 'grid', gridTemplateColumns: `1fr ${sideW}mm`, minHeight: 0 }}>
        <div style={{ position: 'relative', minHeight: 0, borderRight: `1px solid ${brand.rule}`, overflow: 'hidden' }}>
          <MapView config={config} basemap={basemap?.id || 'none'} layers={layers} state={state} data={data} interactive={false}
            attributionControl={false} pixelRatio={preview ? Math.min(2, window.devicePixelRatio || 1) : DPI / 96}
            initial={view.bounds ? { bounds: view.bounds, bearing: view.bearing } : { center: view.center, zoom: view.zoom, bearing: view.bearing }}
            onReady={(m) => { if (view.bounds) m.fitBounds(view.bounds, { duration: 0, padding: 0, bearing: view.bearing || 0 }) }}
            onIdle={onIdle} style={{ position: 'absolute', inset: 0 }} />
          {mapState && <NorthArrow bearing={mapState.bearing} />}
          {mapState && <ScaleBar zoom={mapState.zoom} lat={mapState.lat} />}
          <div style={{ position: 'absolute', left: '1em', top: '1em', width: `${product.page_size === 'A3' ? 52 : 40}mm`, height: `${product.page_size === 'A3' ? 38 : 30}mm`, border: `0.3mm solid ${config.symbology.ink}`, background: '#fff', boxShadow: '0 0 0 0.8mm rgba(255,255,255,.8)' }}>
            {mapState?.bounds ? <Inset config={config} basemapId={basemap?.id} bounds={mapState.bounds} onReady={() => setInsetReady(true)} /> : null}
          </div>
        </div>
        <aside style={{ padding: '1.1em 1.3em', display: 'flex', flexDirection: 'column', gap: '1em', overflow: 'hidden' }}>
          {product.key_message && (
            <div style={{ borderLeft: `0.8mm solid ${config.symbology.ink}`, paddingLeft: '0.8em' }}>
              <h2 style={{ margin: 0, fontSize: '0.8em', textTransform: 'uppercase', letterSpacing: '0.06em', color: brand.muted }}>Key message</h2>
              <p style={{ margin: '0.3em 0 0', fontWeight: 600, lineHeight: 1.3 }}>{product.key_message}</p>
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5em' }}>
            {glance.map((g, i) => (
              <div key={i} style={{ border: `1px solid ${brand.rule}`, padding: '0.5em 0.6em', borderRadius: 2 }}>
                <b style={{ display: 'block', fontSize: '1.6em', lineHeight: 1.1 }}>{g.value || '–'}</b>
                <span style={{ fontSize: '0.75em', color: brand.muted }}>{g.label}{g.tbc && <em style={{ marginLeft: '0.4em', fontStyle: 'normal', fontWeight: 700, fontSize: '0.85em', padding: '0 0.3em', border: `1px solid ${brand.muted}`, borderRadius: 2 }}>TBC</em>}</span>
              </div>
            ))}
          </div>
          <div style={{ fontSize: '0.95em' }}><Legend config={config} data={legend} /></div>
        </aside>
      </div>

      {/* Footer */}
      <footer style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto', gap: '1.6em', alignItems: 'center', padding: '0.6em 1.6em', borderTop: `1px solid ${brand.rule}`, fontSize: '0.68em', color: brand.muted }}>
        <p style={{ margin: 0, lineHeight: 1.35 }}>
          <b>Sources:</b> {sources}<br />{product.disclaimer}
        </p>
        <div style={{ textAlign: 'center' }}><small style={{ display: 'block' }}>Produced with the</small><b style={{ color: config.symbology.ink, fontSize: '1.3em' }}>RISA</b> <small>method</small></div>
        <div><small style={{ display: 'block' }}>Technical support</small><b style={{ color: config.symbology.ink }}>{product.credits}</b></div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5em' }}>
          {qr && <img src={qr} style={{ width: '12mm', height: '12mm' }} alt="" />}
          <small style={{ maxWidth: '7em', lineHeight: 1.2 }}>Scan for the live map</small>
        </div>
      </footer>
    </div>
  )
}

function autoSources(layers: LayerT[], basemapAttribution?: string) {
  const parts = layers.map((l) => {
    const bits = [l.attribution || l.name]
    if (l.resolution_cm) bits.push(`${l.resolution_cm} cm/px`)
    if (l.captured_at) bits.push(new Date(l.captured_at).toLocaleDateString('en-GB'))
    if (l.kind === 'kobo' && l.kobo) bits.push(`${l.kobo.submissions} points`)
    return bits.join(', ')
  })
  if (basemapAttribution) parts.push(`Base: ${basemapAttribution}`)
  return parts.join('. ') + '.'
}

function NorthArrow({ bearing }: { bearing: number }) {
  return (
    <svg viewBox="-12 -16 24 32" style={{ position: 'absolute', right: '1.2em', top: '1.2em', width: '7mm', transform: `rotate(${-bearing}deg)` }} aria-label="North">
      <path d="M0 -14 L8 8 L0 3 L-8 8 Z" fill="#1D232B" stroke="#fff" strokeWidth="1.5" />
      <text y="15" textAnchor="middle" fontSize="7" fontWeight="700" fill="#1D232B" stroke="#fff" strokeWidth="2" paintOrder="stroke">N</text>
    </svg>
  )
}

/** Metric scale bar for the map's zoom at its centre latitude. 1 CSS px = 1/96 in. */
function ScaleBar({ zoom, lat }: { zoom: number; lat: number }) {
  const mPerPx = (40075016.686 * Math.cos((lat * Math.PI) / 180)) / (512 * 2 ** zoom)
  const targetPx = 150
  const raw = mPerPx * targetPx
  const pow = 10 ** Math.floor(Math.log10(raw))
  const nice = [1, 2, 5, 10].map((n) => n * pow).reverse().find((n) => n <= raw) || pow
  const px = nice / mPerPx
  const label = nice >= 1000 ? `${nice / 1000} km` : `${nice} m`
  const scale = Math.round(mPerPx / (0.0254 / 96))
  return (
    <div style={{ position: 'absolute', left: '1.2em', bottom: '1.2em', background: 'rgba(255,255,255,.88)', padding: '0.35em 0.6em', borderRadius: 2, fontSize: '0.75em' }}>
      <svg width={px + 2} height="10" style={{ display: 'block' }}>
        <rect x="1" y="2" width={px / 2} height="6" fill="#1D232B" />
        <rect x={1 + px / 2} y="2" width={px / 2} height="6" fill="#fff" stroke="#1D232B" strokeWidth="1" />
        <rect x="1" y="2" width={px} height="6" fill="none" stroke="#1D232B" strokeWidth="1" />
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1em' }}><span>0</span><span>{label}</span></div>
      <div style={{ color: '#4A5A6D' }}>1:{scale.toLocaleString('en-GB')} at print size</div>
    </div>
  )
}

function Inset({ config, basemapId, bounds, onReady }: { config: Config; basemapId?: string; bounds: [number, number, number, number]; onReady: () => void }) {
  const el = useRef<HTMLDivElement>(null)
  useEffect(() => {
    addProtocols()
    // The inset needs a map: fall back from imagery or none to a light basemap
    const bm = config.basemaps.find((b) => b.id === basemapId && b.kind !== 'raster' && b.kind !== 'none')
      || config.basemaps.find((b) => b.kind === 'style' || b.kind === 'pmtiles')
      || config.basemaps.find((b) => b.id === basemapId)
    const [w, s, e, n] = bounds
    const map = new maplibregl.Map({
      container: el.current!, style: basemapStyle(bm, config.glyphs), interactive: false, attributionControl: false,
      center: [(w + e) / 2, (s + n) / 2], zoom: 11, pixelRatio: 3, canvasContextAttributes: { preserveDrawingBuffer: true }, fadeDuration: 0,
    })
    map.on('load', () => {
      map.addSource('frame', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } } })
      map.addLayer({ id: 'frame-fill', type: 'fill', source: 'frame', paint: { 'fill-color': '#A8281A', 'fill-opacity': 0.15 } })
      map.addLayer({ id: 'frame', type: 'line', source: 'frame', paint: { 'line-color': '#A8281A', 'line-width': 2 } })
      map.addSource('centre', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [(w + e) / 2, (s + n) / 2] } } })
      map.addLayer({ id: 'centre', type: 'circle', source: 'centre', paint: { 'circle-radius': 4, 'circle-color': '#A8281A', 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5 } })
      map.once('idle', onReady)
    })
    map.on('error', () => onReady())
    return () => map.remove()
  }, [bounds.join(','), basemapId])
  return <div ref={el} style={{ width: '100%', height: '100%' }} />
}
