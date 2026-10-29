// What each page's walkthrough says. Kept together so the wording can be edited in
// one place (and translated later). See tour.ts for how they run.

import type { TourStep } from './tour'

export const homeTour = (): TourStep[] => [
  {
    title: 'Welcome to the RISA Dashboard',
    body: 'RISA (Rapid Infrastructure and Service Assessment) puts drone and satellite imagery, KoboCollect observations and analysis on one map, and prints the result as RISA page 1. This tour takes a minute.',
  },
  {
    target: 'responses',
    title: 'Responses',
    body: 'Each emergency response has its sites: camps, collective centres or settlements. Open the sample response to see a site with real drone imagery and test data.',
    side: 'bottom',
  },
  {
    target: 'new-response',
    title: 'Start a response',
    body: 'Create a response for a new emergency. You get an edit key to share with your team; there are no accounts to set up.',
    side: 'left',
  },
  {
    target: 'about',
    title: 'Free and open source',
    body: 'Anyone can run it: on this hosted instance, on a national authority’s own server, or fully offline next to a local Kobo server.',
    side: 'top',
  },
  {
    target: 'tour',
    title: 'Tours',
    body: 'Every page has its own tour. Run one again from here, or add ?tour to a link to start it for a demo.',
    side: 'bottom',
  },
]

export const responseTour = (): TourStep[] => [
  {
    target: 'sites',
    title: 'Sites in this response',
    body: 'Open a site to see its map, layers, figures and printed products.',
    side: 'bottom',
  },
  {
    target: 'edit-key',
    title: 'Editing',
    body: 'Viewing is open to anyone with the link. Adding sites, uploading imagery, drawing and printing need the response’s edit key.',
    side: 'bottom',
  },
  {
    target: 'new-site',
    title: 'Add a site',
    body: 'Give it a name and, if you have it, a location. The map zooms to the first imagery or data you add.',
    side: 'left',
  },
]

export const siteTour = ({ showSummary, showAi }: { showSummary: () => void; showAi: () => void }): TourStep[] => [
  {
    title: 'A RISA site',
    body: 'One site in a response: imagery, field observations and analysis on one map, with the figures and printed product built from them. Restart this tour any time from Tour at the top.',
    before: showSummary,
  },
  {
    target: 'map',
    title: 'The map',
    body: 'Click any point, line or area for its details and photos. Status is always shown twice, by colour and by shape: solid or filled is working, dashed or half-filled is restricted, dotted or crossed out is closed.',
    side: 'left',
  },
  {
    target: 'layers',
    title: 'Layers',
    body: 'Drone orthomosaics, satellite scenes, Kobo projects and vector files. Turn them on and off, fade them and reorder them. Add uploads a GeoTIFF of any size (it resumes if the connection drops), connects a Kobo project, or adds imagery by URL.',
    side: 'right',
  },
  {
    target: 'basemap',
    title: 'Basemaps',
    body: 'Online basemaps when there’s a connection, or offline extracts loaded onto a box that has none.',
    side: 'right',
  },
  {
    target: 'tools',
    title: 'Draw and measure',
    body: 'Draw points, lines and areas and tag them with a RISA type and status, then reshape them later. Anyone can measure distances and areas.',
    side: 'bottom',
  },
  {
    target: 'legend',
    title: 'Legend',
    body: 'Built from what’s on the map, and the same on the printed page.',
    side: 'right',
  },
  {
    target: 'summary',
    title: 'The RISA questions, in numbers',
    body: 'Can we reach people? Which services still work? The at-a-glance figures here go straight onto page 1.',
    side: 'left',
    before: showSummary,
  },
  {
    target: 'products',
    title: 'RISA page 1',
    body: 'Frame the map and make the Common Operational Picture at A3 or A4: key message, figures, legend, sources and a QR code to the live map. It’s rendered on the server at 300 dpi, small enough to send on WhatsApp, and every version is kept.',
    side: 'left',
    before: showSummary,
  },
  {
    target: 'ai',
    title: 'AI analysis',
    body: 'Detect shelters on the imagery, grouped into blocks with the site outlined. Every result is a suggestion to accept, reject or reshape; only accepted shelters count. Your corrections teach it: Learn from corrections makes a better version for this response. The detection is simulated for now.',
    side: 'left',
    before: showAi,
  },
  {
    target: 'data-table',
    title: 'Data table',
    body: 'Every record in a layer, with its photos, search and a status filter.',
    side: 'bottom',
  },
  {
    target: 'export',
    title: 'Take it to QGIS or ArcGIS',
    body: 'A GeoPackage of every vector layer opens in QGIS and ArcGIS Pro. Each imagery layer downloads as a cloud-optimised GeoTIFF.',
    side: 'bottom',
  },
  {
    target: 'edit-key',
    title: 'Editing',
    body: 'No accounts: anyone with the response’s edit key can edit. Viewing is open to anyone with the link.',
    side: 'bottom',
  },
  {
    target: 'source',
    title: 'Free and open source',
    body: 'AGPL-3.0, like KoboToolbox. Run it on your own server, or fully offline on a kobo-in-a-box.',
    side: 'bottom',
  },
  {
    target: 'tour',
    title: 'That’s the tour',
    body: 'Run it again from here, or add ?tour to a link to start it for a demo.',
    side: 'bottom',
    before: showSummary,
  },
]
