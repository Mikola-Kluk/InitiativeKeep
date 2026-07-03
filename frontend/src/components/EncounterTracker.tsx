import { useCallback, useEffect, useState } from 'react'
import { api, type Combatant, type Encounter, type Monster } from '../api/client'

const CONDITIONS = [
  'blinded', 'charmed', 'deafened', 'frightened', 'grappled', 'incapacitated',
  'invisible', 'paralyzed', 'petrified', 'poisoned', 'prone', 'restrained',
  'stunned', 'unconscious', 'exhaustion',
]

function d20() {
  return Math.floor(Math.random() * 20) + 1
}

export default function EncounterTracker({
  encounterId,
  onBack,
}: {
  encounterId: number
  onBack: () => void
}) {
  const [enc, setEnc] = useState<Encounter | null>(null)
  const [monsters, setMonsters] = useState<Monster[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.encounters.get(encounterId).then(setEnc).catch((e) => setError(e.message))
  }, [encounterId])

  useEffect(load, [load])
  useEffect(() => { api.monsters.list().then(setMonsters).catch(() => {}) }, [])

  if (!enc) return <p className="muted">Loading… {error && <span className="error">{error}</span>}</p>

  const started = enc.current_turn_index >= 0
  const activeId = started ? enc.combatants[enc.current_turn_index]?.id : undefined

  async function ctrl(fn: () => Promise<Encounter>) {
    try { setEnc(await fn()) } catch (e) { setError((e as Error).message) }
  }

  async function rollAll() {
    if (!enc) return
    for (const c of enc.combatants) {
      if (c.initiative === null) {
        await api.encounters.updateCombatant(enc.id, c.id, { initiative: d20() + c.dex_modifier })
      }
    }
    load()
  }

  return (
    <section>
      <div className="row spread">
        <button className="link" onClick={onBack}>← Back</button>
        <h2>{enc.name}</h2>
        <span className="round-badge">Round {enc.round}</span>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="row controls">
        <button onClick={() => ctrl(() => api.encounters.start(enc.id))}>▶ Start</button>
        <button disabled={!started} onClick={() => ctrl(() => api.encounters.prevTurn(enc.id))}>◀ Prev</button>
        <button disabled={!started} onClick={() => ctrl(() => api.encounters.nextTurn(enc.id))}>Next ▶</button>
        <button className="ghost" onClick={rollAll}>🎲 Roll unrolled initiative</button>
      </div>

      {enc.combatants.length === 0 && <p className="muted">No combatants — add some below.</p>}

      <ul className="tracker">
        {enc.combatants.map((c) => (
          <CombatantRow
            key={c.id}
            c={c}
            active={c.id === activeId}
            onChange={setEnc}
            encounterId={enc.id}
            onError={setError}
          />
        ))}
      </ul>

      <AddCombatant encounterId={enc.id} monsters={monsters} onAdded={setEnc} onError={setError} />
    </section>
  )
}

function CombatantRow({
  c, active, encounterId, onChange, onError,
}: {
  c: Combatant
  active: boolean
  encounterId: number
  onChange: (e: Encounter) => void
  onError: (m: string) => void
}) {
  const [delta, setDelta] = useState('')
  const [cond, setCond] = useState('')

  async function patch(body: Partial<Combatant>) {
    try { onChange(await api.encounters.updateCombatant(encounterId, c.id, body)) }
    catch (e) { onError((e as Error).message) }
  }

  function applyHp(sign: number) {
    const n = parseInt(delta, 10)
    if (isNaN(n)) return
    const next = Math.max(0, Math.min(c.max_hp, c.current_hp + sign * n))
    setDelta('')
    patch({ current_hp: next })
  }

  function addCond() {
    const v = cond.trim().toLowerCase()
    if (!v || c.conditions.includes(v)) { setCond(''); return }
    setCond('')
    patch({ conditions: [...c.conditions, v] })
  }

  const hpPct = c.max_hp > 0 ? (c.current_hp / c.max_hp) * 100 : 0
  const hpColor = hpPct > 50 ? 'ok' : hpPct > 25 ? 'warn' : 'crit'

  return (
    <li className={`combatant ${active ? 'active' : ''} ${c.current_hp === 0 ? 'down' : ''}`}>
      <div className="init">
        <input
          className="init-input"
          type="number"
          value={c.initiative ?? ''}
          placeholder="–"
          onChange={(e) => patch({ initiative: e.target.value === '' ? null : Number(e.target.value) })}
        />
      </div>

      <div className="who">
        <strong>{c.name}</strong>
        <span className="tags">
          {c.is_pc ? <span className="tag pc">PC</span> : <span className="tag npc">NPC</span>}
          <span className="tag">AC {c.armor_class}</span>
        </span>
      </div>

      <div className="hp">
        <div className="hp-bar"><div className={`hp-fill ${hpColor}`} style={{ width: `${hpPct}%` }} /></div>
        <span className="hp-num">{c.current_hp}/{c.max_hp}{c.temp_hp ? ` (+${c.temp_hp})` : ''}</span>
        <div className="hp-ctrl">
          <input
            type="number"
            value={delta}
            placeholder="0"
            onChange={(e) => setDelta(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') applyHp(-1) }}
          />
          <button className="danger" onClick={() => applyHp(-1)}>Dmg</button>
          <button className="heal" onClick={() => applyHp(1)}>Heal</button>
        </div>
      </div>

      <div className="conds">
        {c.conditions.map((cd) => (
          <button key={cd} className="chip" onClick={() => patch({ conditions: c.conditions.filter((x) => x !== cd) })}>
            {cd} ✕
          </button>
        ))}
        <input
          list="conditions"
          value={cond}
          placeholder="+ condition"
          onChange={(e) => setCond(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') addCond() }}
        />
        <datalist id="conditions">
          {CONDITIONS.map((x) => <option key={x} value={x} />)}
        </datalist>
      </div>

      <button
        className="danger remove"
        onClick={async () => onChange(await api.encounters.removeCombatant(encounterId, c.id))}
      >
        ✕
      </button>
    </li>
  )
}

function AddCombatant({
  encounterId, monsters, onAdded, onError,
}: {
  encounterId: number
  monsters: Monster[]
  onAdded: (e: Encounter) => void
  onError: (m: string) => void
}) {
  const [mode, setMode] = useState<'pc' | 'monster'>('monster')
  const [name, setName] = useState('')
  const [hp, setHp] = useState('')
  const [ac, setAc] = useState('')
  const [init, setInit] = useState('')
  const [monsterId, setMonsterId] = useState<number | ''>('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const initiative = init === '' ? null : Number(init)
      if (mode === 'monster') {
        if (monsterId === '') return
        onAdded(await api.encounters.addCombatant(encounterId, { monster_id: Number(monsterId), initiative }))
      } else {
        if (!name.trim()) return
        onAdded(await api.encounters.addCombatant(encounterId, {
          name: name.trim(),
          is_pc: true,
          initiative,
          max_hp: hp ? Number(hp) : 1,
          armor_class: ac ? Number(ac) : 10,
        }))
      }
      setName(''); setHp(''); setAc(''); setInit(''); setMonsterId('')
    } catch (err) {
      onError((err as Error).message)
    }
  }

  return (
    <form onSubmit={submit} className="add-combatant">
      <div className="row">
        <label><input type="radio" checked={mode === 'monster'} onChange={() => setMode('monster')} /> Monster</label>
        <label><input type="radio" checked={mode === 'pc'} onChange={() => setMode('pc')} /> PC</label>
      </div>
      <div className="row">
        {mode === 'monster' ? (
          <select value={monsterId} onChange={(e) => setMonsterId(e.target.value === '' ? '' : Number(e.target.value))}>
            <option value="">— pick imported monster —</option>
            {monsters.map((m) => (
              <option key={m.id} value={m.id}>{m.name} (HP {m.hit_points}, AC {m.armor_class})</option>
            ))}
          </select>
        ) : (
          <>
            <input placeholder="PC name" value={name} onChange={(e) => setName(e.target.value)} />
            <input type="number" placeholder="HP" value={hp} onChange={(e) => setHp(e.target.value)} style={{ width: 70 }} />
            <input type="number" placeholder="AC" value={ac} onChange={(e) => setAc(e.target.value)} style={{ width: 70 }} />
          </>
        )}
        <input type="number" placeholder="init" value={init} onChange={(e) => setInit(e.target.value)} style={{ width: 70 }} />
        <button type="submit">+ Add</button>
      </div>
    </form>
  )
}
