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
      <header className="page-head">
        <h2>Encounters</h2>
        <p className="page-sub">Every fight you have set up. Open one to roll initiative.</p>
      </header>

      {error && <p className="error">{error}</p>}

      <form onSubmit={create} className="new-enc">
        <label className="new-enc-label" htmlFor="new-enc-name">Start a new encounter</label>
        <div className="new-enc-row">
          <input
            id="new-enc-name"
            placeholder="Ambush at the ford…"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button type="submit" className="run" disabled={!name.trim()}>Create</button>
        </div>
      </form>

      {encounters.length === 0 ? (
        <div className="empty">
          <span className="empty-mark">❖</span>
          <p className="empty-title">No encounters yet</p>
          <p className="muted">Name one above and it opens straight into the tracker.</p>
        </div>
      ) : (
        <ul className="card-list">
          {encounters.map((enc) => {
            const started = enc.current_turn_index >= 0
            const pcs = enc.combatants.filter((c) => c.is_pc).length
            const foes = enc.combatants.length - pcs
            return (
              <li key={enc.id} className={`card enc-card ${started ? 'live' : ''}`}>
                <span className="enc-seal" aria-hidden="true">
                  {started ? <b>{enc.round}</b> : <b className="enc-seal-icon">⚔</b>}
                  <small>{started ? 'round' : 'ready'}</small>
                </span>

                <span className="enc-body">
                  <button className="link-strong enc-name" onClick={() => onOpen(enc.id)}>
                    {enc.name}
                  </button>
                  <span className="enc-meta">
                    {enc.combatants.length === 0 ? (
                      <span className="tag">empty</span>
                    ) : (
                      <>
                        {pcs > 0 && <span className="tag pc">{pcs} player{pcs !== 1 ? 's' : ''}</span>}
                        {foes > 0 && <span className="tag npc">{foes} monster{foes !== 1 ? 's' : ''}</span>}
                      </>
                    )}
                    <span className={`tag ${started ? 'live' : ''}`}>
                      {started ? 'in progress' : 'not started'}
                    </span>
                  </span>
                </span>

                <button className="enc-go" onClick={() => onOpen(enc.id)}>Open →</button>
                <button
                  className="danger enc-del"
                  title={`Delete ${enc.name}`}
                  aria-label={`Delete ${enc.name}`}
                  onClick={() => remove(enc.id)}
                >
                  ✕
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
