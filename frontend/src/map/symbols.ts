// RISA service symbols drawn on a canvas, matching ~/code/risa/site/assets/sitemap.js:
// working = filled, partly = half-filled, not working = crossed out, not assessed = grey outline.
// Images are made on demand (styleimagemissing) with ids like "risa:water:partial".

import type { Map as MLMap } from 'maplibre-gl'
import type { Status, Symbology } from '../api'

export const SYMBOL_PREFIX = 'risa:'

export function symbolId(type: string, status: string) {
  return `${SYMBOL_PREFIX}${type || 'other'}:${status || 'unknown'}`
}

export function drawSymbol(sym: Symbology, type: string, status: Status, px = 2, size = 26): ImageData {
  const S = size * px
  const c = document.createElement('canvas')
  c.width = c.height = S
  const g = c.getContext('2d')!
  const st = sym.status[status] || sym.status.unknown
  const glyph = sym.types[type]?.glyph ?? sym.types.other.glyph
  const R = 11 * px
  const cx = S / 2
  const cy = S / 2
  g.lineJoin = 'round'
  const ink = sym.ink
  const circle = () => {
    g.beginPath()
    g.arc(cx, cy, R, 0, Math.PI * 2)
  }
  const text = (fill: string) => {
    if (!glyph) return
    g.fillStyle = fill
    g.font = `700 ${12.5 * px}px Inter, system-ui, sans-serif`
    g.textAlign = 'center'
    g.textBaseline = 'middle'
    g.fillText(glyph, cx, cy + 0.6 * px)
  }
  if (status === 'ok') {
    circle()
    g.fillStyle = st.color
    g.fill()
    g.lineWidth = 2 * px
    g.strokeStyle = '#fff'
    g.stroke()
    text('#fff')
  } else if (status === 'partial') {
    circle()
    g.fillStyle = '#fff'
    g.fill()
    g.beginPath()
    g.arc(cx, cy, R, 0, Math.PI)
    g.closePath()
    g.fillStyle = st.color
    g.fill()
    circle()
    g.lineWidth = 3 * px
    g.strokeStyle = st.color
    g.stroke()
    text(ink)
  } else if (status === 'no') {
    circle()
    g.fillStyle = '#fff'
    g.fill()
    g.lineWidth = 3 * px
    g.strokeStyle = st.color
    g.stroke()
    text(st.color)
    g.beginPath()
    g.moveTo(cx - R * 0.72, cy + R * 0.72)
    g.lineTo(cx + R * 0.72, cy - R * 0.72)
    g.stroke()
  } else {
    circle()
    g.fillStyle = '#fff'
    g.fill()
    g.lineWidth = 2.4 * px
    g.strokeStyle = st.color
    g.stroke()
    text(st.color)
  }
  return g.getImageData(0, 0, S, S)
}

export function installSymbols(map: MLMap, sym: Symbology, pixelRatio = 2) {
  map.on('styleimagemissing', (e) => {
    const id = e.id
    if (!id.startsWith(SYMBOL_PREFIX) || map.hasImage(id)) return
    const [, type, status] = id.split(':')
    map.addImage(id, drawSymbol(sym, type, (status as Status) || 'unknown', pixelRatio), { pixelRatio })
  })
}

/** Data URL of a symbol, for legends. */
export function symbolDataUrl(sym: Symbology, type: string, status: Status, px = 2) {
  const img = drawSymbol(sym, type, status, px)
  const c = document.createElement('canvas')
  c.width = img.width
  c.height = img.height
  c.getContext('2d')!.putImageData(img, 0, 0)
  return c.toDataURL()
}
