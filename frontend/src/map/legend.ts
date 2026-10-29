// What the legend shows: built from the features in the visible layers.
import type { LayerT, Status } from '../api'

export interface LegendData {
  routes: Status[]
  services: string[]
  statuses: Status[]
  areas: string[]
  imagery: LayerT[]
}

const ORDER: Status[] = ['ok', 'partial', 'no', 'unknown']

export function legendData(layers: LayerT[], data: Record<string, GeoJSON.FeatureCollection | undefined>): LegendData {
  const routes = new Set<Status>()
  const services = new Set<string>()
  const statuses = new Set<Status>()
  const areas = new Set<string>()
  for (const l of layers) {
    const fc = data[l.id]
    if (!fc) continue
    for (const f of fc.features) {
      const t = String(f.properties?.risa_type || '')
      const s = (String(f.properties?.risa_status || '') || 'unknown') as Status
      const g = f.geometry?.type || ''
      if (g.includes('LineString')) routes.add(s)
      else if (g.includes('Polygon')) areas.add(t || 'other')
      else {
        services.add(t || 'other')
        statuses.add(s)
      }
    }
  }
  return {
    routes: ORDER.filter((s) => routes.has(s)),
    services: [...services].sort(),
    statuses: ORDER.filter((s) => statuses.has(s)),
    areas: [...areas],
    imagery: layers.filter((l) => ['raster', 'cog_url', 'xyz', 'wms'].includes(l.kind)),
  }
}
