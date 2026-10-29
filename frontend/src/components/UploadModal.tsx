import { Button, Group, Modal, Progress, Select, Stack, Text, TextInput } from '@mantine/core'
import { Dropzone } from '@mantine/dropzone'
import { notifications } from '@mantine/notifications'
import { IconUpload } from '@tabler/icons-react'
import { useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { api, uploadFile, type SiteFull } from '../api'
import { DateInput } from './DateInput'

const RASTER = /\.(tiff?|geotiff|jp2|img|vrt)$/i

export function UploadModal({ site, opened, onClose }: { site: SiteFull; opened: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [captured, setCaptured] = useState<string | null>(null)
  const [attribution, setAttribution] = useState('')
  const [progress, setProgress] = useState<number | null>(null)
  const [err, setErr] = useState('')
  const abort = useRef<AbortController | null>(null)
  const isRaster = file ? RASTER.test(file.name) : false

  const pick = (f: File) => {
    setFile(f)
    setName(f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '))
    setErr('')
  }
  const start = async () => {
    if (!file) return
    setProgress(0)
    abort.current = new AbortController()
    try {
      await uploadFile(site.id, file, { name, captured_at: captured, attribution }, setProgress, abort.current.signal)
      notifications.show({ message: isRaster ? `${name}: uploaded, converting to a cloud-optimised GeoTIFF…` : `${name}: uploaded, importing…` })
      qc.invalidateQueries({ queryKey: ['site'] })
      setFile(null)
      setProgress(null)
      onClose()
    } catch (e) {
      setErr(String((e as Error).message))
      setProgress(null)
    }
  }
  return (
    <Modal opened={opened} onClose={() => { abort.current?.abort(); onClose() }} title="Upload a file" size="lg">
      <Stack>
        <Dropzone onDrop={(fs) => fs[0] && pick(fs[0])} multiple={false} maxSize={8 * 1024 ** 3}>
          <Group justify="center" gap="md" mih={110} style={{ pointerEvents: 'none' }}>
            <IconUpload size={32} stroke={1.5} />
            <div>
              <Text>{file ? file.name : 'Drop a file here or click to choose'}</Text>
              <Text size="xs" c="dimmed" mt={4}>
                Imagery: GeoTIFF orthomosaic or satellite scene (any projection, up to 8 GB).<br />
                Vector: GeoJSON, GeoPackage, zipped Shapefile, KML/KMZ, or CSV with latitude/longitude columns.
              </Text>
            </div>
          </Group>
        </Dropzone>
        {file && (
          <>
            <TextInput label="Layer name" value={name} onChange={(e) => setName(e.currentTarget.value)} />
            <Group grow>
              <DateInput label={isRaster ? 'Captured on' : 'Data date'} value={captured} onChange={setCaptured} />
              <TextInput label="Source / credit" placeholder={isRaster ? 'Drone orthomosaic, DJI Mini 4 Pro, 120 m AGL' : 'MapAction, OSM…'} value={attribution} onChange={(e) => setAttribution(e.currentTarget.value)} />
            </Group>
            <Text size="xs" c="dimmed">{(file.size / 1024 ** 2).toFixed(1)} MB · {isRaster ? 'imagery' : 'vector'} · uploads in 8 MB parts and resumes if the connection drops</Text>
          </>
        )}
        {progress !== null && <Progress value={progress * 100} animated />}
        {err && <Text c="red" size="sm">{err}</Text>}
        <Group justify="flex-end"><Button onClick={start} disabled={!file || progress !== null} loading={progress !== null}>Upload</Button></Group>
      </Stack>
    </Modal>
  )
}

export function UrlLayerModal({ site, opened, onClose }: { site: SiteFull; opened: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [f, setF] = useState({ name: '', kind: 'xyz', source: '', attribution: '', captured_at: null as string | null })
  const [err, setErr] = useState('')
  const submit = async () => {
    try {
      await api(`/sites/${site.id}/layers`, { body: f })
      qc.invalidateQueries({ queryKey: ['site'] })
      onClose()
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }
  return (
    <Modal opened={opened} onClose={onClose} title="Imagery by URL" size="lg">
      <Stack>
        <Text size="sm" c="dimmed">Needs the internet. For offline use, upload the GeoTIFF instead.</Text>
        <TextInput label="Name" value={f.name} onChange={(e) => setF({ ...f, name: e.currentTarget.value })} placeholder="Maxar pre-event, 2026-06-20" />
        <Select label="Type" value={f.kind} onChange={(v) => setF({ ...f, kind: v || 'xyz' })} data={[
          { value: 'xyz', label: 'XYZ / TMS tiles ({z}/{x}/{y})' },
          { value: 'cog_url', label: 'Cloud-optimised GeoTIFF (Web Mercator)' },
          { value: 'wms', label: 'WMS' },
        ]} />
        <TextInput label="URL" value={f.source} onChange={(e) => setF({ ...f, source: e.currentTarget.value })}
          placeholder={f.kind === 'xyz' ? 'https://tiles.openaerialmap.org/…/{z}/{x}/{y}' : f.kind === 'wms' ? 'https://…/wms?layers=…' : 'https://…/scene.tif'} />
        <Group grow>
          <TextInput label="Credit" value={f.attribution} onChange={(e) => setF({ ...f, attribution: e.currentTarget.value })} placeholder="© Maxar, CC BY-NC 4.0" />
          <DateInput label="Captured on" value={f.captured_at} onChange={(v) => setF({ ...f, captured_at: v })} />
        </Group>
        {err && <Text c="red" size="sm">{err}</Text>}
        <Group justify="flex-end"><Button onClick={submit} disabled={!f.name || !f.source}>Add layer</Button></Group>
      </Stack>
    </Modal>
  )
}
