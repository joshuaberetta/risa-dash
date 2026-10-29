import { ActionIcon, Badge, Group, Image, Modal, ScrollArea, Select, Table, Text, TextInput, Tooltip } from '@mantine/core'
import { IconSearch, IconSparkles, IconX } from '@tabler/icons-react'
import { useMemo, useState } from 'react'
import { photoNote } from '../analysis'
import type { Config, LayerT, Status } from '../api'
import type { PickedFeature } from '../map/MapView'
import { symbolDataUrl } from '../map/symbols'
import { AI_COLOR } from './AnalysisPanel'
import { StatusBadge } from './FeaturePanel'

const SAMPLE_PHOTO = '/sample-photo.svg'
// Shown in their own columns, or internal
const SKIP = new Set(['risa_id', 'risa_type', 'risa_status', 'risa_label', '_photos', 'observed_at', 'type', 'status', 'label', 'note', 'observed'])
const MAX_COLUMNS = 12

interface Photo { url: string; large?: string; name?: string }

/** Records of a vector layer (Kobo submissions first) with their photos. */
export default function DataTable({ config, layers, data, onPick, onClose }: {
  config: Config; layers: LayerT[]; data: Record<string, GeoJSON.FeatureCollection | undefined>
  onPick: (f: PickedFeature) => void; onClose: () => void
}) {
  const choices = layers.filter((l) => data[l.id]?.features.length)
    .sort((a, b) => Number(b.kind === 'kobo') - Number(a.kind === 'kobo'))
  const [layerId, setLayerId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [photo, setPhoto] = useState<{ src: string; caption: string } | null>(null)
  const layer = choices.find((l) => l.id === layerId) || choices[0]
  const features = (layer && data[layer.id]?.features) || []

  const columns = useMemo(() => {
    const keys = new Set<string>()
    for (const f of features) for (const [k, v] of Object.entries(f.properties || {})) {
      if (!SKIP.has(k) && !k.endsWith(':label') && v !== null && v !== '' && typeof v !== 'object') keys.add(k)
    }
    return [...keys].slice(0, MAX_COLUMNS)
  }, [features])

  const hasNote = features.some((f) => f.properties?.note)
  const rows = features.filter((f) => {
    const p = f.properties || {}
    if (status !== 'all' && (p.risa_status || 'unknown') !== status) return false
    if (!search) return true
    const q = search.toLowerCase()
    return Object.values(p).some((v) => v != null && String(v).toLowerCase().includes(q)) ||
      (config.symbology.types[String(p.risa_type)]?.label || '').toLowerCase().includes(q)
  })

  if (!layer) {
    return <Group p="sm" justify="space-between"><Text size="sm" c="dimmed">No records yet. Connect a Kobo project or upload vector data.</Text><ActionIcon variant="subtle" color="gray" onClick={onClose}><IconX size={16} /></ActionIcon></Group>
  }
  const photosOf = (p: Record<string, unknown>): Photo[] => {
    const ph = (typeof p._photos === 'string' ? JSON.parse(p._photos) : p._photos || []) as Photo[]
    return ph.map((x) => ({ ...x, url: `/api/layers/${layer.id}/kobo/photo?url=${encodeURIComponent(x.url)}`, large: x.large && `/api/layers/${layer.id}/kobo/photo?url=${encodeURIComponent(x.large)}` }))
  }
  const statuses = config.symbology.status

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Group px="sm" py={6} gap="xs" wrap="nowrap" style={{ borderBottom: '1px solid var(--mantine-color-gray-3)' }}>
        <Select size="xs" w={260} value={layer.id} onChange={setLayerId} allowDeselect={false}
          data={choices.map((l) => ({ value: l.id, label: `${l.name}${l.kind === 'kobo' ? ' · Kobo' : ''}` }))} />
        <TextInput size="xs" w={200} placeholder="Search" leftSection={<IconSearch size={14} />} value={search} onChange={(e) => setSearch(e.currentTarget.value)} />
        <Select size="xs" w={170} value={status} onChange={(v) => setStatus(v || 'all')} allowDeselect={false}
          data={[{ value: 'all', label: 'All statuses' }, ...(Object.keys(statuses) as Status[]).map((s) => ({ value: s, label: statuses[s].short }))]} />
        <Text size="xs" c="dimmed" ml="auto" style={{ whiteSpace: 'nowrap' }}>{rows.length} of {features.length} records</Text>
        <Tooltip label="Close table"><ActionIcon variant="subtle" color="gray" onClick={onClose} aria-label="Close table"><IconX size={16} /></ActionIcon></Tooltip>
      </Group>
      <ScrollArea style={{ flex: 1 }}>
        <Table fz="xs" verticalSpacing={4} highlightOnHover stickyHeader striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Photo</Table.Th>
              <Table.Th>Label</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Observed</Table.Th>
              {hasNote && <Table.Th>Note</Table.Th>}
              {columns.map((c) => <Table.Th key={c} style={{ whiteSpace: 'nowrap' }}>{c.split('/').pop()}</Table.Th>)}
              <Table.Th style={{ minWidth: 220 }}>
                <Tooltip label="Example of what an image model could read from the photo. Not real.">
                  <Group gap={4} wrap="nowrap"><IconSparkles size={13} color={`var(--mantine-color-${AI_COLOR}-6)`} /><span>Photo notes</span><Badge size="xs" color={AI_COLOR} variant="light">example</Badge></Group>
                </Tooltip>
              </Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((f) => {
              const p = f.properties || {}
              const id = String(p.risa_id ?? f.id)
              const type = String(p.risa_type || '')
              const st = String(p.risa_status || '')
              const photos = photosOf(p)
              const point = f.geometry?.type === 'Point'
              const shown: Photo[] = photos.length ? photos : point ? [{ url: SAMPLE_PHOTO }] : []
              const label = String(p.risa_label || config.symbology.types[type]?.label || 'Feature')
              return (
                <Table.Tr key={id} style={{ cursor: 'pointer' }} onClick={() => f.geometry && onPick({ layerId: layer.id, id, properties: p, geometry: f.geometry })}>
                  <Table.Td>
                    <Group gap={4} wrap="nowrap">
                      {shown.slice(0, 3).map((ph) => (
                        <img key={ph.url} src={ph.url} alt={ph.name || 'Sample photo'} loading="lazy" width={56} height={42}
                          style={{ objectFit: 'cover', borderRadius: 3, display: 'block', cursor: 'zoom-in' }}
                          onClick={(e) => { e.stopPropagation(); setPhoto({ src: ph.large || ph.url, caption: `${label}${photos.length ? '' : ' · template image, no photo yet'}` }) }} />
                      ))}
                      {photos.length > 3 && <Text size="xs" c="dimmed">+{photos.length - 3}</Text>}
                    </Group>
                  </Table.Td>
                  <Table.Td fw={500} style={{ whiteSpace: 'nowrap' }}>{String(p.risa_label || '–')}</Table.Td>
                  <Table.Td style={{ whiteSpace: 'nowrap' }}>
                    <Group gap={6} wrap="nowrap">
                      {point && <img src={symbolDataUrl(config.symbology, type, (st || 'unknown') as Status, 1)} width={16} height={16} alt="" />}
                      {config.symbology.types[type]?.label || type || '–'}
                    </Group>
                  </Table.Td>
                  <Table.Td style={{ minWidth: 160 }}><StatusBadge config={config} status={st} /></Table.Td>
                  <Table.Td style={{ whiteSpace: 'nowrap' }}>{String(p.observed || p._submission_time || p.observed_at || '').slice(0, 10) || '–'}</Table.Td>
                  {hasNote && <Table.Td>{String(p.note || '') || '–'}</Table.Td>}
                  {columns.map((c) => <Table.Td key={c}>{p[c] == null || p[c] === '' ? '–' : String(p[`${c}:label`] ?? p[c])}</Table.Td>)}
                  <Table.Td c="dimmed">{point ? photoNote(type, st) || '–' : '–'}</Table.Td>
                </Table.Tr>
              )
            })}
          </Table.Tbody>
        </Table>
      </ScrollArea>
      <Modal opened={!!photo} onClose={() => setPhoto(null)} size="lg" title={photo?.caption}>
        {photo && <Image src={photo.src} radius="sm" />}
      </Modal>
    </div>
  )
}
