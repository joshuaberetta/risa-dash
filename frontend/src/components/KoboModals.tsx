import { Button, Group, Loader, Modal, PasswordInput, Select, Stack, Table, Text, TextInput } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type FieldMap, type KoboQuestion, type LayerT, type SiteFull, type Status } from '../api'
import { useConfigData } from '../hooks'

const KNOWN: Record<string, string> = {
  'https://kf.kobotoolbox.org': 'Global (kf.kobotoolbox.org)',
  'https://eu.kobotoolbox.org': 'European Union (eu.kobotoolbox.org)',
}

export function KoboConnectModal({ site, opened, onClose }: { site: SiteFull; opened: boolean; onClose: () => void }) {
  const config = useConfigData()
  const qc = useQueryClient()
  const [server, setServer] = useState(config.allowed_servers[0] || '')
  const [token, setToken] = useState('')
  const [projects, setProjects] = useState<{ uid: string; name: string; submissions: number }[] | null>(null)
  const [uid, setUid] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const load = async () => {
    setBusy(true)
    setErr('')
    try {
      setProjects(await api(`/responses/${site.response.slug}/kobo/projects`, { body: { server, token } }))
    } catch (e) {
      setErr(String((e as Error).message))
    }
    setBusy(false)
  }
  const connect = async () => {
    setBusy(true)
    try {
      const p = projects?.find((x) => x.uid === uid)
      await api(`/sites/${site.id}/kobo`, { body: { server, token, asset_uid: uid, name: p?.name || '' } })
      notifications.show({ message: 'Connected. Pulling submissions…' })
      qc.invalidateQueries({ queryKey: ['site'] })
      onClose()
    } catch (e) {
      setErr(String((e as Error).message))
    }
    setBusy(false)
  }
  return (
    <Modal opened={opened} onClose={onClose} title="Connect a Kobo project" size="lg">
      <Stack>
        <Select label="Server" data={config.allowed_servers.map((s) => ({ value: s, label: KNOWN[s] || s }))} value={server} onChange={(v) => { setServer(v || ''); setProjects(null) }}
          description="Servers this instance may use. A private server (or a box's local Kobo) is added by the administrator with ALLOWED_SERVERS." />
        <PasswordInput label="API token" description="Kobo: Account settings › Security › API key. Stored encrypted on this server and only sent to the Kobo server above." value={token} onChange={(e) => { setToken(e.currentTarget.value); setProjects(null) }} />
        {!projects && <Group justify="flex-end"><Button onClick={load} loading={busy} disabled={!server || !token}>List my projects</Button></Group>}
        {projects && (
          <>
            <Select label="Project" searchable data={projects.map((p) => ({ value: p.uid, label: `${p.name} (${p.submissions})` }))} value={uid} onChange={setUid}
              nothingFoundMessage="No deployed projects" />
            <Text size="xs" c="dimmed">Points come from the first geopoint question. Type and status are guessed from the form (works with the RISA form as is) and can be adjusted after.</Text>
            <Group justify="flex-end"><Button onClick={connect} loading={busy} disabled={!uid}>Connect and sync</Button></Group>
          </>
        )}
        {err && <Text c="red" size="sm">{err}</Text>}
      </Stack>
    </Modal>
  )
}

export function KoboMappingModal({ layer, onClose }: { layer: LayerT; onClose: () => void }) {
  const config = useConfigData()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['kobo', layer.id], queryFn: () => api<{ field_map: FieldMap; questions: KoboQuestion[] }>(`/layers/${layer.id}/kobo`) })
  const [fm, setFm] = useState<FieldMap | null>(null)
  const map = fm || q.data?.field_map
  const qs = q.data?.questions || []
  const opts = (types?: string[]) => qs.filter((x) => !types || types.includes(x.type)).map((x) => ({ value: x.path, label: `${x.label || x.name} (${x.path})` }))
  const set = (patch: Partial<FieldMap>) => setFm({ ...(map as FieldMap), ...patch })
  const statusQ = qs.find((x) => x.path === map?.status)
  const typeQ = qs.find((x) => x.path === map?.type)
  const statusOpts = (Object.keys(config.symbology.status) as Status[]).map((s) => ({ value: s, label: config.symbology.status[s].label }))
  const typeOpts = Object.entries(config.symbology.types).map(([k, v]) => ({ value: k, label: v.label }))
  const save = async () => {
    await api(`/layers/${layer.id}/kobo`, { method: 'PATCH', body: { field_map: map } })
    notifications.show({ message: 'Saved. Re-applying to every submission…' })
    qc.invalidateQueries({ queryKey: ['site'] })
    onClose()
  }
  const choiceMap = (key: 'status_map' | 'type_map', question: KoboQuestion | undefined, options: { value: string; label: string }[]) =>
    question?.choices?.length ? (
      <Table withRowBorders={false} verticalSpacing={2}>
        <Table.Tbody>
          {question.choices.map((c) => (
            <Table.Tr key={c.name}>
              <Table.Td><Text size="sm">{c.label || c.name}</Text></Table.Td>
              <Table.Td w={240}>
                <Select size="xs" data={options} clearable placeholder="Not mapped" value={map?.[key]?.[c.name] || null}
                  onChange={(v) => set({ [key]: { ...(map?.[key] || {}), [c.name]: v || '' } } as Partial<FieldMap>)} />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    ) : null
  return (
    <Modal opened onClose={onClose} title={`Map ${layer.name} to RISA`} size="xl">
      {!map ? <Loader /> : (
        <Stack>
          <Select label="Location question" data={opts(['geopoint', 'geotrace', 'geoshape'])} value={map.geo || null} onChange={(v) => set({ geo: v || '' })} />
          <Group grow align="flex-start">
            <Stack gap="xs">
              <Select label="Type of infrastructure / service" data={opts(['select_one', 'text'])} value={map.type || null} onChange={(v) => set({ type: v || '' })} clearable />
              {choiceMap('type_map', typeQ, typeOpts)}
            </Stack>
            <Stack gap="xs">
              <Select label="Status" data={opts(['select_one'])} value={map.status || null} onChange={(v) => set({ status: v || '' })} clearable
                description="Unmapped answers show as Not assessed (grey), never as a status" />
              {choiceMap('status_map', statusQ, statusOpts)}
            </Stack>
          </Group>
          <Select label="Label" data={opts()} value={map.label || null} onChange={(v) => set({ label: v || '' })} clearable />
          <TextInput label="Left out (sensitive)" description="Question paths, comma separated. Not stored on this server." value={(map.sensitive || []).join(', ')}
            onChange={(e) => set({ sensitive: e.currentTarget.value.split(',').map((s) => s.trim()).filter(Boolean) })} />
          <Group justify="flex-end"><Button onClick={save}>Save and re-sync</Button></Group>
        </Stack>
      )}
    </Modal>
  )
}
