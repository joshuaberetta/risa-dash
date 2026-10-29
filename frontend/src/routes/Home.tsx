import { Anchor, AppShell, Badge, Button, Card, Container, Group, Modal, PasswordInput, Select, SimpleGrid, Stack, Text, TextInput, Title } from '@mantine/core'
import { DateInput } from '../components/DateInput'
import { IconPlus } from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { api, saveEditKey, type ResponseT } from '../api'
import { ShowKey } from '../components/EditKey'
import Header from '../components/Header'
import { useConfigData } from '../hooks'

const HAZARDS = ['Earthquake', 'Flood', 'Tropical cyclone', 'Conflict / displacement', 'Landslide', 'Volcano', 'Drought', 'Epidemic', 'Other']

export default function Home() {
  const config = useConfigData()
  const responses = useQuery({ queryKey: ['responses'], queryFn: () => api<(ResponseT & { sites: number })[]>('/responses') })
  const [open, setOpen] = useState(false)
  return (
    <AppShell header={{ height: 52 }}>
      <AppShell.Header><Header /></AppShell.Header>
      <AppShell.Main>
        <Container size="lg" py="xl">
          <Group justify="space-between" mb="lg">
            <div>
              <Title order={2}>Responses</Title>
              <Text c="dimmed" size="sm">Drone and satellite imagery, KoboCollect observations and analysis layers, printed as RISA page 1.</Text>
            </div>
            <Button leftSection={<IconPlus size={16} />} onClick={() => setOpen(true)}>New response</Button>
          </Group>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
            {responses.data?.map((r) => (
              <Card key={r.id} component={Link} to={`/r/${r.slug}`} withBorder padding="lg">
                <Group justify="space-between" mb={4}>
                  <Text fw={600}>{r.name}</Text>
                  {r.country && <Badge variant="light" color="gray">{r.country}</Badge>}
                </Group>
                <Text size="sm" c="dimmed">{[r.hazard, r.glide, r.start_date].filter(Boolean).join(' · ')}</Text>
                <Text size="xs" c="dimmed" mt="sm">{r.sites} site{r.sites === 1 ? '' : 's'}</Text>
              </Card>
            ))}
          </SimpleGrid>
          {responses.data?.length === 0 && <Text c="dimmed">No responses yet.</Text>}
          <Text size="sm" c="dimmed" mt={48} pt="md" style={{ borderTop: '1px solid var(--mantine-color-gray-3)' }}>
            RISA Dashboard is free and open-source software under the {config.licence} licence, the same as KoboToolbox.
            Anyone can run it, including fully offline or on their own servers.{' '}
            <Anchor href={config.source_url} target="_blank" rel="noopener" size="sm">Source code, documentation and self-hosting guide on GitHub</Anchor>.
          </Text>
        </Container>
        <NewResponse opened={open} onClose={() => setOpen(false)} />
      </AppShell.Main>
    </AppShell>
  )
}

function NewResponse({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const config = useConfigData()
  const nav = useNavigate()
  const [f, setF] = useState({ name: '', hazard: '', country: '', glide: '', start_date: null as string | null, language: 'en' })
  const [createKey, setCreateKey] = useState('')
  const [err, setErr] = useState('')
  const [made, setMade] = useState<{ slug: string; key: string } | null>(null)
  const submit = async () => {
    try {
      const r = await api<{ response: ResponseT; edit_key: string }>('/responses', {
        body: f, headers: createKey ? { 'X-Create-Key': createKey } : {},
      })
      saveEditKey(r.response.slug, r.edit_key)
      setMade({ slug: r.response.slug, key: r.edit_key })
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }
  return (
    <Modal opened={opened} onClose={onClose} title="New response" size="lg">
      {made ? (
        <Stack>
          <ShowKey editKey={made.key} />
          <Group justify="flex-end"><Button onClick={() => nav(`/r/${made.slug}`)}>Open response</Button></Group>
        </Stack>
      ) : (
        <Stack>
          <TextInput label="Name" placeholder="Venezuela: earthquake, June 2026" required value={f.name} onChange={(e) => setF({ ...f, name: e.currentTarget.value })} data-autofocus />
          <Group grow>
            <Select label="Hazard" data={HAZARDS} value={f.hazard || null} onChange={(v) => setF({ ...f, hazard: v || '' })} clearable />
            <TextInput label="Country (ISO3)" placeholder="VEN" maxLength={3} value={f.country} onChange={(e) => setF({ ...f, country: e.currentTarget.value.toUpperCase() })} />
          </Group>
          <Group grow>
            <TextInput label="GLIDE number" placeholder="EQ-2026-000093-VEN" value={f.glide} onChange={(e) => setF({ ...f, glide: e.currentTarget.value })} />
            <DateInput label="Start date" value={f.start_date} onChange={(v) => setF({ ...f, start_date: v })} />
            <Select label="Product language" data={[{ value: 'en', label: 'English' }, { value: 'es', label: 'Español' }, { value: 'fr', label: 'Français' }, { value: 'pt', label: 'Português' }]} value={f.language} onChange={(v) => setF({ ...f, language: v || 'en' })} />
          </Group>
          {config.create_key_required && (
            <PasswordInput label="Instance create key" description="This instance needs a key to create responses" value={createKey} onChange={(e) => setCreateKey(e.currentTarget.value)} />
          )}
          {err && <Text c="red" size="sm">{err}</Text>}
          <Group justify="flex-end"><Button onClick={submit} disabled={!f.name}>Create</Button></Group>
        </Stack>
      )}
    </Modal>
  )
}
