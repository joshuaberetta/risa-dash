// The map for a printed product, alone and full-window. The worker opens this in
// headless Chromium at the frame's exact size (and 300 dpi as the device scale), waits
// for window.__printReady, screenshots it, and Typst places the image on the page.
//
//   /print/map/:id?v=3&part=main
//   /print/map/:id?part=inset&bounds=w,s,e,n&zoom=17

import { useQuery } from '@tanstack/react-query'
import maplibregl, { type Map as MLMap } from 'maplibre-gl'
import { useEffect, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router'
import { api, type ProductT, type SiteFull } from '../api'
import { useConfigData, useLayerData } from '../hooks'
import MapView, { addProtocols, type LayerState } from '../map/MapView'
import { basemapStyle } from '../map/style'

declare global {
  interface Window {
    __printReady?: boolean
    __printError?: string
    __mapState?: { zoom: number; lat: number; bearing: number; m_per_px: number; bounds: number[] }
  }
}

export default function MapPrint() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const v = params.get('v')
  const q = useQuery({
    queryKey: ['print', id, v],
    queryFn: () => api<{ product: ProductT; site: SiteFull }>(`/products/${id}${v ? `?v=${v}` : ''}`),
  })
  useEffect(() => {
    document.body.style.margin = '0'
    if (q.error) window.__printError = String(q.error)
  }, [q.error])
  if (!q.data) return null
  return params.get('part') === 'inset'
    ? <Inset product={q.data.product} bounds={(params.get('bounds') || '').split(',').map(Number)} zoom={Number(params.get('zoom') || 16)} />
    : <MainMap product={q.data.product} site={q.data.site} />
}

const full: React.CSSProperties = { position: 'fixed', inset: 0 }

function MainMap({ product, site }: { product: ProductT; site: SiteFull }) {
  const config = useConfigData()
  const view = product.view
  const vl = view.layers || []
  const visible = new Set(vl.filter((l) => l.visible).map((l) => l.id))
  const layers = site.layers.filter((l) => (vl.length ? visible.has(l.id) : l.visible_default))
  const state: Record<string, LayerState> = {}
  for (const l of site.layers) {
    const x = vl.find((y) => y.id === l.id)
    state[l.id] = { visible: x ? x.visible : l.visible_default, opacity: x?.opacity ?? l.style.opacity ?? 1 }
  }
  const { data, loading } = useLayerData(layers)
  const basemap = config.basemaps.find((b) => b.id === view.basemap) || config.basemaps[0]
  const fitted = useRef(false)

  const onReady = (m: MLMap) => {
    if (view.bounds) m.fitBounds(view.bounds as [number, number, number, number], { duration: 0, padding: 0, bearing: view.bearing || 0 })
    fitted.current = true
  }
  const onIdle = (m: MLMap) => {
    if (loading || !fitted.current || !m.areTilesLoaded()) return
    const c = m.getCenter()
    const b = m.getBounds()
    window.__mapState = {
      zoom: m.getZoom(), lat: c.lat, bearing: m.getBearing(),
      // Ground metres per CSS px at the centre (MapLibre tiles are 512 px)
      m_per_px: (40075016.686 * Math.cos((c.lat * Math.PI) / 180)) / (512 * 2 ** m.getZoom()),
      bounds: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()],
    }
    // One more frame so the last tiles are painted
    requestAnimationFrame(() => requestAnimationFrame(() => (window.__printReady = true)))
  }
  return (
    <MapView config={config} basemap={basemap?.id || 'none'} layers={layers} state={state} data={data} interactive={false}
      attributionControl={false} pixelRatio={window.devicePixelRatio || 1} style={full}
      initial={view.bounds ? { bounds: view.bounds as [number, number, number, number], bearing: view.bearing } : { center: view.center, zoom: view.zoom, bearing: view.bearing }}
      onReady={onReady} onIdle={onIdle} />
  )
}

/** Locator: a light basemap zoomed out, with the main map's extent marked. */
function Inset({ product, bounds, zoom }: { product: ProductT; bounds: number[]; zoom: number }) {
  const config = useConfigData()
  const el = useRef<HTMLDivElement>(null)
  useEffect(() => {
    addProtocols()
    const id = product.view.basemap
    const bm = config.basemaps.find((b) => b.id === id && (b.kind === 'style' || b.kind === 'pmtiles'))
      || config.basemaps.find((b) => b.kind === 'style' || b.kind === 'pmtiles')
      || config.basemaps.find((b) => b.id === id)
    const [w, s, e, n] = bounds
    const centre: [number, number] = [(w + e) / 2, (s + n) / 2]
    const map = new maplibregl.Map({
      container: el.current!, style: basemapStyle(bm, config.glyphs), interactive: false, attributionControl: false,
      center: centre, zoom: Math.max(3, Math.min(13, zoom - 5)), pixelRatio: window.devicePixelRatio || 1,
      canvasContextAttributes: { preserveDrawingBuffer: true }, fadeDuration: 0,
    })
    map.on('load', () => {
      map.addSource('frame', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } } })
      map.addSource('centre', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: centre } } })
      map.addLayer({ id: 'frame-fill', type: 'fill', source: 'frame', paint: { 'fill-color': '#A8281A', 'fill-opacity': 0.15 } })
      map.addLayer({ id: 'frame', type: 'line', source: 'frame', paint: { 'line-color': '#A8281A', 'line-width': 2 } })
      map.addLayer({ id: 'centre', type: 'circle', source: 'centre', paint: { 'circle-radius': 4, 'circle-color': '#A8281A', 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5 } })
    })
    map.on('idle', () => {
      if (map.loaded() && map.areTilesLoaded()) requestAnimationFrame(() => requestAnimationFrame(() => (window.__printReady = true)))
    })
    map.on('error', (e) => console.warn('inset', e.error?.message))
    return () => map.remove()
  }, [])
  return <div ref={el} style={full} />
}
