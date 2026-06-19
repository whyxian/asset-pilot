import { AppRouter } from '@/routes'
import { SettingsProvider } from '@/lib/settings'

function App() {
  return (
    <SettingsProvider>
      <AppRouter />
    </SettingsProvider>
  )
}

export default App
