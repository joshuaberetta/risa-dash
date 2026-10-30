// The one theme file for the web app. It follows kobo-dash's admin look
// (kobo-dash src/kobo_dash/static/site.css): its ink, muted and line greys, Kobo blue as
// the primary, 12 px cards and 8 px controls, and sentence-case badges. app.css holds the
// few rules Mantine's theme can't set. The printed page's colours are in
// backend/risa/page1.py (COLORS). The reserved status colours are not brand and live in
// symbology/risa.json; violet stays the colour of AI suggestions.
import { Badge, Card, createTheme, Modal, Popover, Tooltip, type CSSVariablesResolver } from '@mantine/core'

export const theme = createTheme({
  fontFamily: 'Inter, system-ui, sans-serif',
  headings: { fontFamily: 'Inter, system-ui, sans-serif', fontWeight: '700' },
  primaryColor: 'kobo',
  primaryShade: 6,
  colors: {
    // site.css --primary-wash (0), --primary (6), --primary-dark (7)
    kobo: ['#eaf2fc', '#d5e5f8', '#aacbf1', '#7eb0ea', '#5598e7', '#3c88de', '#2a78d6', '#1f62b5', '#184f95', '#104281'],
    // hover (0), badge (1), --line (2), --line-strong (3), --muted (6), --ink (9)
    gray: ['#f7f8fa', '#eef0f4', '#e3e7ee', '#c9d0db', '#aeb7c5', '#8a94a4', '#5e6878', '#454e5d', '#2c3442', '#18202e'],
    // --danger-wash (0), --danger (6)
    red: ['#fdf1f0', '#f9dedb', '#f1c9c5', '#e8a39c', '#dc7a70', '#cf5649', '#c0362c', '#a32c23', '#8e261f', '#6e1d18'],
    // --ok-wash (0), --ok (6)
    green: ['#e6f5ee', '#c8eadb', '#94d5b8', '#5fbf95', '#33a677', '#1d8f67', '#13795b', '#0f664d', '#0d5c45', '#0a4535'],
  },
  defaultRadius: 'md',
  radius: { xs: '4px', sm: '6px', md: '8px', lg: '12px', xl: '999px' },
  shadows: {
    xs: '0 1px 2px rgba(24, 32, 46, 0.04)',
    sm: '0 4px 14px rgba(24, 32, 46, 0.06)',
    md: '0 6px 24px rgba(24, 32, 46, 0.12)',
  },
  components: {
    Card: Card.extend({ defaultProps: { radius: 'lg', shadow: 'xs' } }),
    Modal: Modal.extend({ defaultProps: { radius: 'lg' } }),
    Popover: Popover.extend({ defaultProps: { shadow: 'md' } }),
    Tooltip: Tooltip.extend({ defaultProps: { radius: 'sm' } }),
    Badge: Badge.extend({ styles: { root: { textTransform: 'none', letterSpacing: '0.02em', fontWeight: 600 } } }),
  },
})

export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {},
  light: {
    '--mantine-color-text': '#18202e',
    '--mantine-color-default-border': '#c9d0db',
    '--mantine-color-default-hover': '#f7f8fa',
  },
  dark: {},
})
