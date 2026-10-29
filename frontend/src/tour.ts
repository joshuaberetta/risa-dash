// Walkthrough: highlights the parts of a page in turn. Each page registers its own
// steps; the tour starts by itself the first time someone opens that kind of page,
// and again from "Tour" in the header (or ?tour in the URL, for demos).
//
// Steps point at elements with data-tour="…". Steps whose element isn't on the page
// (e.g. drawing tools when editing is locked) are skipped.

import { driver, type DriveStep } from 'driver.js'
import 'driver.js/dist/driver.css'
import { useEffect } from 'react'

export interface TourStep {
  /** data-tour value of the element to highlight; none for a centred note */
  target?: string
  title: string
  body: string
  side?: 'top' | 'bottom' | 'left' | 'right'
  /** e.g. switch to the tab the step talks about */
  before?: () => void
}

interface Registered {
  name: string
  steps: () => TourStep[]
}

let current: Registered | null = null
const SEEN = 'risa-tour-seen:'

const el = (target: string) => document.querySelector<HTMLElement>(`[data-tour="${target}"]`)

export function startTour() {
  if (!current) return
  const steps = current.steps().filter((s) => !s.target || el(s.target))
  if (!steps.length) return
  const d = driver({
    showProgress: true,
    progressText: '{{current}} of {{total}}',
    nextBtnText: 'Next',
    prevBtnText: 'Back',
    doneBtnText: 'Done',
    allowClose: true,
    overlayOpacity: 0.55,
    stagePadding: 6,
    stageRadius: 6,
    popoverClass: 'risa-tour',
    steps: steps.map((s): DriveStep => ({
      // Resolved when the step shows, so tabs switched by `before` are found
      element: s.target ? () => el(s.target!) || document.body : undefined,
      popover: { title: s.title, description: s.body, side: s.side, align: 'start' },
      onHighlightStarted: () => s.before?.(),
    })),
    onDestroyed: () => localStorage.setItem(SEEN + current?.name, '1'),
  })
  // The first step's `before` runs before anything is measured
  steps[0].before?.()
  d.drive()
}

/** Register this page's tour; start it once, the first time, when `ready`. */
export function usePageTour(name: string, steps: () => TourStep[], ready: boolean) {
  useEffect(() => {
    const reg = { name, steps }
    current = reg
    return () => {
      if (current === reg) current = null
    }
  })
  useEffect(() => {
    if (!ready) return
    const forced = new URLSearchParams(window.location.search).has('tour')
    if (!forced && localStorage.getItem(SEEN + name)) return
    // Let the map and panels lay out first
    const t = setTimeout(startTour, forced ? 600 : 1200)
    return () => clearTimeout(t)
  }, [ready, name])
}

export const hasTour = () => !!current
