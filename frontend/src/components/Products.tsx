import { ActionIcon, Anchor, Badge, Box, Button, Center, Checkbox, Group, Loader, Modal, NumberInput, Paper, ScrollArea, SegmentedControl, Select, Stack, Switch, Tabs, Text, TextInput, Textarea, Tooltip } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconArrowDown, IconArrowUp, IconCrop, IconFileTypePdf, IconPlus, IconPrinter, IconSparkles, IconTrash } from '@tabler/icons-react'
import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api, type Gap, type Glance, type ProductT, type ProductView, type SiteFull } from '../api'

export function ProductsPanel({ site, canEdit, captureView }: { site: SiteFull; canEdit: boolean; captureView: () => ProductView }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<string | null>(null)
  const create = async () => {
    const p = await api<ProductT>(`/sites/${site.id}/products`, {
      body: { view: captureView(), title: 'Common Operational Picture', version_label: 'Initial assessment · v1.0', authority: '' },
    })
    await qc.invalidateQueries({ queryKey: ['site'] })
    setEditing(p.id)
  }
  const product = site.products.find((p) => p.id === editing)
  return (
    <Stack gap="xs" p="sm">
      <Group justify="space-between">
        <Text fw={600} size="sm">Printed products</Text>
        {canEdit && <Button size="compact-xs" variant="light" leftSection={<IconPlus size={14} />} onClick={create}>Page 1 from this view</Button>}
      </Group>
      {site.products.length === 0 && <Text size="xs" c="dimmed">Frame the map, then make a RISA page 1 (Common Operational Picture) to print at A3 or A4.</Text>}
      {site.products.map((p) => {
        const latest = p.versions[0]
        return (
          <Box key={p.id} className="layer-row" py={6}>
            <Group justify="space-between" wrap="nowrap">
              <div style={{ minWidth: 0 }}>
                <Anchor size="sm" fw={500} onClick={() => setEditing(p.id)} truncate>{p.code ? `${p.code} · ` : ''}{p.title}</Anchor>
                <Text size="xs" c="dimmed">{p.page_size} · {p.version_label}</Text>
              </div>
              {latest?.status === 'processing' && <Loader size="xs" />}
              {latest?.pdf && (
                <Tooltip label={`Version ${latest.n}, ${new Date(latest.rendered_at).toLocaleString()}`}>
                  <ActionIcon component="a" href={latest.pdf} target="_blank" variant="light"><IconFileTypePdf size={16} /></ActionIcon>
                </Tooltip>
              )}
            </Group>
          </Box>
        )
      })}
      {product && <ProductEditor site={site} product={product} canEdit={canEdit} captureView={captureView} onClose={() => setEditing(null)} />}
    </Stack>
  )
}

const DEFAULT_GLANCE: Glance[] = [
  { value: '', label: 'people (estimate)', tbc: true },
  { value: '', label: 'shelters counted on imagery', tbc: false },
  { value: '', label: 'water points working', tbc: false },
  { value: '', label: 'access routes open', tbc: false },
]

function ProductEditor({ site, product, canEdit, captureView, onClose }: {
  site: SiteFull; product: ProductT; canEdit: boolean; captureView: () => ProductView; onClose: () => void
}) {
  const qc = useQueryClient()
  const [p, setP] = useState<ProductT>(product)
  const [dirty, setDirty] = useState(false)
  const [tab, setTab] = useState<string>('1')
  const [shown, setShown] = useState(1)
  const [household, setHousehold] = useState<number | string>(site.response.household_size ?? 5)
  const page2 = p.pages?.includes(2)
  const findings = p.findings || { reach_note: '', gaps: [] }
  const setFindings = (patch: Partial<typeof findings>) => set({ findings: { ...findings, ...patch } })
  const setGap = (i: number, patch: Partial<Gap>) => setFindings({ gaps: findings.gaps.map((x, j) => (j === i ? { ...x, ...patch } : x)) })
  const moveGap = (i: number, d: number) => {
    const gs = [...findings.gaps]
    const [x] = gs.splice(i, 1)
    gs.splice(i + d, 0, x)
    setFindings({ gaps: gs })
  }
  const suggest = async () => {
    if (findings.gaps.length && !confirm('Replace the gaps with suggestions from the map?')) return
    setFindings({ gaps: await api<Gap[]>(`/products/${p.id}/suggested-gaps`) })
  }
  const printed = product.versions.find((v) => v.pdf)
  const latestPdf = printed?.pdf
  const pageCount = Math.max(1, canEdit ? (p.preview?.pages?.length || 1) : (printed?.images?.length || 1))
  useEffect(() => {
    // Keep versions and the preview fresh while the worker runs
    setP((cur) => ({ ...cur, versions: product.versions, preview: product.preview }))
  }, [product.versions, product.preview])
  const set = (patch: Partial<ProductT>) => { setP({ ...p, ...patch }); setDirty(true) }
  useEffect(() => {
    if (canEdit && !product.preview?.status) api(`/products/${product.id}/preview`, { method: 'POST' }).then(() => qc.invalidateQueries({ queryKey: ['site'] }))
  }, [product.id])
  const glance = p.glance?.length === 4 ? p.glance : DEFAULT_GLANCE
  const loc: ProductT['locators'] = p.locators || { area: true, country: false, place: 'map' }
  const setLoc = (patch: Partial<ProductT['locators']>) => set({ locators: { ...loc, ...patch } })

  const save = async (extra: Partial<ProductT> = {}) => {
    const body = { ...p, ...extra }
    const out = await api<ProductT>(`/products/${p.id}`, { method: 'PATCH', body: {
      title: body.title, code: body.code, version_label: body.version_label, page_size: body.page_size, view: body.view,
      key_message: body.key_message, glance: body.glance, authority: body.authority, sources: body.sources,
      disclaimer: body.disclaimer, credits: body.credits, locators: body.locators, pages: body.pages, findings: body.findings,
    } })
    if (Number(household) !== site.response.household_size) {
      await api(`/responses/${site.response.slug}`, { method: 'PATCH', body: { household_size: Number(household) || 5 } })
    }
    setP({ ...out })
    setDirty(false)
    qc.invalidateQueries({ queryKey: ['site'] })
  }
  const preview = async () => {
    await save()
    await api(`/products/${p.id}/preview`, { method: 'POST' })
    qc.invalidateQueries({ queryKey: ['site'] })
  }
  const render = async () => {
    if (dirty) await save()
    await api(`/products/${p.id}/render`, { method: 'POST' })
    notifications.show({ message: 'Rendering the PDF… it appears in the list when ready (usually under a minute).' })
    qc.invalidateQueries({ queryKey: ['site'] })
  }
  const remove = async () => {
    if (!confirm('Delete this product and its PDFs?')) return
    await api(`/products/${p.id}`, { method: 'DELETE' })
    qc.invalidateQueries({ queryKey: ['site'] })
    onClose()
  }
  const g = (i: number, patch: Partial<Glance>) => set({ glance: glance.map((x, j) => (j === i ? { ...x, ...patch } : x)) })

  return (
    <Modal opened onClose={onClose} fullScreen title={<Text fw={600}>RISA product · {site.name}</Text>} padding="md">
      <Group align="flex-start" wrap="nowrap" gap="lg" h="calc(100vh - 90px)">
        <ScrollArea w={360} h="100%" offsetScrollbars>
          <Stack gap="sm">
            <Tabs value={tab} onChange={(v) => { setTab(v || '1'); setShown(v === '2' && page2 ? 2 : 1) }}>
              <Tabs.List grow>
                <Tabs.Tab value="1">Page 1 · map</Tabs.Tab>
                <Tabs.Tab value="2">Page 2 · findings{page2 ? '' : ' (off)'}</Tabs.Tab>
              </Tabs.List>
                <Tabs.Panel value="1">
                  <Stack gap="sm" pt="sm">
                <SegmentedControl data={['A3', 'A4']} value={p.page_size} onChange={(v) => set({ page_size: v as 'A3' | 'A4' })} disabled={!canEdit} />
                <Stack gap={6}>
                  <Text size="sm" fw={500}>Locator maps</Text>
                  <Checkbox size="xs" label="Area round the site" checked={loc.area} onChange={(e) => setLoc({ area: e.currentTarget.checked })} disabled={!canEdit} />
                  <Checkbox size="xs" label="Country overview" description="About 1,500 km across, with the area marked and joined to it"
                    checked={loc.country} onChange={(e) => setLoc({ country: e.currentTarget.checked })} disabled={!canEdit} />
                  <SegmentedControl size="xs" value={loc.place} onChange={(v) => setLoc({ place: v as 'map' | 'side' })}
                    data={[{ label: 'On the map', value: 'map' }, { label: 'In the side panel', value: 'side' }]}
                    disabled={!canEdit || (!loc.area && !loc.country)} />
                </Stack>
                <TextInput label="Title" value={p.title} onChange={(e) => set({ title: e.currentTarget.value })} disabled={!canEdit} />
                <Group grow>
                  <TextInput label="Map code" placeholder="MA023" value={p.code} onChange={(e) => set({ code: e.currentTarget.value })} disabled={!canEdit} />
                  <TextInput label="Version" value={p.version_label} onChange={(e) => set({ version_label: e.currentTarget.value })} disabled={!canEdit} />
                </Group>
                <TextInput label="Leading authority" description="Shown first in the header. RISA is credited as the method." placeholder="Protección Civil Venezuela"
                  value={p.authority} onChange={(e) => set({ authority: e.currentTarget.value })} disabled={!canEdit} />
                <Textarea label="Key message" autosize minRows={2} placeholder="Blocks B1 and B2 are flooded. Use R1 (light vehicles) or R3."
                  value={p.key_message} onChange={(e) => set({ key_message: e.currentTarget.value })} disabled={!canEdit} />
                <Text size="sm" fw={500}>At a glance <Text span size="xs" c="dimmed">blank = computed from the data</Text></Text>
                {glance.map((x, i) => (
                  <Group key={i} gap={6} wrap="nowrap" align="flex-end">
                    <TextInput size="xs" w={90} placeholder="auto" value={x.value} onChange={(e) => g(i, { value: e.currentTarget.value })} disabled={!canEdit} />
                    <TextInput size="xs" style={{ flex: 1 }} value={x.label} onChange={(e) => g(i, { label: e.currentTarget.value })} disabled={!canEdit} />
                    <Checkbox size="xs" label="TBC" checked={x.tbc} onChange={(e) => g(i, { tbc: e.currentTarget.checked })} disabled={!canEdit} mb={6} />
                  </Group>
                ))}
                <Textarea label="Sources" description="Blank: built from each layer's credit and dates" autosize minRows={2} value={p.sources}
                  onChange={(e) => set({ sources: e.currentTarget.value })} disabled={!canEdit} />
                <Textarea label="Disclaimer" autosize minRows={2} value={p.disclaimer} onChange={(e) => set({ disclaimer: e.currentTarget.value })} disabled={!canEdit} />
                <TextInput label="Technical support" value={p.credits} onChange={(e) => set({ credits: e.currentTarget.value })} disabled={!canEdit} />
                  </Stack>
                </Tabs.Panel>
                <Tabs.Panel value="2">
                  <Stack gap="sm" pt="sm">
                    <Switch label="Print page 2: key findings" checked={!!page2} disabled={!canEdit}
                      onChange={(e) => { set({ pages: e.currentTarget.checked ? [1, 2] : [1] }); setShown(e.currentTarget.checked ? 2 : 1) }} />
                    <Text size="xs" c="dimmed">Access routes, logistics, services and shelters by block come from the map. Add a line on access and the gaps to act on.</Text>
                    <Textarea label="On access" description="Printed under the routes, e.g. which route to use" autosize minRows={2}
                      value={findings.reach_note} onChange={(e) => setFindings({ reach_note: e.currentTarget.value })} disabled={!canEdit} />
                    <NumberInput label="People per shelter" description="For the population estimate, printed as TBC" min={1} max={20} step={0.5} decimalScale={1}
                      value={household} onChange={(v) => { setHousehold(v); setDirty(true) }} disabled={!canEdit} />
                    <Group justify="space-between" mt="xs">
                      <Text size="sm" fw={500}>Where do we act first?</Text>
                      {canEdit && <Button size="compact-xs" variant="light" color="violet" leftSection={<IconSparkles size={13} />} onClick={suggest}>Suggest from the map</Button>}
                    </Group>
                    {findings.gaps.length === 0 && <Text size="xs" c="dimmed">No gaps yet. Suggest them from the map (closed routes, services not working, hazards over shelters), then edit.</Text>}
                    {findings.gaps.map((gp, i) => (
                      <Paper key={i} withBorder p="xs">
                        <Group gap={6} wrap="nowrap" mb={6}>
                          <Badge variant="filled" color={gp.status === 'no' ? 'red' : 'orange'} size="sm">{i + 1}</Badge>
                          <Select size="xs" w={110} value={gp.status} onChange={(v) => v && setGap(i, { status: v as Gap['status'] })} disabled={!canEdit}
                            data={[{ value: 'no', label: 'Urgent' }, { value: 'partial', label: 'High' }]} allowDeselect={false} />
                          {canEdit && <Group gap={0} ml="auto" wrap="nowrap">
                            <ActionIcon size="sm" variant="subtle" color="gray" disabled={i === 0} onClick={() => moveGap(i, -1)}><IconArrowUp size={14} /></ActionIcon>
                            <ActionIcon size="sm" variant="subtle" color="gray" disabled={i === findings.gaps.length - 1} onClick={() => moveGap(i, 1)}><IconArrowDown size={14} /></ActionIcon>
                            <ActionIcon size="sm" variant="subtle" color="red" onClick={() => setFindings({ gaps: findings.gaps.filter((_, j) => j !== i) })}><IconTrash size={14} /></ActionIcon>
                          </Group>}
                        </Group>
                        <TextInput size="xs" placeholder="The gap, e.g. Water: 2 of 6 points not working" value={gp.title} onChange={(e) => setGap(i, { title: e.currentTarget.value })} disabled={!canEdit} />
                        <Textarea size="xs" mt={4} autosize minRows={1} placeholder="What to do" value={gp.text} onChange={(e) => setGap(i, { text: e.currentTarget.value })} disabled={!canEdit} />
                        <TextInput size="xs" mt={4} placeholder="Who acts, e.g. WASH cluster" value={gp.who} onChange={(e) => setGap(i, { who: e.currentTarget.value })} disabled={!canEdit} />
                      </Paper>
                    ))}
                    {canEdit && findings.gaps.length < 5 && (
                      <Button size="xs" variant="subtle" leftSection={<IconPlus size={14} />}
                        onClick={() => setFindings({ gaps: [...findings.gaps, { status: 'partial', title: '', text: '', who: '' }] })}>Add a gap</Button>
                    )}
                  </Stack>
                </Tabs.Panel>
            </Tabs>
            {canEdit && (
              <Stack gap="xs" mt="sm">
                <Button variant="default" leftSection={<IconCrop size={16} />} onClick={() => save({ view: captureView() })}>Use the map's current view and layers</Button>
                <Group grow>
                  <Button variant="light" onClick={preview} loading={p.preview?.status === 'processing'}>Update preview</Button>
                  <Button leftSection={<IconPrinter size={16} />} onClick={render}>Render PDF</Button>
                </Group>
                {dirty && <Text size="xs" c="dimmed">Unsaved changes: Update preview or Render PDF saves them.</Text>}
                <Button variant="subtle" color="red" size="xs" leftSection={<IconTrash size={14} />} onClick={remove}>Delete product</Button>
              </Stack>
            )}
            <Text size="sm" fw={500} mt="md">Versions</Text>
            {p.versions.length === 0 && <Text size="xs" c="dimmed">Not rendered yet.</Text>}
            {p.versions.map((v) => (
              <Group key={v.n} gap="xs">
                <Badge variant="light" color={v.status === 'failed' ? 'red' : 'gray'}>v{v.n}</Badge>
                {v.pdf ? <Anchor size="sm" href={v.pdf} target="_blank">PDF · {new Date(v.rendered_at).toLocaleString()}</Anchor>
                  : v.status === 'processing' ? <Group gap={4}><Loader size="xs" /><Text size="xs">rendering</Text></Group>
                  : <Tooltip label={v.error} multiline w={400}><Text size="xs" c="red">failed</Text></Tooltip>}
              </Group>
            ))}
          </Stack>
        </ScrollArea>
        <Box style={{ flex: 1, height: '100%', overflow: 'auto', background: 'var(--mantine-color-gray-2)', borderRadius: 8, padding: 16 }}>
          {!canEdit && (
            <Text size="xs" c="dimmed" ta="center" mb={8}>
              View only. To change the page or update its preview, unlock editing with the response's edit key (<b>Unlock editing</b> at the top).
            </Text>
          )}
          {/* Viewers see the page as last printed; editors the draft of their changes */}
          {pageCount > 1 && (
            <Group justify="center" mb={8}><SegmentedControl size="xs" value={String(shown)} onChange={(v) => setShown(Number(v))}
              data={Array.from({ length: pageCount }, (_, i) => ({ value: String(i + 1), label: `Page ${i + 1}` }))} /></Group>
          )}
          {!canEdit && printed?.image ? (
            <>
              <img src={printed.images?.[shown - 1] || printed.image} alt={`Page 1, version ${printed.n}, as printed`} style={{ display: 'block', width: '100%', maxWidth: 1400, margin: '0 auto', boxShadow: '0 2px 12px rgba(0,0,0,.15)', background: '#fff' }} />
              <Text size="xs" ta="center" mt={8}>Version {printed.n}, printed {new Date(printed.rendered_at).toLocaleString()} · <Anchor size="xs" href={printed.pdf!} target="_blank">Open the PDF</Anchor></Text>
            </>
          ) : !canEdit && latestPdf ? (
            <iframe src={latestPdf} title="Page 1 as last printed" style={{ display: 'block', width: '100%', height: 'calc(100% - 28px)', border: 0, background: '#fff', boxShadow: '0 2px 12px rgba(0,0,0,.15)' }} />
          ) : p.preview?.url ? (
            <img src={p.preview.pages?.[shown - 1] || p.preview.url} alt="Preview of page 1" style={{ display: 'block', width: '100%', maxWidth: 1400, margin: '0 auto', boxShadow: '0 2px 12px rgba(0,0,0,.15)', background: '#fff', opacity: p.preview.status === 'processing' ? 0.5 : 1 }} />
          ) : (
            <Center h="60%"><Text c="dimmed">{p.preview?.status === 'processing' ? 'Rendering a draft…'
              : canEdit ? 'Click Update preview to see the page as it will print.' : 'Not printed yet.'}</Text></Center>
          )}
          <Group justify="center" gap={6} mt={8}>
            {p.preview?.status === 'processing' && <Loader size="xs" />}
            {!(!canEdit && latestPdf) && <Text size="xs" c={p.preview?.status === 'failed' ? 'red' : 'dimmed'}>
              {p.preview?.status === 'failed' ? `Preview failed: ${p.preview.error.slice(0, 300)}`
                : p.preview?.at ? `Draft at low resolution, ${new Date(p.preview.at).toLocaleTimeString()}. The PDF is 300 dpi.` : ''}
            </Text>}
          </Group>
        </Box>
      </Group>
    </Modal>
  )
}
