import type { Config, Status } from '../api'
import type { LegendData } from '../map/legend'
import { symbolDataUrl } from '../map/symbols'

const DASH: Record<string, string> = { ok: '', partial: '8 4', no: '0.1 7', unknown: '' }

function RouteSwatch({ color, status, w = 4 }: { color: string; status: string; w?: number }) {
  return (
    <svg width="34" height="12" viewBox="0 0 34 12" aria-hidden="true">
      <path d="M2 6H32" stroke="#fff" strokeWidth={w + 4} />
      <path d="M2 6H32" stroke={color} strokeWidth={status === 'no' ? w * 1.15 : w} strokeDasharray={DASH[status]} strokeLinecap={status === 'no' ? 'round' : 'butt'} />
    </svg>
  )
}

/** RISA legend. `em` sizing so the print layout can scale it. */
export default function Legend({ config, data, compact }: { config: Config; data: LegendData; compact?: boolean }) {
  const sym = config.symbology
  const h3: React.CSSProperties = { font: '600 0.78em/1.2 Inter, sans-serif', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#4A5A6D', margin: '0.9em 0 0.35em' }
  const row: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: '0.5em', margin: '0.2em 0', fontSize: '0.85em' }
  const areaColor = (t: string) => t === 'flood' ? sym.hazards.flood.fill : t === 'debris' ? sym.hazards.debris.fill : t === 'block' ? 'rgba(200,168,107,0.45)' : 'rgba(59,91,122,0.3)'
  const areaStroke = (t: string) => t === 'flood' ? sym.hazards.flood.color : t === 'debris' ? sym.hazards.debris.color : '#8C939C'
  const empty = !data.routes.length && !data.services.length && !data.areas.length && !data.analysis.classes.length
  return (
    <div style={{ fontFamily: 'Inter, sans-serif', color: sym.ink }}>
      {empty && <p style={{ ...row, color: '#8C939C' }}>No mapped features yet</p>}
      {data.routes.length > 0 && (
        <>
          <h3 style={h3}>Access routes</h3>
          {data.routes.map((s) => <p key={s} style={row}><RouteSwatch color={sym.status[s].color} status={s} />{sym.status[s].label.split(' / ')[0]}</p>)}
        </>
      )}
      {data.services.length > 0 && (
        <>
          <h3 style={h3}>Services</h3>
          <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : '1fr 1fr', columnGap: '0.8em' }}>
            {data.services.map((t) => (
              <p key={t} style={row}><img src={symbolDataUrl(sym, t, 'ok')} style={{ width: '1.4em', height: '1.4em' }} alt="" />{sym.types[t]?.label || t}</p>
            ))}
          </div>
          <p style={{ ...row, flexWrap: 'wrap', marginTop: '0.5em' }}>
            {(data.statuses.length ? data.statuses : (['ok', 'partial', 'no'] as Status[])).map((s) => (
              <span key={s} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3em', marginRight: '0.6em' }}>
                <img src={symbolDataUrl(sym, 'water', s)} style={{ width: '1.4em', height: '1.4em' }} alt="" />{sym.status[s].short}
              </span>
            ))}
          </p>
        </>
      )}
      {data.analysis.classes.length > 0 && (
        <>
          <h3 style={h3}>Imagery analysis{data.analysis.simulated ? ' (simulated)' : ''}</h3>
          {data.analysis.classes.map((c) => {
            const col = sym.analysis?.[c]?.color || '#7048E8'
            const isArea = c === 'block' || c === 'boundary'
            return (
              <p key={c} style={row}>
                <i style={{ width: '1.6em', height: '1em', display: 'inline-block', background: isArea ? 'transparent' : `${col}55`, border: `${isArea ? 2 : 1.5}px solid ${col}` }} />
                {c === 'block' ? 'Detected block' : c === 'boundary' ? 'Detected site boundary' : sym.types[c]?.label || c}
              </p>
            )
          })}
          {data.analysis.suggested && <p style={{ ...row, color: '#4A5A6D' }}>Dashed: suggested, not yet reviewed</p>}
        </>
      )}
      {data.areas.length > 0 && (
        <>
          <h3 style={h3}>Areas</h3>
          {data.areas.map((t) => (
            <p key={t} style={row}>
              <i style={{ width: '1.6em', height: '1em', background: areaColor(t), border: `1.5px solid ${areaStroke(t)}`, display: 'inline-block' }} />
              {sym.types[t]?.label || (t === 'other' ? 'Mapped area' : t)}
            </p>
          ))}
        </>
      )}
    </div>
  )
}
