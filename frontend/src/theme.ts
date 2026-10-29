// The one theme file. Neutral for now; the chosen RISA brand direction replaces these
// values later. The reserved status colours are not brand and live in symbology/risa.json.
import { createTheme } from '@mantine/core'

export const theme = createTheme({
  fontFamily: 'Inter, system-ui, sans-serif',
  headings: { fontFamily: 'Inter, system-ui, sans-serif', fontWeight: '650' },
  primaryColor: 'slate',
  colors: {
    slate: ['#f1f4f8', '#e2e7ee', '#c3ccd8', '#a1afc1', '#8495ad', '#7185a1', '#667c9b', '#556988', '#4a5d7a', '#3b5070'],
  },
  defaultRadius: 'sm',
})

// Used by the printed product (page 1 header band etc.)
export const brand = {
  band: '#1D2A3A',
  bandInk: '#FFFFFF',
  accent: '#E2E7EE',
  accentInk: '#1D2A3A',
  rule: '#D9DEE4',
  muted: '#4A5A6D',
}
