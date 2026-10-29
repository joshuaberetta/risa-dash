// Drawing and shape editing with Terra Draw. Plain JS, no WASM: points, lines and
// polygons with snapping, plus vertex editing of an existing feature.

import type { Map as MLMap } from 'maplibre-gl'
import {
  TerraDraw, TerraDrawLineStringMode, TerraDrawPointMode, TerraDrawPolygonMode, TerraDrawRenderMode, TerraDrawSelectMode,
} from 'terra-draw'
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter'

export type DrawMode = 'static' | 'point' | 'linestring' | 'polygon' | 'select'

const INK = '#1D232B'
const ACCENT = '#2F74B5'

export function createDraw(map: MLMap, onDrawn: (id: string, geometry: GeoJSON.Geometry) => void) {
  const editable = { draggable: true, coordinates: { midpoints: true, draggable: true, deletable: true } }
  const draw = new TerraDraw({
    adapter: new TerraDrawMapLibreGLAdapter({ map: map as never, prefixId: 'td' }),
    modes: [
      new TerraDrawRenderMode({ modeName: 'static', styles: {} }),
      new TerraDrawPointMode({ styles: { pointColor: ACCENT, pointOutlineColor: '#fff', pointWidth: 7, pointOutlineWidth: 2 } }),
      new TerraDrawLineStringMode({ snapping: { toCoordinate: true }, styles: { lineStringColor: ACCENT, lineStringWidth: 3 } }),
      new TerraDrawPolygonMode({ snapping: { toCoordinate: true }, styles: { fillColor: ACCENT, fillOpacity: 0.2, outlineColor: ACCENT, outlineWidth: 2 } }),
      new TerraDrawSelectMode({
        flags: { polygon: { feature: editable }, linestring: { feature: editable }, point: { feature: { draggable: true } } },
        styles: { selectedPolygonColor: ACCENT, selectedPolygonOutlineColor: INK, selectedLineStringColor: ACCENT, selectionPointColor: '#fff', selectionPointOutlineColor: INK },
      }),
    ],
  })
  draw.start()
  draw.setMode('static')
  draw.on('finish', (id, ctx) => {
    if (ctx.action !== 'draw') return
    const f = draw.getSnapshotFeature(id)
    if (f) onDrawn(String(id), f.geometry as GeoJSON.Geometry)
  })
  return draw
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
