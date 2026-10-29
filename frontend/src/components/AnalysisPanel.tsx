import { Alert, Badge, Button, Group, Paper, Progress, SimpleGrid, Stack, Text, ThemeIcon, Tooltip, UnstyledButton } from '@mantine/core'
import { IconInfoCircle, IconSparkles } from '@tabler/icons-react'
import type { Analysis, Finding, Ref, Severity } from '../analysis'

export const AI_COLOR = 'violet'

const SEVERITY: Record<Severity, { label: string; variant: string }> = {
  high: { label: 'High', variant: 'filled' },
  medium: { label: 'Medium', variant: 'light' },
  low: { label: 'Low', variant: 'outline' },
}

const pct = (n: number) => `${Math.round(n * 100)}%`

function FindingCard({ f, active, onFocus }: { f: Finding; active: boolean; onFocus: (refs: Ref[], id: string) => void }) {
  return (
    <UnstyledButton onClick={() => onFocus(f.refs, f.id)} disabled={!f.refs.length}>
      <Paper withBorder p={8} style={{ borderColor: active ? `var(--mantine-color-${AI_COLOR}-5)` : undefined }}>
        <Group gap={6} mb={2} wrap="nowrap">
          <Badge size="xs" color={AI_COLOR} variant={SEVERITY[f.severity].variant}>{SEVERITY[f.severity].label}</Badge>
          <Text size="xs" c="dimmed">{f.topic}</Text>
        </Group>
        <Text size="sm" fw={600} lh={1.3}>{f.title}</Text>
        {f.detail && <Text size="xs" mt={2}>{f.detail}</Text>}
        <Text size="xs" c="dimmed" mt={4}>Based on: {f.basis}{f.refs.length ? ' · show on map' : ''}</Text>
      </Paper>
    </UnstyledButton>
  )
}

export default function AnalysisPanel({ analysis, active, onFocus }: {
  analysis: Analysis | null; active: string | null; onFocus: (refs: Ref[], id: string) => void
}) {
  if (!analysis) {
    return <Text size="xs" c="dimmed" p="sm">Add imagery and field observations to see an analysis here.</Text>
  }
  const im = analysis.imagery
  const maxShelters = im ? Math.max(...im.blocks.map((b) => b.shelters)) : 1
  return (
    <Stack gap="sm" p="sm">
      <Alert color={AI_COLOR} variant="light" p="xs" icon={<IconInfoCircle size={16} />} title="Example output">
        <Text size="xs">AI analysis isn't connected yet. This shows what it could return for this site. Shelter and people counts are illustrative: don't use them.</Text>
      </Alert>

      <div>
        <Group gap={6} mb={4}>
          <ThemeIcon size="sm" variant="light" color={AI_COLOR}><IconSparkles size={13} /></ThemeIcon>
          <Text fw={600} size="sm">Situation brief</Text>
        </Group>
        <Stack gap={6}>{analysis.brief.map((p, i) => <Text key={i} size="xs">{p}</Text>)}</Stack>
      </div>

      {im && (
        <div>
          <Text fw={600} size="sm" mb={4}>From the imagery</Text>
          <SimpleGrid cols={2} spacing={6}>
            <Paper withBorder p={8}>
              <Text fw={700} size="lg" lh={1.1}>{im.shelters.toLocaleString('en')}</Text>
              <Text size="xs" c="dimmed">shelters detected · {pct(im.confidence)} confidence</Text>
            </Paper>
            <Paper withBorder p={8}>
              <Text fw={700} size="lg" lh={1.1}>{im.people[0].toLocaleString('en')}–{im.people[1].toLocaleString('en')}</Text>
              <Text size="xs" c="dimmed">people (4.2–5.0 per shelter)</Text>
            </Paper>
          </SimpleGrid>
          <Stack gap={4} mt={8}>
            {im.blocks.map((b) => (
              <UnstyledButton key={b.ref.id} onClick={() => onFocus([b.ref], `block-${b.ref.id}`)}>
                <Group justify="space-between" gap={4} wrap="nowrap">
                  <Text size="xs" fw={active === `block-${b.ref.id}` ? 700 : 500}>{b.label}</Text>
                  <Tooltip label={`${b.perHa} shelters/ha · ${pct(b.confidence)} confidence${b.nearestWater != null ? ` · ${Math.round(b.nearestWater)} m to working water` : ''}`}>
                    <Text size="xs" c="dimmed">{b.shelters.toLocaleString('en')} shelters · ~{(Math.round(b.people / 100) * 100).toLocaleString('en')} people</Text>
                  </Tooltip>
                </Group>
                <Progress size={4} color={AI_COLOR} value={(b.shelters / maxShelters) * 100} />
              </UnstyledButton>
            ))}
          </Stack>
          {im.waterHa > 0 && <Text size="xs" mt={6}>Standing water: {im.waterHa.toFixed(2)} ha</Text>}
          <Text size="xs" c="dimmed" mt={6}>{im.caveat}</Text>
          <Text size="xs" c="dimmed" mt={4}>After review, these would fill “people (estimate)” and “shelters counted on imagery” on page 1.</Text>
        </div>
      )}

      {analysis.findings.length > 0 && (
        <div>
          <Text fw={600} size="sm" mb={4}>Findings</Text>
          <Stack gap={6}>
            {analysis.findings.map((f) => <FindingCard key={f.id} f={f} active={active === f.id} onFocus={onFocus} />)}
          </Stack>
        </div>
      )}

      {analysis.priorities.length > 0 && (
        <div>
          <Text fw={600} size="sm" mb={4}>Suggested priorities</Text>
          <Stack gap={4}>
            {analysis.priorities.map((p, i) => (
              <Group key={i} gap={8} wrap="nowrap" align="flex-start">
                <Badge size="sm" circle color={AI_COLOR} variant="light">{i + 1}</Badge>
                <Text size="xs">{p.text}</Text>
              </Group>
            ))}
          </Stack>
        </div>
      )}

      <div>
        <Text size="xs" c="dimmed">Inputs: {analysis.inputs.join(' · ')}</Text>
        <Group gap="xs" mt={8}>
          <Tooltip label="Not connected yet"><Button size="compact-xs" variant="light" color={AI_COLOR} leftSection={<IconSparkles size={13} />} disabled>Run analysis</Button></Tooltip>
          <Tooltip label="Not connected yet"><Button size="compact-xs" variant="default" disabled>Send to page 1</Button></Tooltip>
        </Group>
      </div>
    </Stack>
  )
}
