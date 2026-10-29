// Drawing and shape editing with Terra Draw. Plain JS, no WASM: points, lines and
// polygons with snapping, plus vertex editing of an existing feature.

import area from '@turf/area'
import length from '@turf/length'
import type { Map as MLMap } from 'maplibre-gl'
import {
  TerraDraw, TerraDrawLineStringMode, TerraDrawPointMode, TerraDrawPolygonMode, TerraDrawRenderMode, TerraDrawSelectMode,
} from 'terra-draw'
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter'

export type DrawMode = 'static' | 'point' | 'linestring' | 'polygon' | 'select' | 'measure-line' | 'measure-area'

const INK = '#1D232B'
const ACCENT = '#2F74B5'
const MEASURE = '#1D232B'

export interface Measurement {
  kind: 'line' | 'area'
  /** metres: the line, or the area's perimeter */
  length: number
  /** square metres, for areas */
  area: number
  done: boolean
}

export const isMeasureMode = (m: string) => m.startsWith('measure-')

/** Geodesic length and area of what's being measured, in metres and m². */
function measure(f: GeoJSON.Feature): Omit<Measurement, 'done'> | null {
  const g = f.geometry
  if (g.type === 'LineString') return g.coordinates.length > 1 ? { kind: 'line', length: length(f) * 1000, area: 0 } : null
  if (g.type === 'Polygon') {
    const ring = { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: g.coordinates[0] } } as GeoJSON.Feature
    return { kind: 'area', length: length(ring) * 1000, area: g.coordinates[0].length > 3 ? area(f) : 0 }
  }
  return null
}

export function formatLength(m: number) {
  return m < 1000 ? `${m < 100 ? m.toFixed(1) : Math.round(m)} m` : `${(m / 1000).toFixed(m < 10000 ? 2 : 1)} km`
}

export function formatArea(m2: number) {
  return m2 < 10000 ? `${Math.round(m2).toLocaleString()} m²` : `${(m2 / 10000).toFixed(m2 < 1e6 ? 2 : 1)} ha`
}

export function createDraw(
  map: MLMap,
  onDrawn: (id: string, geometry: GeoJSON.Geometry) => void,
  onMeasure: (m: Measurement | null) => void,
) {
  const editable = { draggable: true, coordinates: { midpoints: true, draggable: true, deletable: true } }
  const draw = new TerraDraw({
    adapter: new TerraDrawMapLibreGLAdapter({ map: map as never, prefixId: 'td' }),
    modes: [
      new TerraDrawRenderMode({ modeName: 'static', styles: {} }),
      new TerraDrawPointMode({ styles: { pointColor: ACCENT, pointOutlineColor: '#fff', pointWidth: 7, pointOutlineWidth: 2 } }),
      new TerraDrawLineStringMode({ snapping: { toCoordinate: true }, styles: { lineStringColor: ACCENT, lineStringWidth: 3 } }),
      new TerraDrawPolygonMode({ snapping: { toCoordinate: true }, styles: { fillColor: ACCENT, fillOpacity: 0.2, outlineColor: ACCENT, outlineWidth: 2 } }),
      // Measuring: same tools, nothing is saved
      new TerraDrawLineStringMode({ modeName: 'measure-line', styles: { lineStringColor: MEASURE, lineStringWidth: 2.5, closingPointColor: '#fff', closingPointOutlineColor: MEASURE } }),
      new TerraDrawPolygonMode({ modeName: 'measure-area', styles: { fillColor: MEASURE, fillOpacity: 0.12, outlineColor: MEASURE, outlineWidth: 2.5, closingPointColor: '#fff', closingPointOutlineColor: MEASURE } }),
      new TerraDrawSelectMode({
        flags: { polygon: { feature: editable }, linestring: { feature: editable }, point: { feature: { draggable: true } } },
        styles: { selectedPolygonColor: ACCENT, selectedPolygonOutlineColor: INK, selectedLineStringColor: ACCENT, selectionPointColor: '#fff', selectionPointOutlineColor: INK },
      }),
    ],
  })
  draw.start()
  draw.setMode('static')
  // The last finished measurement: starting a new one clears it, so there's one at a time.
  // (Terra Draw's guide points share the mode name, so match on shapes and ids only.)
  let lastMeasure: string | null = null
  const isShape = (f?: { geometry: { type: string } } | null) => !!f && (f.geometry.type === 'LineString' || f.geometry.type === 'Polygon')
  draw.on('change', (ids, type) => {
    if (type === 'delete' || !isMeasureMode(draw.getMode())) return
    for (const id of ids) {
      if (id === undefined || id === null) continue
      const f = draw.getSnapshotFeature(id)
      if (!isShape(f) || !isMeasureMode(String(f!.properties?.mode || ''))) continue
      if (lastMeasure && lastMeasure !== String(id) && draw.getSnapshotFeature(lastMeasure)) {
        draw.removeFeatures([lastMeasure])
        lastMeasure = null
      }
      const m = measure(f as GeoJSON.Feature)
      if (m) onMeasure({ ...m, done: false })
    }
  })
  draw.on('finish', (id, ctx) => {
    if (ctx.action !== 'draw') return
    const f = draw.getSnapshotFeature(id)
    if (!f) return
    if (isMeasureMode(ctx.mode)) {
      lastMeasure = String(id)
      const m = measure(f as GeoJSON.Feature)
      onMeasure(m ? { ...m, done: true } : null)
      return
    }
    onDrawn(String(id), f.geometry as GeoJSON.Geometry)
  })
  return draw
}

/** Remove measurement shapes (keeps anything else being drawn). */
export function clearMeasurements(draw: TerraDraw) {
  const ids = draw.getSnapshot()
    .filter((f) => f.id != null && isMeasureMode(String(f.properties?.mode || '')) && f.geometry.type !== 'Point')
    .map((f) => f.id!)
  if (ids.length) draw.removeFeatures(ids)
}

const MODE_FOR: Record<string, string> = { Point: 'point', LineString: 'linestring', Polygon: 'polygon' }

/** Put an existing feature into Terra Draw for vertex editing. Multi-geometries edit their first part. */
export function editShape(draw: TerraDraw, id: string, geometry: GeoJSON.Geometry) {
  let g = geometry
  if (g.type === 'MultiPolygon') g = { type: 'Polygon', coordinates: g.coordinates[0] }
  if (g.type === 'MultiLineString') g = { type: 'LineString', coordinates: g.coordinates[0] }
  if (g.type === 'MultiPoint') g = { type: 'Point', coordinates: g.coordinates[0] }
  const mode = MODE_FOR[g.type]
  if (!mode) return false
  draw.clear()
  draw.setMode('select')
  const res = draw.addFeatures([{ id, type: 'Feature', geometry: g as never, properties: { mode } }])
  if (!res[0]?.valid) return false
  draw.selectFeature(id)
  return true
}
