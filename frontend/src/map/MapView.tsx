import { cogProtocol } from '@geomatico/maplibre-cog-protocol'
import maplibregl, { type LngLatBoundsLike, type Map as MLMap, type StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Protocol } from 'pmtiles'
import { useEffect, useRef } from 'react'
import type { Config, LayerT } from '../api'
import { installSymbols } from './symbols'
import { INTERACTIVE_PARTS, OVERLAY_PREFIX, basemapStyle, overlayLayers, overlaySource, sourceId } from './style'

let protocolsAdded = false
export function addProtocols() {
  if (protocolsAdded) return
  maplibregl.addProtocol('cog', cogProtocol)
  maplibregl.addProtocol('pmtiles', new Protocol().tile)
  protocolsAdded = true
}

export interface LayerState {
  visible: boolean
  opacity: number
}

export interface PickedFeature {
  layerId: string
  id: string
  properties: Record<string, unknown>
  geometry: GeoJSON.Geometry
}

interface Props {
  config: Config
  basemap: string
  /** Top first */
  layers: LayerT[]
  state: Record<string, LayerState>
  data: Record<string, GeoJSON.FeatureCollection | undefined>
  initial?: { center?: [number, number]; zoom?: number; bearing?: number; bounds?: [number, number, number, number] }
  interactive?: boolean
  pixelRatio?: number
  attributionControl?: boolean
  onReady?: (map: MLMap) => void
  onFeatureClick?: (f: PickedFeature | null) => void
  onIdle?: (map: MLMap) => void
  /** Features to outline above everything else */
  highlight?: GeoJSON.Geometry[]
  className?: string
  style?: React.CSSProperties
}

const HL = 'hl-'
const HL_COLOR = '#7048e8'
const isOurs = (id: string) => id.startsWith(OVERLAY_PREFIX) || id.startsWith('td-') || id.startsWith(HL)

export default function MapView(props: Props) {
  const el = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MLMap | null>(null)
  const propsRef = useRef(props)
  propsRef.current = props
  const basemapRef = useRef<string>('')

  // Create the map once
  useEffect(() => {
    addProtocols()
    const p = propsRef.current
    const bm = p.config.basemaps.find((b) => b.id === p.basemap) || p.config.basemaps[0]
    basemapRef.current = bm?.id || ''
    const map = new maplibregl.Map({
      container: el.current!,
      style: basemapStyle(bm, p.config.glyphs),
      center: p.initial?.center || [0, 15],
      zoom: p.initial?.zoom ?? 2,
      bearing: p.initial?.bearing || 0,
      bounds: p.initial?.bounds as LngLatBoundsLike | undefined,
      interactive: p.interactive !== false,
      pixelRatio: p.pixelRatio,
      attributionControl: p.attributionControl === false ? false : { compact: true },
      canvasContextAttributes: { preserveDrawingBuffer: !!p.pixelRatio },
      fadeDuration: p.pixelRatio ? 0 : 300,
      maxZoom: 23,
    })
    mapRef.current = map
    if (import.meta.env.DEV) ((window as unknown as { __maps: MLMap[] }).__maps ||= []).push(map)
    installSymbols(map, p.config.symbology, 2)
    if (p.interactive !== false) {
      map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), 'top-right')
      map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left')
    }
    map.on('style.load', () => sync(map))
    map.on('idle', () => propsRef.current.onIdle?.(map))
    map.on('click', (e) => {
      const ids = interactiveLayerIds(map)
      const hit = ids.length ? map.queryRenderedFeatures(e.point, { layers: ids })[0] : undefined
      if (!hit) return propsRef.current.onFeatureClick?.(null)
      const layerId = hit.layer.id.slice(OVERLAY_PREFIX.length, OVERLAY_PREFIX.length + 36)
      // Full geometry from the source data, not the tiled one
      const fc = propsRef.current.data[layerId]
      const rid = String(hit.properties.risa_id)
      const full = fc?.features.find((f) => String(f.properties?.risa_id) === rid)
      propsRef.current.onFeatureClick?.({
        layerId,
        id: rid,
        properties: (full?.properties || hit.properties) as Record<string, unknown>,
        geometry: (full?.geometry || hit.geometry) as GeoJSON.Geometry,
      })
    })
    map.on('mousemove', (e) => {
      const ids = interactiveLayerIds(map)
      const n = ids.length ? map.queryRenderedFeatures(e.point, { layers: ids }).length : 0
      map.getCanvas().style.cursor = n ? 'pointer' : ''
    })
    map.on('load', () => propsRef.current.onReady?.(map))
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Basemap: swap the style, keeping our overlays and the drawing layers
  useEffect(() => {
    const map = mapRef.current
    if (!map || props.basemap === basemapRef.current) return
    basemapRef.current = props.basemap
    const bm = props.config.basemaps.find((b) => b.id === props.basemap)
    map.setStyle(basemapStyle(bm, props.config.glyphs), {
      diff: false,
      transformStyle: (prev, next) => {
        if (!prev) return next
        const keepSources = Object.fromEntries(Object.entries(prev.sources).filter(([id]) => isOurs(id)))
        const keepLayers = prev.layers.filter((l) => isOurs(l.id))
        return { ...next, sources: { ...next.sources, ...keepSources }, layers: [...next.layers, ...keepLayers] } as StyleSpecification
      },
    })
  }, [props.basemap, props.config])

  // Overlays
  useEffect(() => {
    const map = mapRef.current
    if (map && map.isStyleLoaded()) sync(map)
  }, [props.layers, props.state, props.data, props.highlight])

  function sync(map: MLMap) {
    const { layers, state, data, config } = propsRef.current
    const wanted = new Set<string>()
    // Bottom to top, so each moveLayer() puts the next one above
    for (const l of [...layers].reverse()) {
      const src = overlaySource(l, data[l.id])
      if (!src) continue
      const sid = sourceId(l)
      const existing = map.getSource(sid)
      if (existing && src.type === 'geojson') {
        const d = data[l.id]
        const prev = (existing as unknown as { _risaData?: unknown })._risaData
        if (d && prev !== d) {
          ;(existing as maplibregl.GeoJSONSource).setData(d)
          ;(existing as unknown as { _risaData?: unknown })._risaData = d
        }
      } else if (existing && src.type === 'raster' && (existing as unknown as { _risaUrl?: string })._risaUrl !== srcKey(src)) {
        // URL changed: rebuild
        for (const ly of map.getStyle().layers.filter((x) => 'source' in x && x.source === sid)) map.removeLayer(ly.id)
        map.removeSource(sid)
      }
      if (!map.getSource(sid)) {
        map.addSource(sid, src)
        const s = map.getSource(sid) as unknown as { _risaData?: unknown; _risaUrl?: string }
        if (src.type === 'geojson') s._risaData = data[l.id]
        else s._risaUrl = srcKey(src)
      }
      wanted.add(sid)
      const st = state[l.id] || { visible: l.visible_default, opacity: l.style.opacity ?? 1 }
      const styled = { ...l, style: { ...l.style, opacity: st.opacity } }
      for (const spec of overlayLayers(styled, config.symbology)) {
        if (!map.getLayer(spec.id)) map.addLayer(spec)
        else applyPaint(map, spec)
        map.setLayoutProperty(spec.id, 'visibility', st.visible ? 'visible' : 'none')
        map.moveLayer(spec.id)
        wanted.add(spec.id)
      }
    }
    // Highlight, then the drawing layers, on top
    const hl: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: (propsRef.current.highlight || []).map((geometry) => ({ type: 'Feature', geometry, properties: {} })) }
    const hlSource = map.getSource(`${HL}src`) as maplibregl.GeoJSONSource | undefined
    if (hlSource) hlSource.setData(hl)
    else {
      map.addSource(`${HL}src`, { type: 'geojson', data: hl })
      map.addLayer({ id: `${HL}fill`, type: 'fill', source: `${HL}src`, filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': HL_COLOR, 'fill-opacity': 0.12 } })
      map.addLayer({ id: `${HL}casing`, type: 'line', source: `${HL}src`, filter: ['!=', ['geometry-type'], 'Point'], paint: { 'line-color': '#fff', 'line-width': 7, 'line-opacity': 0.9 } })
      map.addLayer({ id: `${HL}line`, type: 'line', source: `${HL}src`, filter: ['!=', ['geometry-type'], 'Point'], paint: { 'line-color': HL_COLOR, 'line-width': 3.5 } })
      map.addLayer({ id: `${HL}point`, type: 'circle', source: `${HL}src`, filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-radius': 19, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': HL_COLOR, 'circle-stroke-width': 3.5 } })
    }
    for (const ly of map.getStyle().layers) if (ly.id.startsWith(HL)) map.moveLayer(ly.id)
    for (const ly of map.getStyle().layers) if (ly.id.startsWith('td-')) map.moveLayer(ly.id)
    // Remove what's gone
    for (const ly of map.getStyle().layers) {
      if (ly.id.startsWith(OVERLAY_PREFIX) && !wanted.has(ly.id)) map.removeLayer(ly.id)
    }
    for (const sid of Object.keys(map.getStyle().sources)) {
      if (sid.startsWith(OVERLAY_PREFIX) && !wanted.has(sid)) map.removeSource(sid)
    }
  }

  return <div ref={el} className={props.className} style={{ width: '100%', height: '100%', ...props.style }} />
}

function srcKey(src: maplibregl.SourceSpecification) {
  return 'url' in src && src.url ? src.url : 'tiles' in src && src.tiles ? src.tiles.join('|') : ''
}

function applyPaint(map: MLMap, spec: maplibregl.LayerSpecification) {
  const paint = (spec as { paint?: Record<string, unknown> }).paint || {}
  for (const [k, v] of Object.entries(paint)) {
    if (k.endsWith('opacity')) map.setPaintProperty(spec.id, k, v)
  }
}

function interactiveLayerIds(map: MLMap) {
  return map
    .getStyle()
    .layers.filter((l) => l.id.startsWith(OVERLAY_PREFIX) && INTERACTIVE_PARTS.some((p) => l.id.endsWith(`-${p}`)))
    .filter((l) => map.getLayoutProperty(l.id, 'visibility') !== 'none')
    .map((l) => l.id)
}
