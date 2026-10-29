import { AppShell, Badge, Button, Card, Container, Group, Modal, Select, SimpleGrid, Stack, Text, TextInput, Title } from '@mantine/core'
import { IconMapPin, IconPlus } from '@tabler/icons-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api, setCurrentResponse, type ResponseT, type SiteT } from '../api'
import { EditKeyButton } from '../components/EditKey'
import Header from '../components/Header'
import { usePageTour } from '../tour'
import { responseTour } from '../tours'

export const SITE_KINDS = [
  { value: 'camp', label: 'Camp / displacement site' },
  { value: 'collective', label: 'Collective centre' },
  { value: 'settlement', label: 'Informal settlement' },
  { value: 'neighbourhood', label: 'Neighbourhood' },
  { value: 'other', label: 'Other' },
]

export default function ResponsePage() {
  const { response: slug } = useParams()
  setCurrentResponse(slug)
  const q = useQuery({ queryKey: ['response', slug], queryFn: () => api<ResponseT & { sites: SiteT[] }>(`/responses/${slug}`) })
  const [open, setOpen] = useState(false)
  const r = q.data
  usePageTour('response', responseTour, !!r)
  return (
    <AppShell header={{ height: 52 }}>
      <AppShell.Header>
        <Header>
          <Text size="sm" c="dimmed" truncate>/ {r?.name}</Text>
        </Header>
      </AppShell.Header>
      <AppShell.Main>
        <Container size="lg" py="xl">
          {q.error && <Text c="red">{String(q.error)}</Text>}
          {r && (
            <>
              <Group justify="space-between" mb="lg" align="flex-start">
                <div>
                  <Title order={2}>{r.name}</Title>
                  <Group gap="xs" mt={4}>
                    {[r.hazard, r.country, r.glide, r.start_date].filter(Boolean).map((x) => <Badge key={x} variant="light" color="gray">{x}</Badge>)}
                  </Group>
                </div>
                <Group>
                  <span data-tour="edit-key"><EditKeyButton slug={r.slug} canEdit={r.can_edit} /></span>
                  {r.can_edit && <Button leftSection={<IconPlus size={16} />} onClick={() => setOpen(true)} data-tour="new-site">New site</Button>}
                </Group>
              </Group>
              <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} data-tour="sites">
                {r.sites.map((s) => (
                  <Card key={s.id} component={Link} to={`/r/${r.slug}/${s.slug}`} withBorder padding="lg">
                    <Group gap="xs"><IconMapPin size={16} /><Text fw={600}>{s.name}</Text></Group>
                    <Text size="sm" c="dimmed" mt={4}>{s.place || SITE_KINDS.find((k) => k.value === s.kind)?.label}</Text>
                  </Card>
                ))}
              </SimpleGrid>
              {r.sites.length === 0 && <Text c="dimmed">No sites yet. {r.can_edit ? 'Add the first site you assessed.' : 'Unlock editing to add one.'}</Text>}
              <NewSite slug={r.slug} opened={open} onClose={() => setOpen(false)} />
            </>
          )}
        </Container>
      </AppShell.Main>
    </AppShell>
  )
}

function NewSite({ slug, opened, onClose }: { slug: string; opened: boolean; onClose: () => void }) {
  const nav = useNavigate()
  const qc = useQueryClient()
  const [f, setF] = useState({ name: '', place: '', kind: 'camp', latlon: '' })
  const [err, setErr] = useState('')
  const submit = async () => {
    let center: [number, number] | null = null
    if (f.latlon.trim()) {
      const m = f.latlon.split(/[ ,;]+/).map(Number)
      if (m.length !== 2 || m.some(isNaN)) return setErr('Location as "latitude, longitude", e.g. 10.49, -66.88')
      center = [m[1], m[0]]
    }
    try {
      const s = await api<SiteT>(`/responses/${slug}/sites`, { body: { name: f.name, place: f.place, kind: f.kind, center, zoom: 17 } })
      qc.invalidateQueries({ queryKey: ['response', slug] })
      nav(`/r/${slug}/${s.slug}`)
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }
  return (
    <Modal opened={opened} onClose={onClose} title="New site">
      <Stack>
        <TextInput label="Name" placeholder="Campamento Transitorio Estadio Cesar Nieves" required value={f.name} onChange={(e) => setF({ ...f, name: e.currentTarget.value })} data-autofocus />
        <TextInput label="Place" placeholder="Caracas, Distrito Capital" value={f.place} onChange={(e) => setF({ ...f, place: e.currentTarget.value })} />
        <Select label="Kind" data={SITE_KINDS} value={f.kind} onChange={(v) => setF({ ...f, kind: v || 'camp' })} />
        <TextInput label="Location (optional)" description="Latitude, longitude. Otherwise the map zooms to the first layer you add." placeholder="10.4917, -66.8792" value={f.latlon} onChange={(e) => setF({ ...f, latlon: e.currentTarget.value })} />
        {err && <Text c="red" size="sm">{err}</Text>}
        <Group justify="flex-end"><Button onClick={submit} disabled={!f.name}>Create site</Button></Group>
      </Stack>
    </Modal>
  )
}
