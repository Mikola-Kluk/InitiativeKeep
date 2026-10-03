import { useState } from 'react'
import './App.css'
import EncounterList from './components/EncounterList'
import EncounterTracker from './components/EncounterTracker'
import MonsterBrowser from './components/MonsterBrowser'
import { useTheme } from './useTheme'

type Tab = 'encounters' | 'monsters'

export default function App() {
  const [tab, setTab] = useState<Tab>('encounters')
  const [activeEncounter, setActiveEncounter] = useState<number | null>(null)
  const [theme, toggleTheme] = useTheme()

  return (
    <div className="app">
      <header className="topbar">
        <h1>⚔️ InitiativeKeep</h1>
        <nav>
          <button
            className={tab === 'encounters' ? 'active' : ''}
            onClick={() => { setTab('encounters'); setActiveEncounter(null) }}
          >
            Encounters
          </button>
          <button
            className={tab === 'monsters' ? 'active' : ''}
            onClick={() => { setTab('monsters'); setActiveEncounter(null) }}
          >
            Monsters
          </button>
          <button
            className="ghost theme-btn"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? '☀' : '☾'}
          </button>
        </nav>
      </header>

      <main>
        {tab === 'encounters' && activeEncounter === null && (
          <EncounterList onOpen={setActiveEncounter} />
        )}
        {tab === 'encounters' && activeEncounter !== null && (
          <EncounterTracker
            encounterId={activeEncounter}
            onBack={() => setActiveEncounter(null)}
          />
        )}
        {tab === 'monsters' && <MonsterBrowser />}
      </main>
    </div>
  )
}
