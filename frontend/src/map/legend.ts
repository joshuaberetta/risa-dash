// What the legend shows: built from the features in the visible layers.
import type { LayerT, Status } from '../api'

export interface LegendData {
  routes: Status[]
  services: string[]
  statuses: Status[]
  areas: string[]
  imagery: LayerT[]
  /** Imagery-analysis classes shown (not rejected), and whether any are simulated */
  analysis: { classes: string[]; simulated: boolean; suggested: boolean }
}

const ORDER: Status[] = ['ok', 'partial', 'no', 'unknown']

export function legendData(layers: LayerT[], data: Record<string, GeoJSON.FeatureCollection | undefined>): LegendData {
  const routes = new Set<Status>()
  const services = new Set<string>()
  const statuses = new Set<Status>()
  const areas = new Set<string>()
  const aClasses = new Set<string>()
  let simulated = false
  let suggested = false
  for (const l of layers) {
    const fc = data[l.id]
    if (!fc) continue
    if (l.kind === 'analysis') {
      simulated ||= !!l.analysis?.simulated
      for (const f of fc.features) {
        const review = String(f.properties?.review || 'suggested')
        if (review === 'rejected') continue
        suggested ||= review === 'suggested'
        aClasses.add(String(f.properties?.ai_class || f.properties?.risa_type || 'shelter'))
      }
      continue
    }
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
    analysis: { classes: ['shelter', 'building', 'block', 'boundary'].filter((c) => aClasses.has(c)), simulated, suggested },
  }
}
