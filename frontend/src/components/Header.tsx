import { Anchor, Badge, Group, Text, Tooltip } from '@mantine/core'
import { IconBrandGithub } from '@tabler/icons-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { useConfigData } from '../hooks'

export function Logo() {
  return (
    <Anchor component={Link} to="/" underline="never" c="inherit">
      <Group gap={8} wrap="nowrap">
        <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden="true">
          <rect width="32" height="32" rx="6" fill="#1D232B" />
          <circle cx="11" cy="12" r="4" fill="#1F9A62" />
          <circle cx="21" cy="12" r="4" fill="#E9A23B" />
          <circle cx="16" cy="21" r="4" fill="#A8281A" />
        </svg>
        <Text fw={700} size="sm">RISA Dashboard</Text>
        <Badge size="xs" variant="light" color="gray">MVP</Badge>
      </Group>
    </Anchor>
  )
}

/** Free and open source: the code is on GitHub (AGPL-3.0). */
export function SourceLink({ withLabel = true }: { withLabel?: boolean }) {
  const config = useConfigData()
  return (
    <Tooltip label={`Free and open source (${config.licence}). View the code on GitHub.`}>
      <Anchor href={config.source_url} target="_blank" rel="noopener" c="dimmed" underline="never" aria-label="Source code on GitHub">
        <Group gap={5} wrap="nowrap">
          <IconBrandGithub size={18} />
          {withLabel && <Text size="xs" visibleFrom="md">Open source</Text>}
        </Group>
      </Anchor>
    </Tooltip>
  )
}

export default function Header({ children }: { children?: ReactNode }) {
  return (
    <Group h="100%" px="md" justify="space-between" wrap="nowrap" gap="md">
      <Group gap="md" wrap="nowrap" style={{ minWidth: 0, flex: 1 }}>
        <Logo />
        {children}
      </Group>
      <SourceLink />
    </Group>
  )
}
