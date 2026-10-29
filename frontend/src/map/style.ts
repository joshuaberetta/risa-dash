// Basemap styles and the MapLibre sources/layers for each site layer, with RISA symbology.

import { layers as protomapsLayers, namedFlavor } from '@protomaps/basemaps'
import type {
  ExpressionSpecification,
  LayerSpecification,
  SourceSpecification,
  StyleSpecification,
} from 'maplibre-gl'
import { absUrl, type Basemap, type LayerT, type Symbology } from '../api'

export const OVERLAY_PREFIX = 'risa-'
export const FONT = ['Noto Sans Regular']
export const FONT_BOLD = ['Noto Sans Bold']

export function basemapStyle(bm: Basemap | undefined, glyphs: string): StyleSpecification | string {
  const bg: LayerSpecification = { id: 'background', type: 'background', paint: { 'background-color': '#eef0f2' } }
  if (!bm || bm.kind === 'none') return { version: 8, glyphs, sources: {}, layers: [bg] }
  if (bm.kind === 'style') return bm.url!
  if (bm.kind === 'raster') {
    return {
      version: 8,
      glyphs,
      sources: { base: { type: 'raster', tiles: [bm.url!], tileSize: 256, maxzoom: bm.maxzoom || 19, attribution: bm.attribution } },
      layers: [bg, { id: 'base', type: 'raster', source: 'base' }],
    }
  }
  // Local PMTiles extract (works offline)
  return {
    version: 8,
    glyphs,
    sources: { protomaps: { type: 'vector', url: `pmtiles://${absUrl(bm.url!)}`, attribution: bm.attribution } },
    layers: protomapsLayers('protomaps', namedFlavor('light'), { lang: 'en' }) as LayerSpecification[],
  }
}

export const sourceId = (l: LayerT) => `${OVERLAY_PREFIX}${l.id}`
const lid = (l: LayerT, part: string) => `${OVERLAY_PREFIX}${l.id}-${part}`

export function overlaySource(l: LayerT, data?: GeoJSON.FeatureCollection): SourceSpecification | null {
  if (l.status !== 'ready' || !l.url) return null
  switch (l.kind) {
    case 'raster':
    case 'cog_url':
      return { type: 'raster', url: `cog://${absUrl(l.url)}`, tileSize: 256, attribution: l.attribution || undefined }
    case 'xyz':
      return { type: 'raster', tiles: [l.url], tileSize: 256, attribution: l.attribution || undefined }
    case 'wms': {
      let u = l.url
      if (!u.includes('{bbox')) {
        u += `${u.includes('?') ? '&' : '?'}service=WMS&request=GetMap&version=1.1.1&srs=EPSG:3857&width=256&height=256&format=image/png&transparent=true&bbox={bbox-epsg-3857}`
      }
      return { type: 'raster', tiles: [u], tileSize: 256, attribution: l.attribution || undefined }
    }
    default:
      return { type: 'geojson', data: data || { type: 'FeatureCollection', features: [] }, attribution: l.attribution || undefined, promoteId: 'risa_id' }
  }
}

const isPoly: ExpressionSpecification = ['in', ['geometry-type'], ['literal', ['Polygon', 'MultiPolygon']]]
const isLine: ExpressionSpecification = ['in', ['geometry-type'], ['literal', ['LineString', 'MultiLineString']]]
const isPoint: ExpressionSpecification = ['in', ['geometry-type'], ['literal', ['Point', 'MultiPoint']]]
const status: ExpressionSpecification = ['coalesce', ['get', 'risa_status'], '']
const rtype: ExpressionSpecification = ['coalesce', ['get', 'risa_type'], '']

/** The layers drawn for one site layer, bottom to top. */
export function overlayLayers(l: LayerT, sym: Symbology): LayerSpecification[] {
  const src = sourceId(l)
  const op = l.style.opacity ?? 1
  if (!['vector', 'kobo', 'annotations'].includes(l.kind)) {
    return [{ id: lid(l, 'raster'), type: 'raster', source: src, paint: { 'raster-opacity': op, 'raster-fade-duration': 0 } }]
  }
  const base = l.style.color || '#3B5B7A'
  const S = sym.status
  const statusColor: ExpressionSpecification = [
    'match', status, 'ok', S.ok.color, 'partial', S.partial.color, 'no', S.no.color, 'unknown', S.unknown.color, base,
  ]
  const fillColor: ExpressionSpecification = [
    'match', rtype,
    'flood', sym.hazards.flood.color,
    'debris', sym.hazards.debris.color,
    'block', '#C8A86B',
    ['match', status, 'ok', S.ok.color, 'partial', S.partial.color, 'no', S.no.color, base],
  ]
  const lineColor: ExpressionSpecification = [
    'match', rtype, 'flood', sym.hazards.flood.color, 'debris', sym.hazards.debris.color, statusColor,
  ]
  const labelField: ExpressionSpecification = l.style.label_field
    ? ['to-string', ['coalesce', ['get', l.style.label_field], '']]
    : ['coalesce', ['get', 'risa_label'], '']
  // Status shown twice: colour and line style (solid / dashed / dotted)
  const lineLayers = (part: string, geom: ExpressionSpecification, w: number): LayerSpecification[] => [
    {
      id: lid(l, `${part}-casing`), type: 'line', source: src, filter: ['all', geom, ['!', ['in', rtype, ['literal', ['flood', 'debris', 'block']]]]],
      paint: { 'line-color': '#fff', 'line-width': w + 4, 'line-opacity': op },
      layout: { 'line-join': 'round' },
    },
    {
      id: lid(l, `${part}-solid`), type: 'line', source: src, filter: ['all', geom, ['!', ['in', status, ['literal', ['partial', 'no']]]]],
      paint: { 'line-color': lineColor, 'line-width': w, 'line-opacity': op },
      layout: { 'line-join': 'round', 'line-cap': 'round' },
    },
    {
      id: lid(l, `${part}-dashed`), type: 'line', source: src, filter: ['all', geom, ['==', status, 'partial']],
      paint: { 'line-color': lineColor, 'line-width': w, 'line-dasharray': [2, 1], 'line-opacity': op },
      layout: { 'line-join': 'round' },
    },
    {
      id: lid(l, `${part}-dotted`), type: 'line', source: src, filter: ['all', geom, ['==', status, 'no']],
      paint: { 'line-color': lineColor, 'line-width': w * 1.15, 'line-dasharray': [0.1, 1.7], 'line-opacity': op },
      layout: { 'line-join': 'round', 'line-cap': 'round' },
    },
  ]
  return [
    {
      id: lid(l, 'fill'), type: 'fill', source: src, filter: isPoly,
      paint: { 'fill-color': fillColor, 'fill-opacity': ['*', op, ['match', rtype, 'flood', 0.3, 'debris', 0.35, 0.45]] },
    },
    ...lineLayers('outline', isPoly, 2),
    ...lineLayers('line', isLine, 4),
    {
      id: lid(l, 'points'), type: 'symbol', source: src, filter: isPoint,
      layout: {
        'icon-image': ['concat', 'risa:', ['case', ['==', rtype, ''], 'other', rtype], ':', ['case', ['==', status, ''], 'unknown', status]],
        'icon-allow-overlap': true,
        // Labels give way to service symbols, not the other way round
        'icon-ignore-placement': false,
        'icon-size': ['interpolate', ['linear'], ['zoom'], 12, 0.6, 17, 1],
      },
      paint: { 'icon-opacity': op },
    },
    {
      id: lid(l, 'labels-poly'), type: 'symbol', source: src, filter: isPoly,
      // Shifts off the centre rather than sitting under a service symbol
      layout: {
        'text-field': labelField, 'text-font': FONT_BOLD, 'text-size': 13, 'text-max-width': 8, 'text-padding': 1,
        'text-variable-anchor': ['center', 'top', 'bottom', 'left', 'right'], 'text-radial-offset': 0.9,
      },
      paint: { 'text-color': sym.ink, 'text-halo-color': 'rgba(255,255,255,0.9)', 'text-halo-width': 1.6, 'text-opacity': op },
    },
    {
      id: lid(l, 'labels-line'), type: 'symbol', source: src, filter: isLine,
      layout: { 'text-field': labelField, 'text-font': FONT_BOLD, 'text-size': 12, 'symbol-placement': 'line', 'text-letter-spacing': 0.05 },
      paint: { 'text-color': sym.ink, 'text-halo-color': '#fff', 'text-halo-width': 1.6, 'text-opacity': op },
    },
    {
      id: lid(l, 'labels-point'), type: 'symbol', source: src, filter: isPoint, minzoom: 15,
      layout: { 'text-field': labelField, 'text-font': FONT, 'text-size': 11, 'text-offset': [0, 1.5], 'text-anchor': 'top', 'text-optional': true },
      paint: { 'text-color': sym.ink, 'text-halo-color': '#fff', 'text-halo-width': 1.4, 'text-opacity': op },
    },
  ]
}

export const INTERACTIVE_PARTS = ['fill', 'outline-solid', 'outline-dashed', 'outline-dotted', 'line-solid', 'line-dashed', 'line-dotted', 'points']
