// The map for a printed product, alone and full-window. The worker opens this in
// headless Chromium at the frame's exact size (and 300 dpi as the device scale), waits
// for window.__printReady, screenshots it, and Typst places the image on the page.
//
//   /print/map/:id?v=3&part=main
//   /print/map/:id?part=inset&bounds=w,s,e,n&zoom=17          area round the site
//   /print/map/:id?part=overview&bounds=w,s,e,n&centre=lon,lat  country overview

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
    /** Main map: zoom, lat, bearing, m_per_px, bounds. Locators: bounds, and on the
     *  overview the marker's box as fractions of the image [x0, y0, x1, y1] */
    __mapState?: Record<string, unknown>
    /** The map canvas as a JPEG data URL, at the device pixel ratio (300 dpi when printing) */
    __mapImage?: () => string
  }
}

// Reading the canvas directly is much cheaper than a page screenshot at 300 dpi,
// which on a small worker spends minutes compositing in software.
const exportCanvas = (m: MLMap) => () => m.getCanvas().toDataURL('image/jpeg', 0.88)

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
  const part = params.get('part')
  const bounds = (params.get('bounds') || '').split(',').map(Number)
  if (part === 'inset') return <Locator product={q.data.product} bounds={bounds} zoom={Number(params.get('zoom') || 16)} />
  if (part === 'overview') {
    const [lon, lat] = (params.get('centre') || '').split(',').map(Number)
    return <Locator product={q.data.product} bounds={bounds} centre={Number.isFinite(lat) ? [lon, lat] : undefined} overview />
  }
  return <MainMap product={q.data.product} site={q.data.site} />
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
    window.__mapImage = exportCanvas(m)
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

const INK = '#1D232B'
const OVERVIEW_SPAN_M = 1_500_000 // the country overview is about this wide
const EARTH_M = 40075016.686

/** A locator: a light basemap zoomed out, with `bounds` marked. The area locator is
 *  centred on the extent, 5 zoom levels out. The overview is about 1,500 km across
 *  (less if the extent wouldn't fit), and reports where its marker is so the page can
 *  draw leader lines to it. Ink, not the status colours, which are reserved. */
function Locator({ product, bounds, zoom = 16, centre, overview = false }: {
  product: ProductT; bounds: number[]; zoom?: number; centre?: [number, number]; overview?: boolean
}) {
  const config = useConfigData()
  const el = useRef<HTMLDivElement>(null)
  useEffect(() => {
    addProtocols()
    const id = product.view.basemap
    const bm = config.basemaps.find((b) => b.id === id && (b.kind === 'style' || b.kind === 'pmtiles'))
      || config.basemaps.find((b) => b.kind === 'style' || b.kind === 'pmtiles')
      || config.basemaps.find((b) => b.id === id)
    const [w, s, e, n] = bounds
    const mid: [number, number] = centre || [(w + e) / 2, (s + n) / 2]
    const width = el.current!.clientWidth
    let z = Math.max(3, Math.min(13, zoom - 5))
    if (overview) {
      const fit = Math.log2((width * EARTH_M * Math.cos((mid[1] * Math.PI) / 180)) / (512 * OVERVIEW_SPAN_M))
      const extentPx0 = (Math.max(e - w, 1e-6) / 360) * 512 // the extent's width at zoom 0
      z = Math.max(0, Math.min(8, fit, Math.log2((0.35 * width) / extentPx0)))
    }
    const map = new maplibregl.Map({
      container: el.current!, style: basemapStyle(bm, config.glyphs), interactive: false, attributionControl: false,
      center: mid, zoom: z, pixelRatio: window.devicePixelRatio || 1,
      canvasContextAttributes: { preserveDrawingBuffer: true }, fadeDuration: 0,
    })
    const frame: GeoJSON.Feature = { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } }
    const point = (c: [number, number]): GeoJSON.Feature => ({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: c } })
    let marker: number[] | null = null
    map.on('load', () => {
      // The extent as a box, or as a ring when it would be too small to see
      const a = map.project([w, n]), b = map.project([e, s])
      const h = el.current!.clientHeight
      const small = b.x - a.x < 10 || b.y - a.y < 10
      if (small) {
        const c = map.project([(w + e) / 2, (s + n) / 2]), R = 6
        map.addSource('mark', { type: 'geojson', data: point([(w + e) / 2, (s + n) / 2]) })
        map.addLayer({ id: 'mark', type: 'circle', source: 'mark', paint: overview
          ? { 'circle-radius': R, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': INK, 'circle-stroke-width': 2 }
          : { 'circle-radius': 4, 'circle-color': INK, 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5 } })
        marker = [c.x - R, c.y - R, c.x + R, c.y + R]
      } else {
        map.addSource('frame', { type: 'geojson', data: frame })
        map.addLayer({ id: 'frame-fill', type: 'fill', source: 'frame', paint: { 'fill-color': INK, 'fill-opacity': 0.12 } })
        map.addLayer({ id: 'frame', type: 'line', source: 'frame', paint: { 'line-color': INK, 'line-width': 1.6 } })
        if (!overview) {
          map.addSource('centre', { type: 'geojson', data: point(mid) })
          map.addLayer({ id: 'centre', type: 'circle', source: 'centre', paint: { 'circle-radius': 3.5, 'circle-color': INK, 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5 } })
        }
        marker = [a.x, a.y, b.x, b.y]
      }
      marker = [marker[0] / width, marker[1] / h, marker[2] / width, marker[3] / h].map((x) => Math.round(x * 1e4) / 1e4)
    })
    map.on('idle', () => {
      if (!map.loaded() || !map.areTilesLoaded() || !marker) return
      const bb = map.getBounds()
      window.__mapState = { bounds: [bb.getWest(), bb.getSouth(), bb.getEast(), bb.getNorth()], zoom: map.getZoom(), marker }
      window.__mapImage = exportCanvas(map)
      requestAnimationFrame(() => requestAnimationFrame(() => (window.__printReady = true)))
    })
    map.on('error', (e) => console.warn(overview ? 'overview' : 'inset', e.error?.message))
    return () => map.remove()
  }, [])
  return <div ref={el} style={full} />
}
