// API client and types. The edit key for the current response is sent as X-Edit-Key.

export type Status = 'ok' | 'partial' | 'no' | 'unknown'

export interface Basemap {
  id: string
  name: string
  kind: 'style' | 'raster' | 'pmtiles' | 'none'
  url?: string
  maxzoom?: number
  online: boolean
  attribution: string
}

export interface Symbology {
  status: Record<Status, { label: string; short: string; color: string; line: string; symbol: string }>
  ink: string
  hazards: Record<string, { label: string; color: string; fill: string }>
  types: Record<string, { glyph: string; label: string }>
  analysis?: Record<string, { color: string }>
}

export interface Config {
  symbology: Symbology
  basemaps: Basemap[]
  glyphs: string
  allowed_servers: string[]
  create_key_required: boolean
  read_only_public: boolean
  chunk_size: number
  source_url: string
  licence: string
}

export interface ResponseT {
  id: string
  slug: string
  name: string
  hazard: string
  country: string
  glide: string
  start_date: string | null
  language: string
  private: boolean
  can_edit: boolean
  sites?: SiteT[] | number
}

export interface LayerT {
  id: string
  name: string
  kind: 'raster' | 'vector' | 'kobo' | 'annotations' | 'xyz' | 'wms' | 'cog_url' | 'analysis'
  status: 'processing' | 'ready' | 'failed'
  error: string
  style: { color?: string; opacity?: number; label_field?: string; preset?: string }
  z_order: number
  visible_default: boolean
  attribution: string
  licence: string
  captured_at: string | null
  resolution_cm: number | null
  bbox: [number, number, number, number] | null
  online_only: boolean
  updated_at: string
  url?: string
  download?: string
  feature_count?: number | null
  analysis?: {
    source_layer: string
    model: string
    simulated: boolean
    progress?: { step: string; pct: number }
    counts?: { shelter: number; building: number; block: number }
    aoi: [number, number, number, number]
  }
  kobo?: {
    server: string
    asset_uid: string
    asset_name: string
    last_synced_at: string | null
    last_error: string
    submissions: number
    auto_sync: boolean
  }
}

export interface Glance {
  value: string
  label: string
  tbc: boolean
}

export interface ProductVersionT {
  n: number
  status: 'processing' | 'ready' | 'failed'
  error: string
  rendered_at: string
  pdf: string | null
}

export interface ViewLayer {
  id: string
  visible: boolean
  opacity: number
}

export interface ProductView {
  bounds?: [number, number, number, number]
  center?: [number, number]
  zoom?: number
  bearing?: number
  basemap?: string
  layers?: ViewLayer[]
}

export interface ProductT {
  id: string
  site: string
  kind: string
  title: string
  code: string
  version_label: string
  page_size: 'A3' | 'A4'
  view: ProductView
  key_message: string
  glance: Glance[]
  authority: string
  sources: string
  disclaimer: string
  credits: string
  updated_at: string
  versions: ProductVersionT[]
  preview: { status: '' | 'processing' | 'ready' | 'failed'; error: string; at: string | null; url: string | null }
}

export interface SiteT {
  id: string
  slug: string
  name: string
  place: string
  kind: string
  default_view: { center?: [number, number]; zoom?: number; bearing?: number }
  notes: string
}

export interface SiteFull extends SiteT {
  response: ResponseT
  layers: LayerT[]
  products: ProductT[]
}

export interface Summary {
  services: { type: string; label: string; ok: number; partial: number; no: number; unknown: number; total: number }[]
  routes: Record<Status, number>
  route_list: { label: string; status: Status; note: string }[]
  shelters: number
  glance: Glance[]
  features: number
  pending_review?: number
}

export interface KoboQuestion {
  path: string
  name: string
  type: string
  label: string
  choices?: { name: string; label: string }[]
}

export interface FieldMap {
  geo: string
  type: string
  status: string
  label: string
  popup: string[]
  sensitive: string[]
  type_map?: Record<string, string>
  status_map?: Record<string, string>
}

// ---- edit keys --------------------------------------------------------------------

const KEY_PREFIX = 'risa-edit-key:'
let currentKey = ''

export function setCurrentResponse(slug: string | undefined) {
  currentKey = slug ? localStorage.getItem(KEY_PREFIX + slug) || '' : ''
}

export function saveEditKey(slug: string, key: string) {
  localStorage.setItem(KEY_PREFIX + slug, key)
  currentKey = key
}

export function forgetEditKey(slug: string) {
  localStorage.removeItem(KEY_PREFIX + slug)
  currentKey = ''
}

export function getEditKey(slug: string) {
  return localStorage.getItem(KEY_PREFIX + slug) || ''
}

// ---- fetch ----------------------------------------------------------------------------

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown; headers?: Record<string, string>; raw?: BodyInit } = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json', ...(opts.headers || {}) }
  if (currentKey) headers['X-Edit-Key'] = currentKey
  let body: BodyInit | undefined
  if (opts.raw !== undefined) body = opts.raw
  else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }
  const r = await fetch(`/api${path}`, { method: opts.method || (body ? 'POST' : 'GET'), headers, body })
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try {
      const j = await r.json()
      if (j.detail) msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {
      /* not json */
    }
    throw new ApiError(r.status, msg)
  }
  const ct = r.headers.get('content-type') || ''
  return (ct.includes('json') ? r.json() : r.text()) as Promise<T>
}

export function absUrl(u: string) {
  return new URL(u, window.location.origin).toString()
}

// ---- uploads: chunked and resumable ------------------------------------------------

export async function uploadFile(
  siteId: string,
  file: File,
  meta: { name: string; captured_at?: string | null; attribution?: string },
  onProgress: (fraction: number) => void,
  signal?: AbortSignal,
): Promise<LayerT> {
  const start = await api<{ id: string; chunk_size: number; parts: number }>(`/sites/${siteId}/uploads`, {
    body: { filename: file.name, size: file.size, name: meta.name, captured_at: meta.captured_at || null, attribution: meta.attribution || '' },
  })
  const { id, chunk_size, parts } = start
  let done = 0
  const queue = Array.from({ length: parts }, (_, i) => i)
  const sendPart = async (n: number) => {
    const blob = file.slice(n * chunk_size, Math.min(file.size, (n + 1) * chunk_size))
    for (let attempt = 0; ; attempt++) {
      if (signal?.aborted) throw new Error('Upload cancelled')
      try {
        await api(`/uploads/${id}/parts/${n}`, { method: 'PUT', raw: blob, headers: { 'Content-Type': 'application/octet-stream' } })
        break
      } catch (e) {
        // Flaky Wi-Fi: back off and retry the same part
        if (attempt >= 8 || (e instanceof ApiError && e.status < 500 && e.status !== 0)) throw e
        await new Promise((res) => setTimeout(res, Math.min(30000, 1000 * 2 ** attempt)))
      }
    }
    done++
    onProgress(done / parts)
  }
  const workers = Array.from({ length: Math.min(3, parts) }, async () => {
    while (queue.length) await sendPart(queue.shift()!)
  })
  await Promise.all(workers)
  return api<LayerT>(`/uploads/${id}/complete`, { method: 'POST' })
}
