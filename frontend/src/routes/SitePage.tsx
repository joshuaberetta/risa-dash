import { ActionIcon, AppShell, Button, Center, Divider, Group, Loader, Menu, Modal, Paper, ScrollArea, Select, Tabs, Text, Tooltip } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconCheck, IconDownload, IconHome, IconLine, IconMapPin, IconPolygon, IconRuler2, IconRulerMeasure, IconSparkles, IconTable, IconX } from '@tabler/icons-react'
import turfBbox from '@turf/bbox'
import { useQueryClient } from '@tanstack/react-query'
import type { Map as MLMap } from 'maplibre-gl'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import type { TerraDraw } from 'terra-draw'
import { analyse, type Ref } from '../analysis'
import { api, setCurrentResponse, type LayerT, type ProductView } from '../api'
import AnalysisPanel, { AI_COLOR } from '../components/AnalysisPanel'
import DataTable from '../components/DataTable'
import { EditKeyButton } from '../components/EditKey'
import FeaturePanel, { FeatureForm, type FeatureFields } from '../components/FeaturePanel'
import Header from '../components/Header'
import LayerPanel from '../components/LayerPanel'
import Legend from '../components/Legend'
import { AnalyseButton, AnalysisProgress, LearnPanel } from '../components/Analysis'
import { siteTour } from '../tours'
import { usePageTour } from '../tour'
import { ProductsPanel } from '../components/Products'
import SummaryPanel from '../components/SummaryPanel'
import { useConfigData, useLayerData, useSite, useSummary } from '../hooks'
import { clearMeasurements, createDraw, editShape, formatArea, formatLength, isMeasureMode, type DrawMode, type Measurement } from '../map/draw'
import { legendData } from '../map/legend'
import MapView, { type LayerState, type PickedFeature } from '../map/MapView'

function unionBbox(layers: LayerT[]): [number, number, number, number] | null {
  const bs = layers.map((l) => l.bbox).filter(Boolean) as [number, number, number, number][]
  if (!bs.length) return null
  return [Math.min(...bs.map((b) => b[0])), Math.min(...bs.map((b) => b[1])), Math.max(...bs.map((b) => b[2])), Math.max(...bs.map((b) => b[3]))]
}

const TABLE_HEIGHT = 320

export default function SitePage() {
  const { response: rslug, site: sslug } = useParams()
  setCurrentResponse(rslug)
  const config = useConfigData()
  const qc = useQueryClient()
  const q = useSite(rslug, sslug)
  const site = q.data
  const storeKey = site ? `risa-view:${site.id}` : ''
  const [state, setStateAll] = useState<Record<string, LayerState>>({})
  const [basemap, setBasemap] = useState<string>(config.basemaps[0]?.id || 'none')
  const [picked, setPicked] = useState<PickedFeature | null>(null)
  const [pending, setPending] = useState<{ id: string; geometry: GeoJSON.Geometry } | null>(null)
  const [mode, setMode] = useState<DrawMode>('static')
  const [shapeEdit, setShapeEdit] = useState<PickedFeature | null>(null)
  const [measurement, setMeasurement] = useState<Measurement | null>(null)
  // Drawing shelters the detection missed, straight into this analysis layer
  const [addTo, setAddTo] = useState<string | null>(null)
  const addToRef = useRef<string | null>(null)
  addToRef.current = addTo
  const [tab, setTab] = useState<string | null>('summary')
  const [tableOpen, setTableOpen] = useState(false)
  const [focused, setFocused] = useState<{ id: string; geometries: GeoJSON.Geometry[] } | null>(null)
  const mapRef = useRef<MLMap | null>(null)
  const drawRef = useRef<TerraDraw | null>(null)
  const fitted = useRef(false)

  // Restore the layer state and basemap saved in this browser
  useEffect(() => {
    if (!storeKey) return
    try {
      const saved = JSON.parse(localStorage.getItem(storeKey) || '{}')
      if (saved.state) setStateAll(saved.state)
      if (saved.basemap && config.basemaps.some((b) => b.id === saved.basemap)) setBasemap(saved.basemap)
    } catch { /* ignore */ }
  }, [storeKey])
  useEffect(() => {
    if (storeKey) localStorage.setItem(storeKey, JSON.stringify({ state, basemap }))
  }, [state, basemap, storeKey])

  const layers = site?.layers || []
  const { data } = useLayerData(layers)
  const fullState = useMemo(() => {
    const out: Record<string, LayerState> = {}
    for (const l of layers) out[l.id] = state[l.id] || { visible: l.visible_default, opacity: l.style.opacity ?? 1 }
    return out
  }, [layers, state])
  const visibleIds = layers.filter((l) => fullState[l.id]?.visible && l.status === 'ready').map((l) => l.id)
  const summary = useSummary(site?.id, visibleIds, layers.map((l) => l.updated_at).join())
  const visibleLayers = layers.filter((l) => visibleIds.includes(l.id))
  const analysis = useMemo(() => site ? analyse(site.name, visibleLayers, data, (t) => config.symbology.types[t]?.label || t) : null,
    [site?.name, visibleIds.join(), data, config])
  const legend = useMemo(() => legendData(layers.filter((l) => fullState[l.id]?.visible), data), [layers, fullState, data])
  const setState = useCallback((id: string, s: Partial<LayerState>) => {
    setStateAll((cur) => {
      const l = layers.find((x) => x.id === id)
      const prev = cur[id] || { visible: l?.visible_default ?? true, opacity: l?.style.opacity ?? 1 }
      return { ...cur, [id]: { ...prev, ...s } }
    })
  }, [layers])

  // First view: the site's default, or all the layers
  useEffect(() => {
    const map = mapRef.current
    if (!map || !site || fitted.current) return
    const bb = unionBbox(layers)
    if (site.default_view?.center) {
      map.jumpTo({ center: site.default_view.center, zoom: site.default_view.zoom || 16, bearing: site.default_view.bearing || 0 })
      fitted.current = true
    } else if (bb) {
      map.fitBounds(bb, { padding: 40, duration: 0, maxZoom: 19 })
      fitted.current = true
    }
  }, [site, layers, mapRef.current])

  const onReady = (map: MLMap) => {
    mapRef.current = map
    drawRef.current = createDraw(map, (id, geometry) => {
      const target = addToRef.current
      if (!target) return setPending({ id, geometry })
      // Missed shelters go straight in, as accepted; keep drawing the next one
      api(`/layers/${target}/detections`, { body: { geometry, ai_class: 'shelter' } })
        .then(() => { drawRef.current?.removeFeatures([id]); qc.invalidateQueries({ queryKey: ['site'] }); qc.invalidateQueries({ queryKey: ['detector'] }) })
        .catch((e) => notifications.show({ color: 'red', message: String(e.message) }))
    }, setMeasurement)
    fitted.current = false
    qc.invalidateQueries({ queryKey: ['site'] })
  }
  const refresh = () => qc.invalidateQueries({ queryKey: ['site'] })

  // Outline features on the map (from an analysis finding or a table row) and frame them
  const focus = (id: string, geometries: GeoJSON.Geometry[]) => {
    if (focused?.id === id) return setFocused(null)
    setFocused({ id, geometries })
    if (!geometries.length) return
    const fc: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: geometries.map((geometry) => ({ type: 'Feature', geometry, properties: {} })) }
    const bb = turfBbox(fc) as [number, number, number, number]
    mapRef.current?.fitBounds(bb, { padding: 80, maxZoom: 18, duration: 600 })
  }
  const focusRefs = (refs: Ref[], id: string) => focus(id, refs.map((r) => r.geometry))
  const pickFromTable = (f: PickedFeature) => {
    setPicked(f)
    focus(`row-${f.id}`, [f.geometry])
  }

  const setDrawMode = (m: DrawMode) => {
    const d = drawRef.current
    if (!d) return
    if (m !== 'polygon') setAddTo(null)
    // Leaving measuring, or switching between distance and area, clears the measurement
    if (isMeasureMode(mode) && m !== mode) {
      clearMeasurements(d)
      setMeasurement(null)
    }
    d.setMode(m)
    setMode(m)
  }
  const clearMeasure = () => {
    if (drawRef.current) clearMeasurements(drawRef.current)
    setMeasurement(null)
  }
  useEffect(() => {
    // Esc stops drawing or measuring
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape' && mode !== 'static' && !shapeEdit) setDrawMode('static') }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })
  const saveDrawn = async (f: FeatureFields) => {
    if (!pending || !site) return
    try {
      await api(`/sites/${site.id}/annotations`, { body: { geometry: pending.geometry, ...f } })
      drawRef.current?.removeFeatures([pending.id])
      setPending(null)
      refresh()
    } catch (e) {
      notifications.show({ color: 'red', message: String((e as Error).message) })
    }
  }
  const cancelDrawn = () => {
    if (pending) drawRef.current?.removeFeatures([pending.id])
    setPending(null)
  }
  const saveFeature = async (f: FeatureFields) => {
    if (!picked) return
    await api(`/features/${picked.id}`, { method: 'PATCH', body: f })
    setPicked({ ...picked, properties: { ...picked.properties, risa_type: f.risa_type, risa_status: f.risa_status, risa_label: f.label } })
    refresh()
  }
  const reviewFeature = async (review: 'accepted' | 'rejected' | 'suggested') => {
    if (!picked) return
    await api(`/features/${picked.id}`, { method: 'PATCH', body: { review } })
    setPicked({ ...picked, properties: { ...picked.properties, review } })
    refresh()
  }
  const viewBounds = (): [number, number, number, number] | null => {
    const b = mapRef.current?.getBounds()
    return b ? [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()] : null
  }
  const deleteFeature = async () => {
    if (!picked || !confirm('Delete this feature?')) return
    await api(`/features/${picked.id}`, { method: 'DELETE' })
    setPicked(null)
    refresh()
  }
  const startShapeEdit = () => {
    const d = drawRef.current
    if (!picked || !d) return
    if (!editShape(d, picked.id, picked.geometry)) return notifications.show({ message: "This shape can't be edited here" })
    setMode('select')
    setShapeEdit(picked)
  }
  const finishShapeEdit = async (save: boolean) => {
    const d = drawRef.current
    if (!d || !shapeEdit) return
    const f = d.getSnapshotFeature(shapeEdit.id)
    if (save && f) {
      await api(`/features/${shapeEdit.id}`, { method: 'PATCH', body: { geometry: f.geometry } })
      setPicked({ ...shapeEdit, geometry: f.geometry as GeoJSON.Geometry })
      refresh()
    }
    d.clear()
    d.setMode('static')
    setMode('static')
    setShapeEdit(null)
  }
  const captureView = (): ProductView => {
    const map = mapRef.current!
    const b = map.getBounds()
    return {
      bounds: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()],
      center: map.getCenter().toArray() as [number, number],
      zoom: map.getZoom(),
      bearing: map.getBearing(),
      basemap,
      layers: layers.map((l) => ({ id: l.id, visible: fullState[l.id].visible, opacity: fullState[l.id].opacity })),
    }
  }
  const saveDefaultView = async () => {
    const map = mapRef.current
    if (!map || !site) return
    await api(`/sites/${site.id}`, { method: 'PATCH', body: { default_view: { center: map.getCenter().toArray(), zoom: map.getZoom(), bearing: map.getBearing() } } })
    notifications.show({ message: 'Saved as the site’s default view' })
    refresh()
  }

  usePageTour('site', () => siteTour({
    showSummary: () => { setPicked(null); setTab('summary') },
    showAi: () => { setPicked(null); setTab('ai') },
  }), !!site)

  if (q.error) return <Center h="100vh"><Text c="red">{String(q.error)}</Text></Center>
  if (!site) return <Center h="100vh"><Loader /></Center>
  const canEdit = site.response.can_edit
  const pickedLayer = picked ? layers.find((l) => l.id === picked.layerId) : undefined

  return (
    <AppShell header={{ height: 52 }} navbar={{ width: 310, breakpoint: 'sm' }} aside={{ width: 340, breakpoint: 'md' }}>
      <AppShell.Header>
        <Header>
          <Text size="sm" c="dimmed" truncate>
            / <Link to={`/r/${site.response.slug}`} style={{ color: 'inherit' }}>{site.response.name}</Link> / <b>{site.name}</b>
          </Text>
          <Group gap="xs" ml="auto" wrap="nowrap">
            <Button size="xs" variant={tableOpen ? 'light' : 'default'} leftSection={<IconTable size={14} />} onClick={() => setTableOpen(!tableOpen)} data-tour="data-table">Data table</Button>
            <span data-tour="edit-key"><EditKeyButton slug={site.response.slug} canEdit={canEdit} /></span>
            <Menu position="bottom-end">
              <Menu.Target><Button size="xs" variant="default" leftSection={<IconDownload size={14} />} data-tour="export">Export</Button></Menu.Target>
              <Menu.Dropdown>
                <Menu.Item component="a" href={`/api/sites/${site.id}/export.gpkg`}>GeoPackage (QGIS, ArcGIS Pro)</Menu.Item>
                <Menu.Label>Imagery: use “Download COG” on each layer</Menu.Label>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Header>
      </AppShell.Header>
      <AppShell.Navbar>
        <ScrollArea>
          <div data-tour="basemap">
            <Select size="xs" p="sm" pb={0} label="Basemap" value={basemap} onChange={(v) => v && setBasemap(v)}
              data={config.basemaps.map((b) => ({ value: b.id, label: b.name + (b.online ? '' : ' ✓ offline') }))} allowDeselect={false} />
          </div>
          <div data-tour="layers">
            <LayerPanel site={site} state={fullState} setState={setState} canEdit={canEdit}
              onZoom={(l) => l.bbox && mapRef.current?.fitBounds(l.bbox, { padding: 40, maxZoom: 20 })} />
          </div>
          <Divider />
          <div data-tour="legend">
            <Text fw={600} size="sm" px="sm" pt="sm">Legend</Text>
            <div style={{ padding: '0 12px 12px', fontSize: 13 }}><Legend config={config} data={legend} compact /></div>
          </div>
          {canEdit && (
            <Group px="sm" pb="md">
              <Button size="compact-xs" variant="subtle" color="gray" leftSection={<IconHome size={13} />} onClick={saveDefaultView}>Save view as site default</Button>
            </Group>
          )}
        </ScrollArea>
      </AppShell.Navbar>
      <AppShell.Main style={{ height: '100vh', paddingBottom: 0 }}>
        <div data-tour="map" style={{ position: 'relative', height: tableOpen ? `calc(100vh - 52px - ${TABLE_HEIGHT}px)` : 'calc(100vh - 52px)' }}>
          <MapView config={config} basemap={basemap} layers={layers} state={fullState} data={data} highlight={focused?.geometries}
            initial={site.default_view?.center ? site.default_view : undefined}
            onReady={onReady} onFeatureClick={(f) => mode === 'static' && setPicked(f)} />
          <Paper shadow="sm" p={4} withBorder style={{ position: 'absolute', top: 10, left: 10, zIndex: 2 }} data-tour="tools">
            {shapeEdit ? (
              <Group gap={4}>
                <Text size="xs" px={4}>Drag the vertices</Text>
                <Button size="compact-xs" leftSection={<IconCheck size={13} />} onClick={() => finishShapeEdit(true)}>Save shape</Button>
                <Button size="compact-xs" variant="default" onClick={() => finishShapeEdit(false)}>Cancel</Button>
              </Group>
            ) : (
              <Group gap={2}>
                {canEdit && ([['point', IconMapPin, 'Draw a point (service, gate…)'], ['linestring', IconLine, 'Draw a line (route, fence…)'], ['polygon', IconPolygon, 'Draw an area (block, building, flood…)']] as const).map(([m, Icon, label]) => (
                  <Tooltip key={m} label={label} position="bottom">
                    <ActionIcon aria-label={label} variant={mode === m ? 'filled' : 'subtle'} color={mode === m ? undefined : 'gray'} onClick={() => setDrawMode(mode === m ? 'static' : m)}><Icon size={18} /></ActionIcon>
                  </Tooltip>
                ))}
                {canEdit && <Divider orientation="vertical" mx={2} />}
                {([['measure-line', IconRuler2, 'Measure distance'], ['measure-area', IconRulerMeasure, 'Measure area']] as const).map(([m, Icon, label]) => (
                  <Tooltip key={m} label={label} position="bottom">
                    <ActionIcon aria-label={label} variant={mode === m ? 'filled' : 'subtle'} color={mode === m ? 'dark' : 'gray'} onClick={() => setDrawMode(mode === m ? 'static' : m)}><Icon size={18} /></ActionIcon>
                  </Tooltip>
                ))}
                {mode !== 'static' && <Tooltip label="Stop (Esc)"><ActionIcon aria-label="Stop" variant="subtle" color="gray" onClick={() => setDrawMode('static')}><IconX size={18} /></ActionIcon></Tooltip>}
              </Group>
            )}
          </Paper>
          {isMeasureMode(mode) && (
            <Paper shadow="sm" withBorder px="sm" py={6} style={{ position: 'absolute', top: 54, left: 10, zIndex: 2, minWidth: 190 }}>
              {measurement ? (
                <Group justify="space-between" gap="md" wrap="nowrap">
                  <div>
                    {measurement.kind === 'line' ? (
                      <Text fw={700} size="lg" lh={1.2}>{formatLength(measurement.length)}</Text>
                    ) : (
                      <>
                        <Text fw={700} size="lg" lh={1.2}>{formatArea(measurement.area)}</Text>
                        <Text size="xs" c="dimmed">Perimeter {formatLength(measurement.length)}</Text>
                      </>
                    )}
                    {!measurement.done && <Text size="xs" c="dimmed">{measurement.kind === 'line' ? 'Click the last point again to finish' : 'Click the first point to close'}</Text>}
                  </div>
                  <Button size="compact-xs" variant="subtle" color="gray" onClick={clearMeasure}>Clear</Button>
                </Group>
              ) : (
                <Text size="xs" c="dimmed">{mode === 'measure-line' ? 'Click points along the way to measure a distance' : 'Click around an area to measure it'}</Text>
              )}
            </Paper>
          )}
          <AnalysisProgress layers={layers} />
          {mode !== 'static' && !shapeEdit && !isMeasureMode(mode) && (
            <Paper shadow="sm" px="sm" py={4} style={{ position: 'absolute', bottom: 30, left: '50%', transform: 'translateX(-50%)', zIndex: 2 }}>
              <Text size="xs">{mode === 'point' ? 'Click to place a point' : 'Click to add vertices, click the last point again (or the first, for an area) to finish'}</Text>
            </Paper>
          )}
        </div>
        {tableOpen && (
          <div style={{ height: TABLE_HEIGHT, borderTop: '1px solid var(--mantine-color-gray-3)', background: 'white' }}>
            <DataTable config={config} layers={layers.filter((l) => ['kobo', 'vector', 'annotations'].includes(l.kind))} data={data}
              onPick={pickFromTable} onClose={() => setTableOpen(false)} />
          </div>
        )}
      </AppShell.Main>
      <AppShell.Aside>
        <ScrollArea>
          {picked ? (
            <FeaturePanel config={config} feature={picked} layer={pickedLayer} canEdit={canEdit} onClose={() => { setPicked(null); if (focused?.id.startsWith('row-')) setFocused(null) }}
              onSave={saveFeature} onDelete={deleteFeature} onEditShape={startShapeEdit} onReview={reviewFeature} />
          ) : (
            <Tabs value={tab} onChange={setTab}>
              <Tabs.List grow>
                <Tabs.Tab value="summary">Summary</Tabs.Tab>
                <Tabs.Tab value="ai" color={AI_COLOR} leftSection={<IconSparkles size={14} />}>AI analysis</Tabs.Tab>
              </Tabs.List>
              <Tabs.Panel value="summary">
                <div data-tour="summary"><SummaryPanel config={config} summary={summary.data} /></div>
                <Divider />
                <div data-tour="products"><ProductsPanel site={site} canEdit={canEdit} captureView={captureView} /></div>
              </Tabs.Panel>
              <Tabs.Panel value="ai" data-tour="ai">
                {canEdit && <div style={{ padding: '12px 12px 0' }}><AnalyseButton site={site} getViewBounds={viewBounds} onStarted={() => setTab('ai')} /></div>}
                {layers.some((l) => l.kind === 'analysis' && l.status === 'ready') && (
                  <LearnPanel slug={site.response.slug} canEdit={canEdit} drawing={!!addTo}
                    onDrawMissed={() => {
                      const target = layers.filter((l) => l.kind === 'analysis' && l.status === 'ready').sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0]
                      if (addTo) { setDrawMode('static'); return }
                      setDrawMode('polygon')
                      setAddTo(target.id)
                    }} />
                )}
                <AnalysisPanel analysis={analysis} active={focused?.id || null} onFocus={focusRefs} />
              </Tabs.Panel>
            </Tabs>
          )}
        </ScrollArea>
      </AppShell.Aside>
      <Modal opened={!!pending} onClose={cancelDrawn} title="New feature">
        {pending && <FeatureForm config={config} geometryType={pending.geometry.type} onSave={saveDrawn} onCancel={cancelDrawn} saveLabel="Add to map" />}
      </Modal>
    </AppShell>
  )
}
