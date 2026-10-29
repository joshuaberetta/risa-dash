// The one theme file for the web app. Neutral for now; the chosen RISA brand direction
// replaces these values later. The printed page's colours are in backend/risa/page1.py
// (COLORS). The reserved status colours are not brand and live in symbology/risa.json.
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

