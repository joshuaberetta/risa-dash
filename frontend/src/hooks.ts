import { useQueries, useQuery } from '@tanstack/react-query'
import { api, type Config, type LayerT, type SiteFull, type Summary } from './api'

export function useConfig() {
  return useQuery({ queryKey: ['config'], queryFn: () => api<Config>('/config'), staleTime: Infinity })
}

export function useConfigData(): Config {
  const { data } = useConfig()
  return data!
}

export function useSite(response?: string, site?: string) {
  return useQuery({
    queryKey: ['site', response, site],
    queryFn: () => api<SiteFull>(`/responses/${response}/sites/${site}`),
    enabled: !!response && !!site,
    // Poll while something is processing
    refetchInterval: (q) => (q.state.data?.layers.some((l) => l.status === 'processing') ||
      q.state.data?.products.some((p) => p.preview?.status === 'processing' || p.versions.some((v) => v.status === 'processing')) ? 3000 : false),
  })
}

export function useSummary(siteId?: string, layerIds?: string[], version?: string) {
  return useQuery({
    queryKey: ['summary', siteId, layerIds?.join(','), version],
    queryFn: () => api<Summary>(`/sites/${siteId}/summary?layers=${(layerIds || []).join(',')}`),
    enabled: !!siteId,
  })
}

const VECTOR = ['vector', 'kobo', 'annotations', 'analysis']

/** GeoJSON for each ready vector layer, keyed by layer id. URLs carry the layer's
 * updated_at, so a change re-fetches and everything else comes from cache. */
export function useLayerData(layers: LayerT[]) {
  const vec = layers.filter((l) => VECTOR.includes(l.kind) && l.status === 'ready' && l.url)
  const results = useQueries({
    queries: vec.map((l) => ({
      queryKey: ['features', l.url],
      queryFn: async () => {
        const r = await fetch(l.url!)
        if (!r.ok) throw new Error(`${r.status}`)
        return (await r.json()) as GeoJSON.FeatureCollection
      },
      staleTime: Infinity,
    })),
  })
  const data: Record<string, GeoJSON.FeatureCollection | undefined> = {}
  vec.forEach((l, i) => (data[l.id] = results[i].data))
  const loading = results.some((r) => r.isLoading)
  return { data, loading }
}
