import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type Combatant, type ConditionEntry, type Encounter, type Monster } from '../api/client'
import MonsterDetail from './MonsterDetail'

// D&D 2024 DMG: XP budget per character [Low, Moderate, High] by level.
const XP_BUDGET: Record<number, [number, number, number]> = {
  1: [50, 75, 100], 2: [100, 150, 200], 3: [150, 225, 400], 4: [250, 375, 500],
  5: [500, 750, 1100], 6: [600, 1000, 1400], 7: [750, 1300, 1700], 8: [1000, 1700, 2100],
  9: [1300, 2000, 2600], 10: [1600, 2300, 3100], 11: [1900, 2900, 4100], 12: [2200, 3700, 4700],
  13: [2600, 4200, 5400], 14: [2900, 4900, 6200], 15: [3300, 5400, 7800], 16: [3800, 6100, 9800],
  17: [4500, 7200, 11700], 18: [5000, 8700, 14200], 19: [5500, 10700, 17200], 20: [6400, 13200, 22000],
}

// XP value by numeric CR (Monster.cr).
const CR_XP: Record<string, number> = {
  '0': 10, '0.125': 25, '0.25': 50, '0.5': 100,
  '1': 200, '2': 450, '3': 700, '4': 1100, '5': 1800, '6': 2300, '7': 2900, '8': 3900,
  '9': 5000, '10': 5900, '11': 7200, '12': 8400, '13': 10000, '14': 11500, '15': 13000,
  '16': 15000, '17': 18000, '18': 20000, '19': 22000, '20': 25000, '21': 33000, '22': 41000,
  '23': 50000, '24': 62000, '25': 75000, '26': 90000, '27': 105000, '28': 120000,
  '29': 135000, '30': 155000,
}

// D&D 2024 (5.5e) conditions — short rules summaries shown in the picker.
const CONDITION_INFO: Record<string, string> = {
  blinded: "Can't see; auto-fail sight checks. Attacks against you have advantage, your attacks have disadvantage.",
  charmed: "Can't attack the charmer or target them with harmful effects. Charmer has advantage on social checks with you.",
  deafened: "Can't hear; auto-fail any check needing hearing.",
  frightened: "Disadvantage on checks & attacks while the source is in sight. Can't willingly move closer to it.",
  grappled: "Speed 0. Disadvantage on attacks except against the grappler. Ends if grappler is incapacitated.",
  incapacitated: "No actions, bonus actions, or reactions. Concentration broken. Can't speak.",
  invisible: "Unseen without special senses; heavily obscured for hiding. Attacks against you have disadvantage, yours have advantage.",
  paralyzed: "Incapacitated, can't move or speak. Auto-fail STR & DEX saves. Attacks vs you have advantage; hits within 5 ft are crits.",
  petrified: "Turned to solid substance. Incapacitated & unaware, weight ×10. Resistance to all damage; immune to poison & disease.",
  poisoned: 'Disadvantage on attack rolls and ability checks.',
  prone: 'Can only crawl. Disadvantage on attacks. Attacks within 5 ft have advantage, farther have disadvantage.',
  restrained: 'Speed 0. Attacks vs you have advantage, yours have disadvantage. Disadvantage on DEX saves.',
  stunned: 'Incapacitated, can\'t move, speech falters. Auto-fail STR & DEX saves. Attacks vs you have advantage.',
  unconscious: 'Incapacitated, prone, drop what you hold, unaware. Auto-fail STR & DEX saves. Attacks vs you have advantage; hits within 5 ft crit.',
  exhaustion: 'Cumulative 1–6. Each level: −2 to d20 tests and −5 ft speed. Level 6 is death.',
}
const CONDITIONS = Object.keys(CONDITION_INFO)

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
  const [detailId, setDetailId] = useState<number | null>(null)

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

  return (
    <section>
      <div className="row spread">
        <button className="link" onClick={onBack}>← Back</button>
        <h2>{enc.name}</h2>
        <span className="round-badge">Round {enc.round}</span>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="row controls">
        {started ? (
          <button
            className="danger"
            onClick={() => { if (confirm('End combat? Turn order resets; HP and conditions are kept.')) ctrl(() => api.encounters.end(enc.id)) }}
          >
            ⏹ End
          </button>
        ) : (
          <button onClick={() => ctrl(() => api.encounters.start(enc.id))}>▶ Start</button>
        )}
        <button disabled={!started} onClick={() => ctrl(() => api.encounters.prevTurn(enc.id))}>◀ Prev</button>
        <button disabled={!started} onClick={() => ctrl(() => api.encounters.nextTurn(enc.id))}>Next ▶</button>
      </div>

      <DifficultyPanel enc={enc} monsters={monsters} />

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
            onShowDetail={setDetailId}
          />
        ))}
      </ul>

      <AddCombatant encounterId={enc.id} monsters={monsters} onAdded={setEnc} onError={setError} />

      {detailId !== null && <MonsterDetail monsterId={detailId} onClose={() => setDetailId(null)} />}
    </section>
  )
}

// D&D 2024 encounter difficulty: sum monster XP (by CR) vs the party's XP budget.
function DifficultyPanel({ enc, monsters }: { enc: Encounter; monsters: Monster[] }) {
  const [size, setSize] = useState(() => localStorage.getItem('ik-party-size') ?? '4')
  const [level, setLevel] = useState(() => localStorage.getItem('ik-party-level') ?? '3')
  useEffect(() => { localStorage.setItem('ik-party-size', size) }, [size])
  useEffect(() => { localStorage.setItem('ik-party-level', level) }, [level])

  const byId = new Map(monsters.map((m) => [m.id, m]))
  let xp = 0
  let noCr = 0
  for (const c of enc.combatants) {
    if (c.is_pc) continue
    const cr = c.monster_id !== null ? byId.get(c.monster_id)?.cr : null
    const value = cr !== null && cr !== undefined ? CR_XP[String(cr)] : undefined
    if (value === undefined) noCr++
    else xp += value
  }

  const n = Math.max(1, parseInt(size, 10) || 1)
  const lvl = Math.min(20, Math.max(1, parseInt(level, 10) || 1))
  const [low, moderate, high] = XP_BUDGET[lvl]
  const [bLow, bMod, bHigh] = [low * n, moderate * n, high * n]
  const label =
    xp === 0 ? null : xp <= bLow ? 'Low' : xp <= bMod ? 'Moderate' : xp <= bHigh ? 'High' : 'Deadly'
  const cls = label === 'Low' ? 'ok' : label === 'Moderate' ? 'warn' : label ? 'crit' : ''

  return (
    <div className="row difficulty">
      <span className="muted">Party</span>
      <input
        type="number" min={1} value={size} title="Party size"
        onChange={(e) => setSize(e.target.value)} style={{ width: 56 }}
      />
      <span className="muted">× level</span>
      <input
        type="number" min={1} max={20} value={level} title="Party level"
        onChange={(e) => setLevel(e.target.value)} style={{ width: 56 }}
      />
      {label ? (
        <span className="diff-result">
          {xp} XP → <b className={`diff ${cls}`}>{label}</b>
          <span className="muted"> · budget: Low {bLow} / Moderate {bMod} / High {bHigh}</span>
          {noCr > 0 && <span className="muted"> · {noCr} without CR skipped</span>}
        </span>
      ) : (
        <span className="muted">no monsters with CR yet</span>
      )}
    </div>
  )
}

function CombatantRow({
  c, active, encounterId, onChange, onError, onShowDetail,
}: {
  c: Combatant
  active: boolean
  encounterId: number
  onChange: (e: Encounter) => void
  onError: (m: string) => void
  onShowDetail: (monsterId: number) => void
}) {
  const [delta, setDelta] = useState('')
  const [concDc, setConcDc] = useState<number | null>(null)

  async function patch(body: Partial<Combatant>) {
    try { onChange(await api.encounters.updateCombatant(encounterId, c.id, body)) }
    catch (e) { onError((e as Error).message) }
  }

  function applyHp(sign: number) {
    const n = parseInt(delta, 10)
    if (isNaN(n) || n <= 0) return
    setDelta('')
    if (sign < 0) {
      // damage eats temp HP first, remainder hits current HP
      const fromTemp = Math.min(c.temp_hp, n)
      const rest = n - fromTemp
      patch({ temp_hp: c.temp_hp - fromTemp, current_hp: Math.max(0, c.current_hp - rest) })
      if (c.concentrating) setConcDc(Math.max(10, Math.floor(n / 2)))
    } else {
      patch({ current_hp: Math.min(c.max_hp, c.current_hp + n) })
    }
  }

  function setTempHp() {
    const n = parseInt(delta, 10)
    if (isNaN(n) || n < 0) return
    setDelta('')
    patch({ temp_hp: n })
  }

  function toggleCond(name: string) {
    const next = c.conditions.some((x) => x.name === name)
      ? c.conditions.filter((x) => x.name !== name)
      : [...c.conditions, { name, rounds: null }]
    patch({ conditions: next })
  }

  function setCondRounds(name: string, rounds: number | null) {
    patch({ conditions: c.conditions.map((x) => (x.name === name ? { ...x, rounds } : x)) })
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
        {c.monster_id !== null ? (
          <button className="link-strong name-btn" onClick={() => onShowDetail(c.monster_id!)}>
            {c.name}
          </button>
        ) : (
          <strong>{c.name}</strong>
        )}
        <span className="tags">
          {c.is_pc ? <span className="tag pc">PC</span> : <span className="tag npc">NPC</span>}
          <span className="tag">AC {c.armor_class}</span>
          <button
            className={`tag conc ${c.concentrating ? 'on' : ''}`}
            title="Concentration — toggle; taking damage shows the CON save DC"
            onClick={() => { setConcDc(null); patch({ concentrating: !c.concentrating }) }}
          >
            ✦ conc
          </button>
        </span>
        {c.legendary_actions_max > 0 && (
          <span className="la" title="Legendary actions — click orb to spend/restore; refills at the start of its turn">
            <span className="la-label">LA</span>
            {Array.from({ length: c.legendary_actions_max }, (_, i) => (
              <button
                key={i}
                className={`la-orb ${i < c.legendary_actions_remaining ? 'full' : ''}`}
                onClick={() => patch({
                  legendary_actions_remaining: i < c.legendary_actions_remaining ? i : i + 1,
                })}
              >
                {i < c.legendary_actions_remaining ? '●' : '○'}
              </button>
            ))}
          </span>
        )}
        {concDc !== null && (
          <button className="conc-alert" onClick={() => setConcDc(null)}>
            ✦ Concentration check — CON save DC {concDc} ✕
          </button>
        )}
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
          <button className="temp" title="Set temp HP to this value" onClick={setTempHp}>Temp</button>
        </div>
      </div>

      <div className="conds">
        {c.conditions.map((cd) => (
          <button
            key={cd.name}
            className="chip"
            title={CONDITION_INFO[cd.name] ?? cd.name}
            onClick={() => toggleCond(cd.name)}
          >
            {cd.name}{cd.rounds !== null ? ` ·${cd.rounds}` : ''} ✕
          </button>
        ))}
        <ConditionMenu selected={c.conditions} onToggle={toggleCond} onSetRounds={setCondRounds} />
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

// Click-to-open picker (works on touch): toggle any number of conditions,
// each row shows its rules text; active ones get a rounds input (empty = until removed).
// Closes on outside click / Escape.
function ConditionMenu({
  selected, onToggle, onSetRounds,
}: {
  selected: ConditionEntry[]
  onToggle: (name: string) => void
  onSetRounds: (name: string, rounds: number | null) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className={`cond-menu ${open ? 'open' : ''}`} ref={ref}>
      <button type="button" className="cond-add" onClick={() => setOpen((o) => !o)}>＋ Status</button>
      <div className="cond-panel">
        {CONDITIONS.map((name) => {
          const entry = selected.find((x) => x.name === name)
          const on = entry !== undefined
          return (
            <div key={name} className={`cond-opt ${on ? 'on' : ''}`}>
              <button type="button" className="cond-toggle" onClick={() => onToggle(name)}>
                <span className="cond-check">{on ? '☑' : '☐'}</span>
                <span className="cond-body">
                  <span className="cond-name">{name}</span>
                  <span className="cond-desc">{CONDITION_INFO[name]}</span>
                </span>
              </button>
              {on && (
                <input
                  type="number"
                  min={1}
                  className="cond-rounds"
                  placeholder="∞"
                  title="Rounds remaining (empty = until removed); ticks down at end of round"
                  value={entry.rounds ?? ''}
                  onChange={(e) =>
                    onSetRounds(name, e.target.value === '' ? null : Math.max(1, Number(e.target.value)))
                  }
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
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
  const [count, setCount] = useState('1')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const initiative = init === '' ? null : Number(init)
      if (mode === 'monster') {
        if (monsterId === '') return
        const n = Math.min(20, Math.max(1, parseInt(count, 10) || 1))
        onAdded(await api.encounters.addCombatant(encounterId, { monster_id: Number(monsterId), initiative, count: n }))
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
      setName(''); setHp(''); setAc(''); setInit(''); setMonsterId(''); setCount('1')
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
          <>
            <select value={monsterId} onChange={(e) => setMonsterId(e.target.value === '' ? '' : Number(e.target.value))}>
              <option value="">— pick imported monster —</option>
              {monsters.map((m) => (
                <option key={m.id} value={m.id}>{m.name} (HP {m.hit_points}, AC {m.armor_class})</option>
              ))}
            </select>
            <input
              type="number" min={1} max={20} value={count} title="How many copies to add"
              onChange={(e) => setCount(e.target.value)} style={{ width: 60 }}
            />
            <span className="muted">×</span>
          </>
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
