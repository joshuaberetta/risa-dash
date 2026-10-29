// Imagery analysis (simulated): detect shelters, buildings, blocks and the site
// boundary on an orthomosaic, then review the suggestions.

import { Alert, Badge, Button, Group, Loader, Modal, NumberInput, Paper, Progress, Radio, Select, Stack, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconPolygon, IconSchool, IconSparkles } from '@tabler/icons-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type LayerT, type SiteFull } from '../api'

export const SIMULATED_NOTE =
  'Simulated: colour rules on the real image stand in for a segmentation model. Outlines sit on real roofs and tarps, but counts are not reliable. Review every suggestion.'

export function AnalyseButton({ site, getViewBounds, onStarted }: { site: SiteFull; getViewBounds: () => [number, number, number, number] | null; onStarted?: () => void }) {
  const [open, setOpen] = useState(false)
  const rasters = site.layers.filter((l) => l.kind === 'raster' && l.status === 'ready')
  if (!rasters.length) return null
  const running = site.layers.some((l) => l.kind === 'analysis' && l.status === 'processing')
  return (
    <>
      <Button fullWidth variant="light" color="violet" leftSection={running ? <Loader size={14} color="violet" /> : <IconSparkles size={16} />}
        onClick={() => setOpen(true)} disabled={running}>
        {running ? 'Analysing imagery…' : 'Detect shelters on imagery'}
      </Button>
      {open && <AnalyseModal site={site} rasters={rasters} getViewBounds={getViewBounds} onClose={() => setOpen(false)} onStarted={onStarted} />}
    </>
  )
}

function AnalyseModal({ site, rasters, getViewBounds, onClose, onStarted }: {
  site: SiteFull; rasters: LayerT[]; getViewBounds: () => [number, number, number, number] | null; onClose: () => void; onStarted?: () => void
}) {
  const qc = useQueryClient()
  const [layer, setLayer] = useState(rasters[0].id)
  const [area, setArea] = useState<'image' | 'view'>('view')
  const [err, setErr] = useState('')
  const run = async () => {
    try {
      const bounds = area === 'view' ? getViewBounds() : null
      await api(`/layers/${layer}/analyse`, { body: { bounds } })
      qc.invalidateQueries({ queryKey: ['site'] })
      onStarted?.()
      onClose()
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }
  return (
    <Modal opened onClose={onClose} title={<Group gap={6}><IconSparkles size={18} /><Text fw={600}>Detect shelters on imagery</Text></Group>} size="lg">
      <Stack>
        <Text size="sm">
          Finds shelters and buildings on the orthomosaic, groups shelters into blocks and outlines the site. Everything comes back as
          a <b>suggestion</b> to check: accept, reject, re-tag or reshape it. Only accepted shelters count towards the figures on page 1.
        </Text>
        <Alert color="violet" variant="light" title="Simulated analysis">{SIMULATED_NOTE}</Alert>
        {rasters.length > 1 && <Select label="Imagery" data={rasters.map((r) => ({ value: r.id, label: r.name }))} value={layer} onChange={(v) => v && setLayer(v)} allowDeselect={false} />}
        <Radio.Group label="Area of interest" value={area} onChange={(v) => setArea(v as 'image' | 'view')}>
          <Stack gap={6} mt={6}>
            <Radio value="view" label="What's on the map now (zoom to the camp first)" />
            <Radio value="image" label="The whole image" />
          </Stack>
        </Radio.Group>
        {err && <Text c="red" size="sm">{err}</Text>}
        <Group justify="flex-end"><Button color="violet" leftSection={<IconSparkles size={16} />} onClick={run}>Start detection</Button></Group>
      </Stack>
      <Text size="xs" c="dimmed" mt="md">Site: {site.name}</Text>
    </Modal>
  )
}

/** Progress for a running analysis, shown on the map. */
export function AnalysisProgress({ layers }: { layers: LayerT[] }) {
  const running = layers.filter((l) => l.kind === 'analysis' && l.status === 'processing')
  if (!running.length) return null
  const p = running[0].analysis?.progress || { step: 'Queued', pct: 2 }
  return (
    <Paper shadow="md" withBorder p="sm" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', zIndex: 3, width: 300 }}>
      <Group gap="sm" wrap="nowrap">
        <Loader size="sm" color="violet" />
        <div style={{ flex: 1 }}>
          <Text size="sm" fw={600}>Analysing imagery</Text>
          <Text size="xs" c="dimmed">{p.step}…</Text>
        </div>
        <Badge color="violet" variant="light">Simulated</Badge>
      </Group>
      <Progress value={p.pct} color="violet" mt="sm" size="sm" animated />
    </Paper>
  )
}

/** Bulk review in the layer menu. */
export function useBulkReview() {
  const qc = useQueryClient()
  return async (layer: LayerT, action: 'accept' | 'reject' | 'delete_rejected', range?: [number, number]) => {
    const r = await api<{ changed: number }>(`/layers/${layer.id}/review`, {
      body: { action, min_confidence: range?.[0] ?? 0, max_confidence: range?.[1] ?? 1 },
    })
    notifications.show({ message: `${r.changed} ${action === 'delete_rejected' ? 'rejected removed' : action === 'accept' ? 'accepted' : 'rejected'}` })
    qc.invalidateQueries({ queryKey: ['site'] })
  }
}

export function BulkReviewModal({ layer, onClose }: { layer: LayerT; onClose: () => void }) {
  const review = useBulkReview()
  const [action, setAction] = useState<'accept' | 'reject'>('accept')
  const [threshold, setThreshold] = useState<number | string>(70)
  const t = Number(threshold) / 100
  const go = async () => {
    await review(layer, action, action === 'accept' ? [t, 1] : [0, t])
    onClose()
  }
  return (
    <Modal opened onClose={onClose} title="Review suggestions">
      <Stack>
        <Radio.Group value={action} onChange={(v) => setAction(v as 'accept' | 'reject')}>
          <Stack gap={6}>
            <Radio value="accept" label="Accept suggestions at or above" />
            <Radio value="reject" label="Reject suggestions below" />
          </Stack>
        </Radio.Group>
        <NumberInput label="Confidence" suffix=" %" min={0} max={100} step={5} value={threshold} onChange={setThreshold} />
        <Text size="xs" c="dimmed">Only suggestions still waiting for review change. Edited or already reviewed features stay as they are.</Text>
        <Group justify="flex-end"><Button color="violet" onClick={go}>{action === 'accept' ? 'Accept' : 'Reject'}</Button></Group>
      </Stack>
    </Modal>
  )
}

interface DetectorInfo {
  labels: { positives: number; negatives: number; added: number; needed: number }
  versions: {
    version: number; name: string; status: 'processing' | 'ready' | 'failed'; error: string; created_at: string
    metrics: { examples?: number; held_out?: number; accuracy?: number; precision?: number; recall?: number; added?: number; baseline?: { accuracy?: number } }
  }[]
}

const pc = (x?: number | null) => (x == null ? '–' : `${Math.round(x * 100)}%`)

/** Learn from corrections: every accept, reject, edit and drawn shelter is a label. */
export function LearnPanel({ slug, canEdit, onDrawMissed, drawing }: { slug: string; canEdit: boolean; onDrawMissed?: () => void; drawing: boolean }) {
  const qc = useQueryClient()
  const q = useQuery({
    queryKey: ['detector', slug],
    queryFn: () => api<DetectorInfo>(`/responses/${slug}/detector`),
    refetchInterval: (x) => (x.state.data?.versions[0]?.status === 'processing' ? 2500 : 8000),
  })
  const d = q.data
  if (!d) return null
  const { positives, negatives, added, needed } = d.labels
  const latest = d.versions.find((v) => v.status === 'ready')
  const running = d.versions[0]?.status === 'processing'
  const failed = d.versions[0]?.status === 'failed' ? d.versions[0] : null
  const ready = positives >= needed && negatives >= needed
  const train = async () => {
    try {
      await api(`/responses/${slug}/detector/train`, { method: 'POST' })
      qc.invalidateQueries({ queryKey: ['detector', slug] })
    } catch (e) {
      notifications.show({ color: 'red', message: String((e as Error).message) })
    }
  }
  return (
    <Paper withBorder p="sm" mx="sm" mt="sm">
      <Group gap={6} mb={4}><IconSchool size={16} color="var(--mantine-color-violet-7)" /><Text fw={600} size="sm">Learn from corrections</Text></Group>
      <Text size="xs" c="dimmed">
        Every shelter you accept, reject, reshape or draw teaches the detector. Learning makes a new version for this response; the next detection uses it.
      </Text>
      <Group gap="xs" mt="xs">
        <Badge variant="light" color="violet">{positives} accepted{added ? ` (${added} drawn)` : ''}</Badge>
        <Badge variant="light" color="gray">{negatives} rejected</Badge>
      </Group>
      {!ready && <Text size="xs" mt={6}>Review at least {needed} each way to learn ({Math.max(0, needed - positives)} more accepted, {Math.max(0, needed - negatives)} more rejected).</Text>}
      {latest && (
        <Text size="xs" mt={6}>
          <b>Using v{latest.version}</b>, learned from {latest.metrics.examples} reviews: right on {pc(latest.metrics.accuracy)} of {latest.metrics.held_out} reviews held back
          (the built-in rules: {pc(latest.metrics.baseline?.accuracy)}). Precision {pc(latest.metrics.precision)}, recall {pc(latest.metrics.recall)}.
        </Text>
      )}
      {failed && <Text size="xs" c="red" mt={6}>v{failed.version} failed: {failed.error}</Text>}
      {canEdit && (
        <Group gap="xs" mt="sm">
          <Button size="compact-xs" color="violet" leftSection={running ? <Loader size={12} color="white" /> : <IconSchool size={13} />} onClick={train} disabled={!ready || running}>
            {running ? 'Learning…' : latest ? `Learn v${latest.version + 1}` : 'Learn from corrections'}
          </Button>
          {onDrawMissed && <Button size="compact-xs" variant={drawing ? 'filled' : 'light'} color="violet" leftSection={<IconPolygon size={13} />} onClick={onDrawMissed}>{drawing ? 'Drawing missed shelters (Esc to stop)' : 'Draw missed shelters'}</Button>}
        </Group>
      )}
      <Text size="xs" c="dimmed" mt={6}>Simulated: this tunes the stand-in detector. A real model is fine-tuned on the same labels; download them from the analysis layer’s menu.</Text>
    </Paper>
  )
}
