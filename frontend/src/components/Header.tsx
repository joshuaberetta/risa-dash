import { ActionIcon, Anchor, Badge, Button, Group, Text, Tooltip } from '@mantine/core'
import { IconBook, IconBrandGithub, IconMessageCircle, IconRoute } from '@tabler/icons-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { useConfigData } from '../hooks'
import { startTour } from '../tour'

export function Logo() {
  return (
    <Anchor component={Link} to="/" underline="never" c="inherit" style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
      <Group gap={8} wrap="nowrap">
        <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden="true">
          <rect width="32" height="32" rx="6" fill="#18202e" />
          <circle cx="11" cy="12" r="4" fill="#1F9A62" />
          <circle cx="21" cy="12" r="4" fill="#E9A23B" />
          <circle cx="16" cy="21" r="4" fill="#A8281A" />
        </svg>
        <Text fw={700} size="sm">RISA <Text span inherit fw={400} c="dimmed">Dashboard</Text></Text>
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
      <Anchor href={config.source_url} target="_blank" rel="noopener" c="dimmed" underline="never" aria-label="Source code on GitHub" data-tour="source">
        <Group gap={5} wrap="nowrap">
          <IconBrandGithub size={18} />
          {withLabel && <Text size="xs" visibleFrom="md">Open source</Text>}
        </Group>
      </Anchor>
    </Tooltip>
  )
}

/** A labelled button on wide screens, its icon alone on narrower ones, so the bar fits. */
function HeaderButton({ label, tip, icon, tour, href, external, onClick }: {
  label: string; tip: string; icon: ReactNode; tour: string; href?: string; external?: boolean; onClick?: () => void
}) {
  const link = href ? { component: 'a' as const, href, ...(external ? { target: '_blank', rel: 'noopener' } : {}) } : { onClick }
  return (
    <Tooltip label={tip}>
      <span data-tour={tour}>
        <Button {...link} size="xs" variant="subtle" color="gray" leftSection={icon} visibleFrom="lg">{label}</Button>
        <ActionIcon {...link} variant="subtle" color="gray" aria-label={label} hiddenFrom="lg">{icon}</ActionIcon>
      </span>
    </Tooltip>
  )
}

/** `feedback`: the response's form with the site filled in; otherwise the instance's. */
export default function Header({ children, feedback }: { children?: ReactNode; feedback?: string }) {
  const config = useConfigData()
  const href = feedback || config.feedback_url
  return (
    <Group h="100%" px="md" justify="space-between" wrap="nowrap" gap="md">
      <Group gap="md" wrap="nowrap" style={{ minWidth: 0, flex: 1 }}>
        <Logo />
        {children}
      </Group>
      <Group gap="sm" wrap="nowrap">
        {href && (
          <HeaderButton label="Feedback" tip="Tell us what's missing, wrong or unclear on this map" icon={<IconMessageCircle size={15} />}
            tour="feedback" href={href} external />
        )}
        <HeaderButton label="Guide" tip="How to use the dashboard in a response: setup, imagery, Kobo, page 1, offline" icon={<IconBook size={15} />}
          tour="guide" href="/guide/" />
        <HeaderButton label="Tour" tip="A walk through this page" icon={<IconRoute size={15} />} tour="tour" onClick={startTour} />
        <SourceLink />
      </Group>
    </Group>
  )
}
