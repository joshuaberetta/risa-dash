import { Group, Paper, SimpleGrid, Stack, Table, Text } from '@mantine/core'
import type { Config, Summary } from '../api'
import { StatusBadge } from './FeaturePanel'

export default function SummaryPanel({ config, summary }: { config: Config; summary?: Summary }) {
  if (!summary) return null
  const S = config.symbology.status
  return (
    <Stack gap="sm" p="sm">
      <Text fw={600} size="sm">At a glance</Text>
      <SimpleGrid cols={2} spacing={6}>
        {summary.glance.map((g) => (
          <Paper key={g.label} withBorder p={8}>
            <Text fw={700} size="lg" lh={1.1}>{g.value || '–'}</Text>
            <Text size="xs" c="dimmed">{g.label}{g.tbc ? ' · TBC' : ''}</Text>
          </Paper>
        ))}
      </SimpleGrid>
      {summary.services.length > 0 && (
        <>
          <Text fw={600} size="sm" mt="xs">Which services still work?</Text>
          <Table fz="xs" verticalSpacing={3}>
            <Table.Thead>
              <Table.Tr><Table.Th>Service</Table.Th><Table.Th ta="right">All</Table.Th>
                <Table.Th ta="right" c={S.ok.color}>{S.ok.short}</Table.Th><Table.Th ta="right" c={S.partial.color}>Partly</Table.Th><Table.Th ta="right" c={S.no.color}>Not</Table.Th></Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {summary.services.map((s) => (
                <Table.Tr key={s.type}><Table.Td>{s.label}</Table.Td><Table.Td ta="right">{s.total}</Table.Td>
                  <Table.Td ta="right">{s.ok || '–'}</Table.Td><Table.Td ta="right">{s.partial || '–'}</Table.Td><Table.Td ta="right">{s.no || '–'}</Table.Td></Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </>
      )}
      {summary.route_list.length > 0 && (
        <>
          <Text fw={600} size="sm" mt="xs">Can we reach people?</Text>
          {summary.route_list.map((r, i) => (
            <Group key={i} gap="xs" wrap="nowrap"><StatusBadge config={config} status={r.status} /><Text size="xs">{r.label || 'Route'}{r.note ? ` · ${r.note}` : ''}</Text></Group>
          ))}
        </>
      )}
      {!!summary.pending_review && (
        <Text size="xs" c="violet.8">{summary.pending_review.toLocaleString()} detections from imagery are waiting for review. Accepted shelters count above.</Text>
      )}
      {summary.features === 0 && <Text size="xs" c="dimmed">Connect Kobo, upload vector data or draw on the map to see figures here.</Text>}
    </Stack>
  )
}
