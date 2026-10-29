// EXAMPLE AI ANALYSIS OUTPUT. No model runs yet: this module makes the kind of result an
// imagery and field-data model would return (plan: "AI candidates from imagery as a review
// layer"), so the interface can be shown and discussed. Shelter counts and photo notes are
// made up, seeded from the site's own data so they stay the same between visits. Gaps, flood
// exposure and access come from the real features, checked against Sphere minimum standards.

import area from '@turf/area'
import type { LayerT } from './api'

export type Severity = 'high' | 'medium' | 'low'

export interface Ref {
  layerId: string
  id: string
  geometry: GeoJSON.Geometry
}

export interface Finding {
  id: string
  severity: Severity
  topic: string
  title: string
  detail: string
  basis: string
  action?: string
  refs: Ref[]
}

export interface BlockEstimate {
  label: string
  shelters: number
  perHa: number
  confidence: number
  people: number
  nearestWater: number | null
  ref: Ref
}

export interface Analysis {
  brief: string[]
  imagery: {
    layer: string
    capturedAt: string | null
    shelters: number
    people: [number, number]
    confidence: number
    blocks: BlockEstimate[]
    waterHa: number
    caveat: string
    /** 'detected': counts from the shelter detection layer; 'example': made up from block areas */
    source: 'detected' | 'example'
  } | null
  findings: Finding[]
  priorities: { text: string; finding: string }[]
  inputs: string[]
}

// Sphere minimum standards (2018)
const SPHERE_PEOPLE_PER_TAP = 250
const SPHERE_MAX_WATER_DISTANCE = 500
const HOUSEHOLD = [4.2, 5.0]
const SERVICES = ['water', 'latrine', 'hand', 'health', 'cfs', 'dist', 'storage', 'registration', 'kitchen']

// ---- geometry in local metres -------------------------------------------------------

type XY = [number, number]
let lat0 = 0
let lon0 = 0
const toXY = ([lon, lat]: number[]): XY => [(lon - lon0) * Math.cos((lat0 * Math.PI) / 180) * 111320, (lat - lat0) * 110540]

function parts(g: GeoJSON.Geometry): { rings: XY[][]; lines: XY[][]; points: XY[] } {
  const out = { rings: [] as XY[][], lines: [] as XY[][], points: [] as XY[] }
  if (g.type === 'Point') out.points.push(toXY(g.coordinates))
  else if (g.type === 'MultiPoint') out.points.push(...g.coordinates.map(toXY))
  else if (g.type === 'LineString') out.lines.push(g.coordinates.map(toXY))
  else if (g.type === 'MultiLineString') out.lines.push(...g.coordinates.map((l) => l.map(toXY)))
  else if (g.type === 'Polygon') out.rings.push(g.coordinates[0].map(toXY))
  else if (g.type === 'MultiPolygon') out.rings.push(...g.coordinates.map((p) => p[0].map(toXY)))
  return out
}

function inRing([x, y]: XY, ring: XY[]) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

function segDist([px, py]: XY, [ax, ay]: XY, [bx, by]: XY) {
  const dx = bx - ax
  const dy = by - ay
  const t = dx || dy ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy))) : 0
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy))
}

function pointToGeom(p: XY, g: GeoJSON.Geometry) {
  const { rings, lines, points } = parts(g)
  if (rings.some((r) => inRing(p, r))) return 0
  let d = Infinity
  for (const path of [...rings, ...lines]) for (let i = 1; i < path.length; i++) d = Math.min(d, segDist(p, path[i - 1], path[i]))
  for (const q of points) d = Math.min(d, Math.hypot(p[0] - q[0], p[1] - q[1]))
  return d
}

const vertices = (g: GeoJSON.Geometry) => {
  const { rings, lines, points } = parts(g)
  return [...rings.flat(), ...lines.flat(), ...points]
}

/** Approximate: closest vertex of either shape to the other shape. */
function geomDist(a: GeoJSON.Geometry, b: GeoJSON.Geometry) {
  let d = Infinity
  for (const v of vertices(a)) d = Math.min(d, pointToGeom(v, b))
  for (const v of vertices(b)) d = Math.min(d, pointToGeom(v, a))
  return d
}

function centroid(g: GeoJSON.Geometry): XY {
  const vs = vertices(g)
  return [vs.reduce((s, v) => s + v[0], 0) / vs.length, vs.reduce((s, v) => s + v[1], 0) / vs.length]
}

// ---- seeded numbers, so the made-up figures don't change on every render ------------

function seeded(s: string) {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619)
  return () => {
    h = (h + 0x6d2b79f5) | 0
    let t = Math.imul(h ^ (h >>> 15), 1 | h)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const round = (n: number, to: number) => Math.round(n / to) * to
const fmt = (n: number) => n.toLocaleString('en')
const m = (d: number) => `${Math.round(d)} m`
const obsCount = (n: number) => `${n} field observation${n === 1 ? '' : 's'}`
const list = (xs: string[]) => (xs.length <= 1 ? xs.join('') : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`)

// ---- the "model" -------------------------------------------------------------------

interface F {
  ref: Ref
  type: string
  status: string
  label: string
  /** Detected blocks: their shelter count and confidence */
  count?: number
  conf?: number
  note: string
  observed: string
  photos: number
  layer: LayerT
}

export function analyse(siteName: string, layers: LayerT[], data: Record<string, GeoJSON.FeatureCollection | undefined>,
  typeLabel: (t: string) => string, today = new Date()): Analysis | null {
  const feats: F[] = []
  // Shelter detection: only the latest run counts, and never rejected suggestions
  const detection = layers.filter((l) => l.kind === 'analysis' && l.status === 'ready')
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0]
  const detected: { conf: number }[] = []
  for (const l of layers) {
    if (l.kind === 'analysis' && l !== detection) continue
    for (const f of data[l.id]?.features || []) {
      if (!f.geometry) continue
      const p = f.properties || {}
      if (l.kind === 'analysis') {
        if (p.review === 'rejected') continue
        if (p.ai_class === 'shelter') detected.push({ conf: Number(p.confidence) || 0 })
        if (p.ai_class !== 'block') continue
      }
      const photos = typeof p._photos === 'string' ? JSON.parse(p._photos) : p._photos || []
      feats.push({
        ref: { layerId: l.id, id: String(p.risa_id ?? f.id), geometry: f.geometry },
        type: String(p.risa_type || ''), status: String(p.risa_status || ''), label: String(p.risa_label || ''),
        count: p.shelters != null ? Number(p.shelters) : undefined, conf: p.confidence != null ? Number(p.confidence) : undefined,
        note: String(p.note || ''), observed: String(p.observed || p._submission_time || p.observed_at || '').slice(0, 10),
        photos: photos.length, layer: l,
      })
    }
  }
  if (!feats.length) return null
  ;[lon0, lat0] = (() => {
    const c = feats[0].ref.geometry
    const v = c.type === 'Point' ? c.coordinates : c.type === 'Polygon' ? c.coordinates[0][0] : c.type === 'LineString' ? c.coordinates[0] : [0, 0]
    return [v[0], v[1]]
  })()

  const isPoint = (f: F) => f.ref.geometry.type === 'Point' || f.ref.geometry.type === 'MultiPoint'
  const services = feats.filter((f) => SERVICES.includes(f.type))
  const allBlocks = feats.filter((f) => f.type === 'block' && f.ref.geometry.type.includes('Polygon'))
  // Detected blocks replace drawn ones, so the same ground isn't counted twice
  const detectedBlocks = allBlocks.filter((f) => f.layer.kind === 'analysis')
  const blocks = detectedBlocks.length ? detectedBlocks : allBlocks
  const hazards = feats.filter((f) => (f.type === 'flood' || f.type === 'debris') && f.ref.geometry.type.includes('Polygon'))
  const routes = feats.filter((f) => f.type === 'route')
  const water = services.filter((f) => f.type === 'water')
  const waterOk = water.filter((f) => f.status === 'ok')
  const name = (f: F) => f.label || typeLabel(f.type)
  const findings: Finding[] = []

  // Imagery: shelters per block (made up), people from household size
  const raster = layers.find((l) => l.kind === 'raster' || l.kind === 'cog_url')
  let imagery: Analysis['imagery'] = null
  const blockEst: BlockEstimate[] = blocks.map((b) => {
    const r = seeded(siteName + b.label + b.ref.id)
    const ha = area({ type: 'Feature', geometry: b.ref.geometry, properties: {} }) / 10000
    const shelters = b.count ?? Math.max(1, Math.round(ha * Math.round(170 + r() * 130)))
    const perHa = Math.round(shelters / Math.max(ha, 0.01))
    const c = centroid(b.ref.geometry)
    const nearest = waterOk.length ? Math.min(...waterOk.map((w) => pointToGeom(c, w.ref.geometry))) : null
    return { label: name(b), shelters, perHa, confidence: b.conf ?? 0.72 + r() * 0.2, people: Math.round(shelters * (HOUSEHOLD[0] + HOUSEHOLD[1]) / 2), nearestWater: nearest, ref: b.ref }
  })
  if (raster && blockEst.length) {
    // With a detection run, the total is every shelter it found (in blocks or not)
    const shelters = detected.length || blockEst.reduce((s, b) => s + b.shelters, 0)
    const latestObs = feats.map((f) => f.observed).filter(Boolean).sort().pop()
    const ageDays = raster.captured_at ? (today.getTime() - new Date(raster.captured_at).getTime()) / 864e5 : 0
    imagery = {
      layer: raster.name,
      capturedAt: raster.captured_at,
      shelters,
      people: [round(shelters * HOUSEHOLD[0], 100), round(shelters * HOUSEHOLD[1], 100)],
      confidence: detected.length
        ? detected.reduce((s, d) => s + d.conf, 0) / detected.length
        : blockEst.reduce((s, b) => s + b.confidence * b.shelters, 0) / shelters,
      source: detected.length ? 'detected' : 'example',
      blocks: blockEst,
      waterHa: hazards.filter((h) => h.type === 'flood').reduce((s, h) => s + area({ type: 'Feature', geometry: h.ref.geometry, properties: {} }), 0) / 10000,
      caveat: ageDays > 30
        ? `The imagery is from ${raster.captured_at}${latestObs ? `, field observations from ${latestObs}` : ''}. Shelters may have moved since: fly a new survey before using these counts.`
        : 'Counts are of roofs seen from above. Shared and multi-storey shelters are undercounted.',
    }
  }
  const people = imagery ? (imagery.people[0] + imagery.people[1]) / 2 : null

  // Water: quantity per working point and distance
  if (water.length) {
    const broken = water.filter((f) => f.status === 'no' || f.status === 'partial')
    if (people && waterOk.length) {
      const per = Math.round(people / waterOk.length)
      if (per > SPHERE_PEOPLE_PER_TAP) {
        findings.push({
          id: 'water-load', severity: per > SPHERE_PEOPLE_PER_TAP * 2 ? 'high' : 'medium', topic: 'Water',
          title: `About ${fmt(round(per, 50))} people per working water point`,
          detail: `${waterOk.length} of ${water.length} water points work for an estimated ${fmt(round(people, 100))} people. Sphere's guide is ${SPHERE_PEOPLE_PER_TAP} people per tap.`,
          basis: `${obsCount(water.length)}, shelter count from imagery`,
          action: `Repair ${list(broken.map(name).slice(0, 3)) || 'the broken water points'} or add water trucking`,
          refs: [...waterOk, ...broken].map((f) => f.ref),
        })
      }
    } else if (!waterOk.length) {
      findings.push({
        id: 'water-none', severity: 'high', topic: 'Water', title: 'No working water point reported',
        detail: `All ${water.length} water points observed are partly or not working.`, basis: obsCount(water.length),
        action: 'Start water trucking and check the water points again', refs: water.map((f) => f.ref),
      })
    }
    const far = blockEst.filter((b) => b.nearestWater != null && b.nearestWater > SPHERE_MAX_WATER_DISTANCE / 2)
      .sort((a, b) => b.nearestWater! - a.nearestWater!)
    if (far.length) {
      const worst = far[0]
      findings.push({
        id: 'water-distance', severity: worst.nearestWater! > SPHERE_MAX_WATER_DISTANCE ? 'high' : 'medium', topic: 'Water',
        title: `${list(far.map((b) => b.label))}: far from working water`,
        detail: far.map((b) => `${b.label} ${m(b.nearestWater!)}`).join(' · ') + `, from the middle of the block to the nearest working point. Sphere's maximum is ${SPHERE_MAX_WATER_DISTANCE} m.`,
        basis: 'Block outlines and water point locations',
        action: `Put the next water point between ${list(far.slice(0, 2).map((b) => b.label))}`,
        refs: far.map((b) => b.ref),
      })
    }
  }

  // Flood and debris: exposed blocks and services
  for (const h of hazards) {
    const exposedBlocks = blocks.filter((b) => geomDist(b.ref.geometry, h.ref.geometry) < 15)
    const exposedServices = services.filter((s) => geomDist(s.ref.geometry, h.ref.geometry) < 30)
    if (!exposedBlocks.length && !exposedServices.length) continue
    const est = blockEst.filter((b) => exposedBlocks.some((x) => x.ref.id === b.ref.id)).reduce((s, b) => s + b.people, 0)
    findings.push({
      id: `hazard-${h.ref.id}`, severity: exposedBlocks.length ? 'high' : 'medium', topic: h.type === 'flood' ? 'Flood' : 'Debris',
      title: exposedBlocks.length ? `${list(exposedBlocks.map(name))} border the ${name(h).toLowerCase()}` : `Services next to the ${name(h).toLowerCase()}`,
      detail: [
        exposedBlocks.length && est ? `About ${fmt(round(est, 100))} people live within 15 m of it.` : '',
        exposedServices.length ? `Within 30 m: ${list(exposedServices.map((s) => `${name(s)} (${typeLabel(s.type).toLowerCase()})`))}.` : '',
      ].filter(Boolean).join(' '),
      basis: 'Mapped hazard outline, block outlines and service locations',
      action: exposedServices.some((s) => s.type === 'latrine') ? `Check ${list(exposedServices.filter((s) => s.type === 'latrine').map(name))} for overflow into the water` : `Plan relocation for ${list(exposedBlocks.map(name))} if the water rises`,
      refs: [h, ...exposedBlocks, ...exposedServices].map((f) => f.ref),
    })
  }

  // Access
  if (routes.length) {
    const open = routes.filter((r) => r.status === 'ok')
    const closed = routes.filter((r) => r.status === 'no')
    const partial = routes.filter((r) => r.status === 'partial')
    if (open.length <= 1) {
      findings.push({
        id: 'access', severity: open.length ? 'medium' : 'high', topic: 'Access',
        title: open.length ? `${name(open[0])} is the only fully open route` : 'No fully open access route',
        detail: [
          closed.length ? `Closed: ${closed.map((r) => `${name(r)}${r.note ? ` (${r.note.toLowerCase()})` : ''}`).join(', ')}.` : '',
          partial.length ? `Restricted: ${partial.map((r) => `${name(r)}${r.note ? ` (${r.note.toLowerCase()})` : ''}`).join(', ')}.` : '',
          open.length ? 'If it closes, trucks cannot reach the site.' : '',
        ].filter(Boolean).join(' '),
        basis: `${routes.length} route observations`,
        action: partial.length ? `Clear ${name(partial[0])} to give a second vehicle route` : 'Find a second vehicle route',
        refs: routes.map((r) => r.ref),
      })
    }
  }

  // Other services not working
  for (const t of ['health', 'latrine', 'hand']) {
    const of = services.filter((s) => s.type === t)
    const bad = of.filter((s) => s.status === 'no' || s.status === 'partial')
    if (!bad.length) continue
    findings.push({
      id: `svc-${t}`, severity: t === 'health' || bad.some((b) => b.status === 'no') ? 'medium' : 'low', topic: typeLabel(t),
      title: `${bad.length} of ${of.length} ${typeLabel(t).toLowerCase()}${of.length > 1 ? 's' : ''} not fully working`,
      detail: bad.map((b) => `${name(b)}: ${b.status === 'no' ? 'not working' : 'partly'}${b.note ? `, ${b.note.toLowerCase()}` : ''}`).join(' · '),
      basis: obsCount(of.length),
      refs: bad.map((b) => b.ref),
    })
  }

  // Data quality
  const obs = services.filter((s) => s.layer.kind === 'kobo' || s.layer.kind === 'vector')
  const unassessed = feats.filter((f) => isPoint(f) && (!f.status || f.status === 'unknown'))
  const noPhoto = obs.filter((s) => !s.photos)
  const stale = obs.filter((s) => s.observed && (today.getTime() - new Date(s.observed).getTime()) / 864e5 > 3)
  const dupes: F[] = []
  for (let i = 0; i < services.length; i++) for (let j = i + 1; j < services.length; j++) {
    const a = services[i], b = services[j]
    if (a.type === b.type && geomDist(a.ref.geometry, b.ref.geometry) < 10) dupes.push(a, b)
  }
  const dq = [
    unassessed.length ? `${unassessed.length} without a status` : '',
    dupes.length ? `${dupes.length / 2} possible duplicate${dupes.length > 2 ? 's' : ''} (same type, under 10 m apart)` : '',
    stale.length ? `${stale.length} observed more than 3 days ago` : '',
    noPhoto.length ? `${noPhoto.length} of ${obs.length} observations have no photo, so the status can't be checked` : '',
  ].filter(Boolean)
  if (dq.length) {
    findings.push({
      id: 'data', severity: 'low', topic: 'Data', title: 'Check before publishing', detail: dq.join(' · ') + '.',
      basis: 'All field observations', refs: [...unassessed, ...dupes, ...stale].map((f) => f.ref),
    })
  }

  const order: Record<Severity, number> = { high: 0, medium: 1, low: 2 }
  findings.sort((a, b) => order[a.severity] - order[b.severity])

  // Brief
  const brief: string[] = []
  if (imagery) {
    brief.push(`${siteName} has an estimated ${fmt(imagery.people[0])}–${fmt(imagery.people[1])} people in about ${fmt(round(imagery.shelters, 10))} shelters across ${blocks.length} blocks, counted on imagery from ${imagery.capturedAt || 'the latest survey'}.`)
  }
  if (water.length) {
    const s = `${waterOk.length} of ${water.length} water points work`
    brief.push(people && waterOk.length ? `${s}, about ${fmt(round(people / waterOk.length, 50))} people for each, well above Sphere's ${SPHERE_PEOPLE_PER_TAP}.` : `${s}.`)
  }
  const peopleNear = (f: Finding) => { const x = f.detail.match(/^About [^.]+\./); return x ? ` ${x[0]}` : '' }
  const flood = findings.find((f) => f.topic === 'Flood')
  if (flood) brief.push(`${flood.title}.${peopleNear(flood)}`)
  const access = findings.find((f) => f.id === 'access')
  if (access) brief.push(`${access.title}.`)

  const inputs = [
    ...layers.filter((l) => l.kind === 'raster' || l.kind === 'cog_url').map((l) => `${l.name}${l.resolution_cm ? `, ${l.resolution_cm} cm/px` : ''}`),
    ...layers.filter((l) => ['kobo', 'vector', 'annotations'].includes(l.kind) && data[l.id]?.features.length).map((l) => `${l.name}, ${data[l.id]!.features.length} features`),
  ]
  const priorities = findings.filter((f) => f.action).slice(0, 4).map((f) => ({ text: f.action!, finding: f.id }))
  return { brief, imagery, findings, priorities, inputs }
}

// ---- photo notes ------------------------------------------------------------------

const NOTES: Record<string, Partial<Record<string, string>>> = {
  water: { ok: 'Tap stand with water flowing; short queue, jerrycans clean.', partial: 'One of three taps flowing; long queue, puddling around the apron.', no: 'Tap stand dry; tank lid missing, no water in the pipe.' },
  latrine: { ok: 'Latrine block intact; doors lock, lighting visible.', partial: 'Two cubicles out of use; slab cracked, no lock on the women’s side.', no: 'Superstructure collapsed; pit full, area taped off.' },
  hand: { ok: 'Handwashing station with soap and water.', partial: 'Water but no soap at the station.', no: 'Station empty, tap broken.' },
  health: { ok: 'Tent clinic open; patients waiting under shade.', partial: 'Clinic open, sign shows morning hours only.', no: 'Clinic tent empty and closed.' },
  dist: { ok: 'Distribution area fenced, queue lines marked.', partial: 'Distribution under way, crowding at the gate.', no: 'Distribution site empty.' },
  cfs: { ok: 'Children’s activity tent in use, fenced area.' },
  registration: { ok: 'Registration desk staffed, people queuing.' },
  storage: { ok: 'Storage tent intact, stock on pallets off the ground.' },
  gate: { ok: 'Entrance open, no obstruction.' },
  choke: { partial: 'Narrow crossing; market stalls block half the road.', no: 'Crossing blocked.' },
}

/** What an image model might say about an observation's photo. Made up. */
export function photoNote(type: string, status: string) {
  return NOTES[type]?.[status] || NOTES[type]?.ok || ''
}
