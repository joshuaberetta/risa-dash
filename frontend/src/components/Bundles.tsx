import { Alert, Anchor, Button, Checkbox, Group, Loader, Modal, PasswordInput, Progress, Stack, Table, Text } from '@mantine/core'
import { Dropzone } from '@mantine/dropzone'
import { IconDownload, IconPackageImport } from '@tabler/icons-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { api, importBundle, saveEditKey, type TransferT } from '../api'
import { useConfigData } from '../hooks'

export const BUNDLE_HELP = 'A bundle is the whole response in one file: sites, layers and their features, imagery, page 1 versions and their PDFs, and a GeoPackage per site. Use it to move a response between instances (the cloud and a Kobo in a box field kit, by USB drive when there is no link) or to archive it. Kobo tokens are not included.'

function count(n: number | undefined, thing: string) {
  return `${n || 'no'} ${thing}${n === 1 ? '' : 's'}`
}

function size(bytes: number) {
  return bytes >= 1024 ** 3 ? `${(bytes / 1024 ** 3).toFixed(1)} GB` : `${(bytes / 1024 ** 2).toFixed(1)} MB`
}

/** Make a bundle of a response and download it. */
export function BundleModal({ slug, onClose }: { slug: string; onClose: () => void }) {
  const qc = useQueryClient()
  const [imagery, setImagery] = useState(true)
  const [err, setErr] = useState('')
  const list = useQuery({
    queryKey: ['bundles', slug],
    queryFn: () => api<TransferT[]>(`/responses/${slug}/bundles`),
    refetchInterval: (q) => (q.state.data?.some((t) => t.status === 'processing') ? 2500 : false),
  })
  const make = async () => {
    setErr('')
    try {
      await api(`/responses/${slug}/bundles`, { body: { imagery } })
      qc.invalidateQueries({ queryKey: ['bundles', slug] })
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }
  const busy = list.data?.some((t) => t.status === 'processing')
  return (
    <Modal opened onClose={onClose} title="Response bundle" size="lg">
      <Stack>
        <Text size="sm">{BUNDLE_HELP}</Text>
        <Checkbox label="Include imagery" description="Leave it out to send only the work done on it, to an instance that already has the imagery. Much smaller over a thin link."
          checked={imagery} onChange={(e) => setImagery(e.currentTarget.checked)} />
        {err && <Text c="red" size="sm">{err}</Text>}
        <Group justify="flex-end"><Button onClick={make} loading={busy}>Make bundle</Button></Group>
        {!!list.data?.length && (
          <Table>
            <Table.Tbody>
              {list.data.map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td><Text size="sm">{new Date(t.created_at).toLocaleString()}</Text></Table.Td>
                  <Table.Td><Text size="sm" c="dimmed">{t.options.imagery === false ? 'Without imagery' : 'With imagery'}</Text></Table.Td>
                  <Table.Td>
                    {t.status === 'processing' && <Group gap="xs"><Loader size="xs" /><Text size="sm" c="dimmed">Making…</Text></Group>}
                    {t.status === 'failed' && <Text size="sm" c="red" title={t.error}>Failed</Text>}
                    {t.download && <Anchor size="sm" href={t.download}><Group gap={4}><IconDownload size={14} />Download, {size(t.size)}</Group></Anchor>}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Stack>
    </Modal>
  )
}

/** Upload a bundle from another instance and open the response it holds. */
export function ImportBundleModal({ onClose }: { onClose: () => void }) {
  const config = useConfigData()
  const nav = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [createKey, setCreateKey] = useState('')
  const [editKey, setEditKey] = useState('')
  const [progress, setProgress] = useState<number | null>(null)
  const [transfer, setTransfer] = useState<TransferT | null>(null)
  const [err, setErr] = useState('')
  const abort = useRef<AbortController | null>(null)
  const status = useQuery({
    queryKey: ['transfer', transfer?.id],
    queryFn: () => api<TransferT>(`/transfers/${transfer!.id}`),
    enabled: !!transfer,
    refetchInterval: (q) => (q.state.data?.status === 'processing' || !q.state.data ? 2000 : false),
  })
  const t = status.data
  const start = async () => {
    if (!file) return
    setErr('')
    setTransfer(null)
    setProgress(0)
    abort.current = new AbortController()
    try {
      setTransfer(await importBundle(file, { createKey, editKey }, setProgress, abort.current.signal))
    } catch (e) {
      setErr(String((e as Error).message))
      setProgress(null)
    }
  }
  const anyway = async () => {
    setErr('')
    try {
      await api(`/transfers/${transfer!.id}/import-anyway`, { method: 'POST', headers: createKey ? { 'X-Create-Key': createKey } : {} })
      await status.refetch()
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }
  const open = () => {
    if (!t?.response) return
    if (editKey) saveEditKey(t.response, editKey)
    nav(`/r/${t.response}`)
  }
  return (
    <Modal opened onClose={() => { abort.current?.abort(); onClose() }} title="Import a bundle" size="lg">
      <Stack>
        <Text size="sm">A bundle made on another instance, with <b>Bundle</b> on a response's page or <code>manage.py bundle export</code>. Importing it again later updates the response here with the bundle's changes.</Text>
        <Dropzone onDrop={(fs) => fs[0] && (setFile(fs[0]), setErr(''))} multiple={false} disabled={progress !== null && t?.status !== 'failed'} maxSize={64 * 1024 ** 3}>
          <Group justify="center" gap="md" mih={90} style={{ pointerEvents: 'none' }}>
            <IconPackageImport size={32} stroke={1.5} />
            <Text>{file ? `${file.name}, ${size(file.size)}` : 'Drop a bundle (.risa.zip) here or click to choose'}</Text>
          </Group>
        </Dropzone>
        <PasswordInput label="Edit key (if the response is already here)" description="Needed to update a response this instance has. The response keeps the edit key it had where it was made."
          value={editKey} onChange={(e) => setEditKey(e.currentTarget.value)} />
        {config.create_key_required && (
          <PasswordInput label="Instance create key" description="This instance needs a key to create or import responses" value={createKey} onChange={(e) => setCreateKey(e.currentTarget.value)} />
        )}
        {progress !== null && !transfer && <Progress value={progress * 100} animated />}
        {transfer && (!t || t.status === 'processing') && <Group gap="xs"><Loader size="xs" /><Text size="sm">Checking and importing…</Text></Group>}
        {t?.status === 'failed' && !t.result.older && <Alert color="red" title="Import failed">{t.error}</Alert>}
        {t?.status === 'failed' && t.result.older && (
          <Alert color="yellow" title="This bundle is older than what's here">
            <Stack gap="xs" align="flex-start">
              <Text size="sm">{t.error}</Text>
              <Button size="xs" color="yellow" variant="light" onClick={anyway}>Import anyway</Button>
            </Stack>
          </Alert>
        )}
        {t?.status === 'ready' && (
          <Alert color="green" title={t.result.created ? 'Imported' : 'Updated'}>
            {t.result.name}: {[count(t.result.sites, 'site'), count(t.result.layers, 'layer'), count(t.result.features, 'feature'),
              count(t.result.versions, 'printed version')].join(', ')}.
          </Alert>
        )}
        {err && <Text c="red" size="sm">{err}</Text>}
        <Group justify="flex-end">
          {t?.status === 'ready'
            ? <Button onClick={open}>Open response</Button>
            : <Button onClick={start} disabled={!file || (progress !== null && t?.status !== 'failed')}>Import</Button>}
        </Group>
      </Stack>
    </Modal>
  )
}
