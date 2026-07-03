import { useEffect, useState } from 'react'
import { api, type Encounter } from '../api/client'

export default function EncounterList({ onOpen }: { onOpen: (id: number) => void }) {
  const [encounters, setEncounters] = useState<Encounter[]>([])
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  function load() {
    api.encounters.list().then(setEncounters).catch((e) => setError(e.message))
  }

  useEffect(load, [])

  async function create(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    try {
      const enc = await api.encounters.create(name.trim())
      setName('')
      load()
      onOpen(enc.id)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function remove(id: number) {
    if (!confirm('Delete this encounter?')) return
    await api.encounters.remove(id)
    load()
  }

  return (
    <section>
      <h2>Encounters</h2>
      {error && <p className="error">{error}</p>}

      <form onSubmit={create} className="row">
        <input
          placeholder="New encounter name…"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button type="submit">+ Create</button>
      </form>

      {encounters.length === 0 && <p className="muted">No encounters yet.</p>}
      <ul className="card-list">
        {encounters.map((enc) => (
          <li key={enc.id} className="card">
            <button className="link-strong" onClick={() => onOpen(enc.id)}>
              {enc.name}
            </button>
            <span className="muted">
              {enc.combatants.length} combatant{enc.combatants.length !== 1 ? 's' : ''} · round {enc.round}
            </span>
            <button className="danger" onClick={() => remove(enc.id)}>✕</button>
          </li>
        ))}
      </ul>
    </section>
  )
}
