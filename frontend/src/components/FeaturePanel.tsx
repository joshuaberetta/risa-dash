import { ActionIcon, Badge, Button, Group, Image, Modal, Select, SimpleGrid, Stack, Table, Text, TextInput } from '@mantine/core'
import { IconPencil, IconShape, IconTrash, IconX } from '@tabler/icons-react'
import area from '@turf/area'
import length from '@turf/length'
import { useEffect, useState } from 'react'
import type { Config, LayerT, Status } from '../api'
import type { PickedFeature } from '../map/MapView'
import { symbolDataUrl } from '../map/symbols'

export interface FeatureFields {
  risa_type: string
  risa_status: string
  label: string
}

export function StatusBadge({ config, status }: { config: Config; status: string }) {
  const s = config.symbology.status[(status || 'unknown') as Status] || config.symbology.status.unknown
  return <Badge variant="outline" color={s.color} styles={{ root: { color: config.symbology.ink } }}
    leftSection={<span style={{ width: 8, height: 8, borderRadius: 4, background: s.color, display: 'inline-block' }} />}>{s.short}</Badge>
}

/** Type, status and label for a new or existing feature. */
export function FeatureForm({ config, initial, geometryType, onSave, onCancel, saveLabel = 'Save' }: {
  config: Config; initial?: Partial<FeatureFields>; geometryType?: string
  onSave: (f: FeatureFields) => void; onCancel: () => void; saveLabel?: string
}) {
  const [f, setF] = useState<FeatureFields>({ risa_type: '', risa_status: '', label: '', ...initial })
  const types = Object.entries(config.symbology.types)
    .filter(([k]) => geometryType === 'Point' ? !['route', 'block', 'flood', 'debris'].includes(k) : true)
    .map(([value, v]) => ({ value, label: v.label }))
  const statuses = (Object.keys(config.symbology.status) as Status[]).map((value) => ({ value, label: config.symbology.status[value].label }))
  return (
    <Stack gap="sm">
      <TextInput label="Label" placeholder="Puesto de salud" value={f.label} onChange={(e) => setF({ ...f, label: e.currentTarget.value })} data-autofocus
        onKeyDown={(e) => e.key === 'Enter' && onSave(f)} />
      <Select label="Type" searchable clearable data={types} value={f.risa_type || null} onChange={(v) => setF({ ...f, risa_type: v || '' })}
        renderOption={({ option }) => (
          <Group gap={8}>{geometryType === 'Point' && <img src={symbolDataUrl(config.symbology, option.value, 'ok', 1)} width={18} height={18} />}<span>{option.label}</span></Group>
        )} />
      <Select label="Status" clearable data={statuses} value={f.risa_status || null} onChange={(v) => setF({ ...f, risa_status: v || '' })} />
      <Group justify="flex-end">
        <Button variant="default" onClick={onCancel}>Cancel</Button>
        <Button onClick={() => onSave(f)}>{saveLabel}</Button>
      </Group>
    </Stack>
  )
}

const HIDDEN = new Set(['risa_id', 'risa_type', 'risa_status', 'risa_label', '_photos', 'observed_at'])

function measure(g: GeoJSON.Geometry) {
  const f = { type: 'Feature', geometry: g, properties: {} } as GeoJSON.Feature
  if (g.type.includes('Polygon')) {
    const m2 = area(f)
    return m2 > 10000 ? `${(m2 / 10000).toFixed(2)} ha` : `${Math.round(m2).toLocaleString()} m²`
  }
  if (g.type.includes('LineString')) {
    const km = length(f)
    return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(2)} km`
  }
  return ''
}

export default function FeaturePanel({ config, feature, layer, canEdit, onClose, onSave, onDelete, onEditShape }: {
  config: Config; feature: PickedFeature; layer?: LayerT; canEdit: boolean
  onClose: () => void; onSave: (f: FeatureFields) => Promise<void>; onDelete: () => void; onEditShape: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [photo, setPhoto] = useState<string | null>(null)
  useEffect(() => setEditing(false), [feature.id])
  const p = feature.properties
  const editable = canEdit && layer && layer.kind !== 'kobo'
  const photos = (typeof p._photos === 'string' ? JSON.parse(p._photos as string) : p._photos || []) as { url: string; large: string; name: string }[]
  const photoUrl = (u: string) => `/api/layers/${feature.layerId}/kobo/photo?url=${encodeURIComponent(u)}`
  // Prefer Kobo choice labels over raw choice names
  const rows = Object.entries(p).filter(([k, v]) => !HIDDEN.has(k) && !k.endsWith(':label') && v !== null && v !== '' && typeof v !== 'object')
    .map(([k, v]) => [k, String(p[`${k}:label`] ?? v)] as const)
  const typeLabel = config.symbology.types[String(p.risa_type)]?.label
  const m = measure(feature.geometry)
  return (
    <Stack gap="sm" p="sm">
      <Group justify="space-between" wrap="nowrap" align="flex-start">
        <div style={{ minWidth: 0 }}>
          <Text fw={600} truncate>{String(p.risa_label || typeLabel || 'Feature')}</Text>
          <Text size="xs" c="dimmed">{layer?.name}</Text>
        </div>
        <ActionIcon variant="subtle" color="gray" onClick={onClose}><IconX size={16} /></ActionIcon>
      </Group>
      <Group gap="xs">
        <StatusBadge config={config} status={String(p.risa_status || '')} />
        {typeLabel && <Badge variant="light" color="gray">{typeLabel}</Badge>}
        {m && <Badge variant="light" color="gray">{m}</Badge>}
      </Group>
      {editable && !editing && (
        <Group gap="xs">
          <Button size="compact-xs" variant="light" leftSection={<IconPencil size={13} />} onClick={() => setEditing(true)}>Edit</Button>
          <Button size="compact-xs" variant="light" leftSection={<IconShape size={13} />} onClick={onEditShape}>Edit shape</Button>
          <Button size="compact-xs" variant="light" color="red" leftSection={<IconTrash size={13} />} onClick={onDelete}>Delete</Button>
        </Group>
      )}
      {editing && (
        <FeatureForm config={config} geometryType={feature.geometry.type}
          initial={{ risa_type: String(p.risa_type || ''), risa_status: String(p.risa_status || ''), label: String(p.risa_label || '') }}
          onCancel={() => setEditing(false)} onSave={async (f) => { await onSave(f); setEditing(false) }} />
      )}
      {photos.length > 0 && (
        <SimpleGrid cols={2} spacing={6} className="photo-grid">
          {photos.map((ph) => <img key={ph.url} src={photoUrl(ph.url)} alt={ph.name} loading="lazy" style={{ cursor: 'zoom-in' }} onClick={() => setPhoto(photoUrl(ph.large || ph.url))} />)}
        </SimpleGrid>
      )}
      {rows.length > 0 && (
        <Table fz="xs" verticalSpacing={3} withRowBorders>
          <Table.Tbody>
            {rows.slice(0, 60).map(([k, v]) => (
              <Table.Tr key={k}><Table.Td c="dimmed" style={{ wordBreak: 'break-word', width: '42%' }}>{k.split('/').pop()}</Table.Td><Table.Td style={{ wordBreak: 'break-word' }}>{v}</Table.Td></Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      <Modal opened={!!photo} onClose={() => setPhoto(null)} size="xl" withCloseButton={false} padding={0}>
        {photo && <Image src={photo} />}
      </Modal>
    </Stack>
  )
}
