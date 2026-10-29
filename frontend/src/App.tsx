import { Center, Loader, Text } from '@mantine/core'
import { Route, Routes } from 'react-router'
import { useConfig } from './hooks'
import Home from './routes/Home'
import MapPrint from './routes/MapPrint'
import ResponsePage from './routes/ResponsePage'
import SitePage from './routes/SitePage'

export default function App() {
  const config = useConfig()
  if (config.error) return <Center h="100vh"><Text c="red">Can't reach the API: {String(config.error)}</Text></Center>
  if (!config.data) return <Center h="100vh"><Loader /></Center>
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/r/:response" element={<ResponsePage />} />
      <Route path="/r/:response/:site" element={<SitePage />} />
      <Route path="/print/map/:id" element={<MapPrint />} />
    </Routes>
  )
}
