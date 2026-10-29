import { ActionIcon, Badge, Box, Button, Group, Loader, Menu, Slider, Stack, Switch, Text, Tooltip } from '@mantine/core'
import {
  IconArrowDown, IconArrowUp, IconCloudDownload, IconDots, IconDownload, IconFocus2, IconPencil, IconPlus,
  IconRefresh, IconSettings, IconSparkles, IconTrash, IconWorld,
} from '@tabler/icons-react'
import { modals } from '@mantine/modals'
import { notifications } from '@mantine/notifications'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type LayerT, type SiteFull } from '../api'
import type { LayerState } from '../map/MapView'
import { BulkReviewModal, useBulkReview } from './Analysis'
import { KoboConnectModal, KoboMappingModal } from './KoboModals'
import { UploadModal, UrlLayerModal } from './UploadModal'

const KIND_LABEL: Record<LayerT['kind'], string> = {
  raster: 'Imagery', vector: 'Vector', kobo: 'Kobo', annotations: 'Drawn', xyz: 'Tiles', wms: 'WMS', cog_url: 'COG', analysis: 'Analysis',
}

interface Props {
  site: SiteFull
  state: Record<string, LayerState>
  setState: (id: string, s: Partial<LayerState>) => void
  onZoom: (l: LayerT) => void
  canEdit: boolean
}

export default function LayerPanel({ site, state, setState, onZoom, canEdit }: Props) {
  const qc = useQueryClient()
  const [modal, setModal] = useState<null | 'upload' | 'kobo' | 'url'>(null)
  const [mapping, setMapping] = useState<LayerT | null>(null)
  const [reviewing, setReviewing] = useState<LayerT | null>(null)
  const bulkReview = useBulkReview()
  const refresh = () => qc.invalidateQueries({ queryKey: ['site'] })
  const layers = site.layers

  const move = async (i: number, d: -1 | 1) => {
    const ids = layers.map((l) => l.id)
    const j = i + d
    if (j < 0 || j >= ids.length) return
    ;[ids[i], ids[j]] = [ids[j], ids[i]]
    await api(`/sites/${site.id}/layers/reorder`, { body: { ids } })
    refresh()
  }
  const remove = (l: LayerT) =>
    modals.openConfirmModal({
      title: `Delete ${l.name}?`,
      children: <Text size="sm">This removes the layer and its data from the site. Printed PDFs are kept.</Text>,
      labels: { confirm: 'Delete', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: async () => { await api(`/layers/${l.id}`, { method: 'DELETE' }); refresh() },
    })
  const rename = (l: LayerT) => {
    const name = prompt('Layer name', l.name)
    if (name && name !== l.name) api(`/layers/${l.id}`, { method: 'PATCH', body: { name } }).then(refresh)
  }
  const sync = async (l: LayerT) => {
    await api(`/layers/${l.id}/kobo/sync`, { method: 'POST' })
    notifications.show({ message: `Syncing ${l.name} from Kobo…` })
    setTimeout(refresh, 3000)
  }

  return (
    <Stack gap={0}>
      <Group justify="space-between" px="sm" py={8}>
        <Text fw={600} size="sm">Layers</Text>
        {canEdit && (
          <Menu position="bottom-end" withinPortal>
            <Menu.Target><Button size="compact-xs" variant="light" leftSection={<IconPlus size={14} />}>Add</Button></Menu.Target>
            <Menu.Dropdown>
              <Menu.Item leftSection={<IconCloudDownload size={16} />} onClick={() => setModal('upload')}>Upload a file</Menu.Item>
              <Menu.Item leftSection={<IconRefresh size={16} />} onClick={() => setModal('kobo')}>Connect a Kobo project</Menu.Item>
              <Menu.Item leftSection={<IconWorld size={16} />} onClick={() => setModal('url')}>Imagery by URL</Menu.Item>
            </Menu.Dropdown>
          </Menu>
        )}
      </Group>
      {layers.length === 0 && (
        <Text size="sm" c="dimmed" px="sm" pb="sm">
          {canEdit ? 'Add a drone orthomosaic, a Kobo project or a vector file to start.' : 'No layers yet.'}
        </Text>
      )}
      {layers.map((l, i) => {
        const st = state[l.id] || { visible: l.visible_default, opacity: l.style.opacity ?? 1 }
        return (
          <Box key={l.id} className="layer-row" px="sm" py={6}>
            <Group gap={6} wrap="nowrap" justify="space-between">
              <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
                <Switch size="xs" checked={st.visible} onChange={(e) => setState(l.id, { visible: e.currentTarget.checked })} disabled={l.status !== 'ready'} />
                <div style={{ minWidth: 0 }}>
                  <Text size="sm" truncate fw={500} title={l.name}>{l.name}</Text>
                  <Group gap={4}>
                    <Badge size="xs" variant="light" color="gray">{KIND_LABEL[l.kind]}</Badge>
                    {l.status === 'processing' && <Group gap={4}><Loader size={10} /><Text size="xs" c="dimmed">{l.analysis?.progress?.step || 'processing'}</Text></Group>}
                    {l.kind === 'analysis' && l.status === 'ready' && l.analysis?.counts && (
                      <Text size="xs" c="violet.8">{l.analysis.counts.shelter} shelters · {l.analysis.counts.block} blocks{l.analysis.simulated ? ' · simulated' : ''}</Text>
                    )}
                    {l.status === 'failed' && <Tooltip label={l.error} multiline w={300}><Badge size="xs" color="red">failed</Badge></Tooltip>}
                    {l.resolution_cm && <Text size="xs" c="dimmed">{l.resolution_cm} cm/px</Text>}
                    {l.captured_at && <Text size="xs" c="dimmed">{l.captured_at}</Text>}
                    {l.kind !== 'analysis' && l.feature_count != null && l.feature_count > 0 && <Text size="xs" c="dimmed">{l.feature_count} features</Text>}
                    {l.kobo?.last_error && <Tooltip label={l.kobo.last_error} multiline w={300}><Badge size="xs" color="orange">sync error</Badge></Tooltip>}
                  </Group>
                </div>
              </Group>
              <Group gap={0} wrap="nowrap">
                <Tooltip label="Zoom to layer"><ActionIcon variant="subtle" color="gray" size="sm" onClick={() => onZoom(l)} disabled={!l.bbox}><IconFocus2 size={15} /></ActionIcon></Tooltip>
                <Menu position="bottom-end" withinPortal>
                  <Menu.Target><ActionIcon variant="subtle" color="gray" size="sm"><IconDots size={15} /></ActionIcon></Menu.Target>
                  <Menu.Dropdown>
                    {canEdit && <Menu.Item leftSection={<IconArrowUp size={14} />} onClick={() => move(i, -1)} disabled={i === 0}>Move up</Menu.Item>}
                    {canEdit && <Menu.Item leftSection={<IconArrowDown size={14} />} onClick={() => move(i, 1)} disabled={i === layers.length - 1}>Move down</Menu.Item>}
                    {canEdit && <Menu.Item leftSection={<IconPencil size={14} />} onClick={() => rename(l)}>Rename</Menu.Item>}
                    {canEdit && l.kind === 'kobo' && <Menu.Item leftSection={<IconRefresh size={14} />} onClick={() => sync(l)}>Sync now</Menu.Item>}
                    {canEdit && l.kind === 'kobo' && <Menu.Item leftSection={<IconSettings size={14} />} onClick={() => setMapping(l)}>Map form to RISA</Menu.Item>}
                    {canEdit && l.kind === 'analysis' && l.status === 'ready' && <Menu.Item leftSection={<IconSparkles size={14} />} onClick={() => setReviewing(l)}>Review by confidence…</Menu.Item>}
                    {canEdit && l.kind === 'analysis' && l.status === 'ready' && <Menu.Item leftSection={<IconTrash size={14} />} onClick={() => bulkReview(l, 'delete_rejected')}>Remove rejected</Menu.Item>}
                    {l.download && <Menu.Item leftSection={<IconDownload size={14} />} component="a" href={l.download}>Download original</Menu.Item>}
                    {l.kind === 'raster' && l.url && <Menu.Item leftSection={<IconDownload size={14} />} component="a" href={l.url} download>Download COG (QGIS/ArcGIS)</Menu.Item>}
                    {canEdit && <Menu.Divider />}
                    {canEdit && <Menu.Item color="red" leftSection={<IconTrash size={14} />} onClick={() => remove(l)}>Delete</Menu.Item>}
                  </Menu.Dropdown>
                </Menu>
              </Group>
            </Group>
            {st.visible && l.status === 'ready' && (
              <Slider size="xs" mt={6} ml={34} mr={4} min={0} max={1} step={0.05} value={st.opacity} label={(v) => `${Math.round(v * 100)}%`}
                onChange={(v) => setState(l.id, { opacity: v })} />
            )}
          </Box>
        )
      })}
      <UploadModal site={site} opened={modal === 'upload'} onClose={() => setModal(null)} />
      <KoboConnectModal site={site} opened={modal === 'kobo'} onClose={() => setModal(null)} />
      <UrlLayerModal site={site} opened={modal === 'url'} onClose={() => setModal(null)} />
      {mapping && <KoboMappingModal layer={mapping} onClose={() => setMapping(null)} />}
      {reviewing && <BulkReviewModal layer={reviewing} onClose={() => setReviewing(null)} />}
    </Stack>
  )
}
