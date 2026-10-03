import { useEffect, useState } from 'react'
import { api, type Encounter, type Monster } from '../api/client'
import { EncounterSchemaTable, MonsterIdTable, exampleEncounterJson } from './EncounterSchema'

export default function EncounterList({ onOpen }: { onOpen: (id: number) => void }) {
  const [encounters, setEncounters] = useState<Encounter[]>([])
  const [name, setName] = useState('')
  const [pasting, setPasting] = useState(false)
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
          <button
            type="button"
            className="ghost"
            onClick={() => setPasting(true)}
            title="Prepare a fight from JSON: name plus enemies from your library"
          >📋 Paste JSON</button>
        </div>
      </form>

      {pasting && (
        <PrepareJson
          onClose={() => setPasting(false)}
          onSaved={(enc) => { setPasting(false); load(); onOpen(enc.id) }}
        />
      )}

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

function PrepareJson({ onClose, onSaved }: { onClose: () => void; onSaved: (enc: Encounter) => void }) {
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [help, setHelp] = useState<'fields' | 'ids' | 'example' | null>(null)
  const [monsters, setMonsters] = useState<Monster[]>([])

  // library ids for the reference tab and a paste-ready example
  useEffect(() => {
    api.monsters.list().then(setMonsters).catch(() => {})
  }, [])

  const example = exampleEncounterJson(monsters)

  async function save() {
    setError(null)
    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch {
      setError('Invalid JSON. Check for a stray comma or a missing quote.')
      return
    }
    setBusy(true)
    try {
      onSaved(await api.encounters.prepare(parsed))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2>
          Prepare a fight from JSON{' '}
          <button
            className="ghost help-btn"
            title="Show the JSON format"
            aria-label="Show the JSON format"
            onClick={() => setHelp((h) => (h ? null : 'fields'))}
          >?</button>
        </h2>
        <p className="muted">
          Paste an encounter with its enemies. It opens in the tracker, not started, so you can
          add the players before rolling initiative.
        </p>
        {help && (
          <div className="json-help">
            <div className="row">
              <button className={help === 'fields' ? 'active' : ''} onClick={() => setHelp('fields')}>Fields</button>
              <button className={help === 'ids' ? 'active' : ''} onClick={() => setHelp('ids')}>Library</button>
              <button className={help === 'example' ? 'active' : ''} onClick={() => setHelp('example')}>Example</button>
            </div>
            {help === 'fields' && <EncounterSchemaTable />}
            {help === 'ids' && <MonsterIdTable monsters={monsters} />}
            {help === 'example' && (
              <>
                <p className="muted">
                  Three of one monster, one more with a nick, and a renamed one:
                  <button className="link-strong" onClick={() => { setText(example); setHelp(null) }}>Use this</button>
                </p>
                <pre className="json-example"><code>{example}</code></pre>
              </>
            )}
          </div>
        )}
        <textarea
          rows={14}
          spellCheck={false}
          placeholder='{ "name": "Ambush", "enemies": [ { "monster": "Goblin", "count": 3 } ] }'
          value={text}
          onChange={(e) => setText(e.target.value)}
          style={{ width: '100%', fontFamily: 'monospace' }}
        />
        {error && <p className="error">{error}</p>}
        <div className="row">
          <button className="run" disabled={busy || !text.trim()} onClick={save}>
            {busy ? 'Preparing…' : 'Prepare encounter'}
          </button>
          <button className="ghost" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  )
}
