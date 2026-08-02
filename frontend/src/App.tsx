import { Toaster } from 'sonner'
import { AppRouter } from '@/routes'
import { SettingsProvider } from '@/lib/settings-provider'
import { useToastDuration } from '@/lib/settings'

function App() {
  return (
    <SettingsProvider>
      <AppRouter />
      <AppToaster />
    </SettingsProvider>
  )
}

function AppToaster() {
  const duration = useToastDuration()
  return <Toaster position="top-center" richColors closeButton duration={duration || Infinity} />
}

export default App
