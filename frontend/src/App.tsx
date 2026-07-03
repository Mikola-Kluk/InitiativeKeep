import { useState } from 'react'
import './App.css'
import EncounterList from './components/EncounterList'
import EncounterTracker from './components/EncounterTracker'
import MonsterBrowser from './components/MonsterBrowser'

type Tab = 'encounters' | 'monsters'

export default function App() {
  const [tab, setTab] = useState<Tab>('encounters')
  const [activeEncounter, setActiveEncounter] = useState<number | null>(null)

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
