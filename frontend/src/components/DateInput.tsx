import { TextInput } from '@mantine/core'

/** A plain date field (no date-picker dependency). Value is YYYY-MM-DD or null. */
export function DateInput({ label, value, onChange, description }: { label: string; value: string | null; onChange: (v: string | null) => void; description?: string }) {
  return <TextInput type="date" label={label} description={description} value={value || ''} onChange={(e) => onChange(e.currentTarget.value || null)} />
}
