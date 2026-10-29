import { Alert, Button, Code, CopyButton, Group, Modal, PasswordInput, Stack, Text } from '@mantine/core'
import { IconKey, IconLock, IconLockOpen } from '@tabler/icons-react'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, forgetEditKey, saveEditKey, setCurrentResponse } from '../api'

/** Unlock / lock editing for a response with its edit key. */
export function EditKeyButton({ slug, canEdit }: { slug: string; canEdit: boolean }) {
  const [open, setOpen] = useState(false)
  const [key, setKey] = useState('')
  const [err, setErr] = useState('')
  const qc = useQueryClient()
  const submit = async () => {
    saveEditKey(slug, key.trim())
    const r = await api<{ ok: boolean }>(`/responses/${slug}/check-key`, { method: 'POST' })
    if (!r.ok) {
      forgetEditKey(slug)
      setErr("That key doesn't match this response.")
      return
    }
    setOpen(false)
    setErr('')
    qc.invalidateQueries()
  }
  if (canEdit) {
    return (
      <Button size="xs" variant="subtle" color="gray" leftSection={<IconLockOpen size={14} />}
        onClick={() => { forgetEditKey(slug); setCurrentResponse(slug); qc.invalidateQueries() }}>
        Editing on · lock
      </Button>
    )
  }
  return (
    <>
      <Button size="xs" variant="light" leftSection={<IconLock size={14} />} onClick={() => setOpen(true)}>
        Unlock editing
      </Button>
      <Modal opened={open} onClose={() => setOpen(false)} title="Edit key">
        <Stack>
          <Text size="sm">Uploading, drawing, connecting Kobo and printing need this response's edit key. Ask whoever set up the response.</Text>
          <PasswordInput leftSection={<IconKey size={16} />} placeholder="Edit key" value={key} onChange={(e) => setKey(e.currentTarget.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()} error={err} data-autofocus />
          <Group justify="flex-end"><Button onClick={submit}>Unlock</Button></Group>
        </Stack>
      </Modal>
    </>
  )
}

export function ShowKey({ editKey }: { editKey: string }) {
  return (
    <Alert color="yellow" title="Save this edit key now" icon={<IconKey />}>
      <Stack gap="xs">
        <Text size="sm">It's shown once. Anyone with it can edit this response. It's saved in this browser.</Text>
        <Group gap="xs">
          <Code fz="md">{editKey}</Code>
          <CopyButton value={editKey}>{({ copied, copy }) => <Button size="xs" variant="light" onClick={copy}>{copied ? 'Copied' : 'Copy'}</Button>}</CopyButton>
        </Group>
      </Stack>
    </Alert>
  )
}
