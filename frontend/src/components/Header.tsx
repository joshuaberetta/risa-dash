import { Anchor, Badge, Group, Text } from '@mantine/core'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

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

export default function Header({ children }: { children?: ReactNode }) {
  return (
    <Group h="100%" px="md" justify="space-between" wrap="nowrap">
      <Group gap="md" wrap="nowrap" style={{ minWidth: 0 }}>
        <Logo />
        {children}
      </Group>
    </Group>
  )
}
