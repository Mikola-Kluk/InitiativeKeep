import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type Character, type Combatant, type ConditionEntry, type Encounter, type Monster } from '../api/client'
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

// Classic encounter multiplier (2014 DMG): more monsters swing harder than raw XP.
function encounterMultiplier(monsterCount: number): number {
  if (monsterCount <= 1) return 1
  if (monsterCount === 2) return 1.5
  if (monsterCount <= 6) return 2
  if (monsterCount <= 10) return 2.5
  if (monsterCount <= 14) return 3
  return 4
}

type XpAward = { total: number; perPlayer: number; defeated: number; players: number; noCr: number }

// XP earned when combat ends: only monsters that are actually down (0 HP) count —
// survivors that fled or were left standing award nothing. Split evenly per PC.
function defeatedXp(enc: Encounter, monsters: Monster[]): XpAward {
  const byId = new Map(monsters.map((m) => [m.id, m]))
  let total = 0
  let defeated = 0
  let noCr = 0
  for (const c of enc.combatants) {
    if (c.is_pc || c.current_hp !== 0) continue
    defeated++
    const cr = c.monster_id !== null ? byId.get(c.monster_id)?.cr : null
    const value = cr !== null && cr !== undefined ? CR_XP[String(cr)] : undefined
    if (value === undefined) noCr++
    else total += value
  }
  const players = enc.combatants.filter((c) => c.is_pc).length
  const perPlayer = players > 0 ? Math.round(total / players) : total
  return { total, perPlayer, defeated, players, noCr }
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
  const [award, setAward] = useState<XpAward | null>(null)

  const load = useCallback(() => {
    api.encounters.get(encounterId).then(setEnc).catch((e) => setError(e.message))
  }, [encounterId])

  useEffect(load, [load])
  useEffect(() => { api.monsters.list().then(setMonsters).catch(() => {}) }, [])

  // The statblock docks over the right edge of the viewport. Flag the body so
  // the page can give up that strip instead of hiding rows underneath it.
  useEffect(() => {
    document.body.classList.toggle('panel-open', detailId !== null)
    return () => document.body.classList.remove('panel-open')
  }, [detailId])

  const undoLabel = enc?.undo_label ?? null
  const undo = useCallback(async () => {
    try { setEnc(await api.encounters.undo(encounterId)) } catch (e) { setError((e as Error).message) }
  }, [encounterId])

  // Ctrl+Z / Cmd+Z undoes the last combat change — but not while typing in a
  // field, where it should stay the browser's own text undo.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey) || e.shiftKey || e.key.toLowerCase() !== 'z') return
      if ((e.target as HTMLElement).closest('input, textarea, select, [contenteditable]')) return
      if (!undoLabel) return
      e.preventDefault()
      undo()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [undo, undoLabel])

  if (!enc) return <p className="muted">Loading… {error && <span className="error">{error}</span>}</p>

  const started = enc.current_turn_index >= 0
  const activeId = started ? enc.combatants[enc.current_turn_index]?.id : undefined

  // waves: whoever is at or below the current wave fights, the rest wait in reserve
  const fighting = enc.combatants.filter((c) => c.wave <= enc.current_wave)
  const reserve = enc.combatants.filter((c) => c.wave > enc.current_wave)
  const waitingWaves = [...new Set(reserve.map((c) => c.wave))].sort((a, b) => a - b)
  const nextWave = waitingWaves[0]
  const hasWaves = enc.current_wave > 0 || reserve.length > 0

  function startNextWave() {
    const n = reserve.filter((c) => c.wave === nextWave).length
    const who = `${n} combatant${n === 1 ? '' : 's'}`
    if (!confirm(`Start wave ${nextWave}? ${who} will roll initiative and join the fight.`)) return
    ctrl(() => api.encounters.nextWave(enc!.id))
  }

  const row = (c: Combatant, inReserve: boolean) => (
    <CombatantRow
      key={c.id}
      c={c}
      monster={c.monster_id !== null ? monsters.find((m) => m.id === c.monster_id) : undefined}
      round={enc.round}
      active={c.id === activeId}
      reserve={inReserve}
      // moving between waves is safe while the turn order does not depend on it
      waveEdit={hasWaves && (inReserve || !started) ? enc.current_wave : null}
      onChange={setEnc}
      encounterId={enc.id}
      onError={setError}
      onShowDetail={setDetailId}
    />
  )

  async function ctrl(fn: () => Promise<Encounter>) {
    try { setEnc(await fn()) } catch (e) { setError((e as Error).message) }
  }

  async function endCombat() {
    // tally XP from downed monsters before the state resets
    setAward(defeatedXp(enc!, monsters))
    await ctrl(() => api.encounters.end(enc!.id))
  }

  return (
    <section>
      <div className="row spread">
        <button className="link" onClick={onBack}>← Back</button>
        <h2>{enc.name}</h2>
        {hasWaves && started && <span className="tag wave-now" title="Wave currently fighting">Wave {enc.current_wave}</span>}
        <span className="round-badge" title={`Round ${enc.round}`}>
          <small>Round</small>
          <b>{enc.round}</b>
        </span>
      </div>

      {error && <p className="error">{error}</p>}

      {award && (
        <div className="xp-award">
          <span className="xp-title">🏆 Combat over</span>
          {award.defeated === 0 ? (
            <span>No monsters were defeated — no XP.</span>
          ) : (
            <span>
              Defeated {award.defeated} · <b>{award.total} XP</b> total →{' '}
              <b className="xp-per">{award.perPlayer} XP</b> per player
              {award.players > 0 ? <span className="muted"> ({award.players} {award.players === 1 ? 'player' : 'players'})</span> : <span className="muted"> (no PCs — showing total)</span>}
              {award.noCr > 0 && <span className="muted"> · {award.noCr} without CR skipped</span>}
            </span>
          )}
          <button className="xp-close" onClick={() => setAward(null)}>✕</button>
        </div>
      )}

      <div className="row controls">
        {started ? (
          <>
            <button disabled={!started} onClick={() => ctrl(() => api.encounters.prevTurn(enc.id))}>◀ Prev</button>
            <button className="run" disabled={!started} onClick={() => ctrl(() => api.encounters.nextTurn(enc.id))}>Next ▶</button>
            <button
              className="danger"
              onClick={() => { if (confirm('End combat? Turn order resets; HP and conditions are kept.')) endCombat() }}
            >
              ⏹ End
            </button>
            {nextWave !== undefined && (
              <button title="Bring the next waiting wave into the fight" onClick={startNextWave}>
                ⚑ Start wave {nextWave}
              </button>
            )}
          </>
        ) : (
          <button className="run" onClick={() => ctrl(() => api.encounters.start(enc.id))}>⚔ Start fight</button>
        )}
        <button
          className="ghost undo-btn"
          disabled={!undoLabel}
          title={undoLabel ? `Undo: ${undoLabel} (Ctrl+Z)` : 'Nothing to undo'}
          onClick={undo}
        >
          ↶ Undo{undoLabel && <span className="undo-label">{undoLabel}</span>}
        </button>
      </div>

      {!started && <p className="muted prep-hint">Prep phase — add combatants, then “Start fight” rolls initiative for everyone.</p>}

      <DifficultyPanel enc={enc} monsters={monsters} />

      {enc.combatants.length === 0 && <p className="muted">No combatants — add some below.</p>}

      <ul className="tracker">{fighting.map((c) => row(c, false))}</ul>

      {waitingWaves.map((w) => {
        const members = reserve.filter((c) => c.wave === w)
        return (
          <section key={w} className="wave">
            <h3 className="wave-head">
              Wave {w}
              <span className="muted"> · waiting · {members.length} combatant{members.length === 1 ? '' : 's'}</span>
            </h3>
            <ul className="tracker">{members.map((c) => row(c, true))}</ul>
          </section>
        )
      })}

      <AddCombatant encounterId={enc.id} currentWave={enc.current_wave} monsters={monsters} onAdded={setEnc} onError={setError} />

      {detailId !== null && <MonsterDetail monsterId={detailId} variant="panel" onClose={() => setDetailId(null)} />}
    </section>
  )
}

// Encounter difficulty: monster XP (by CR) × count multiplier vs the party budget.
// Party is derived from PC combatants that have a level; falls back to manual entry.
function DifficultyPanel({ enc, monsters }: { enc: Encounter; monsters: Monster[] }) {
  const [size, setSize] = useState(() => localStorage.getItem('ik-party-size') ?? '4')
  const [manualLevel, setManualLevel] = useState(() => localStorage.getItem('ik-party-level') ?? '3')
  useEffect(() => { localStorage.setItem('ik-party-size', size) }, [size])
  useEffect(() => { localStorage.setItem('ik-party-level', manualLevel) }, [manualLevel])

  const byId = new Map(monsters.map((m) => [m.id, m]))
  let rawXp = 0
  let monsterCount = 0
  let noCr = 0
  for (const c of enc.combatants) {
    if (c.is_pc) continue
    monsterCount++
    const cr = c.monster_id !== null ? byId.get(c.monster_id)?.cr : null
    const value = cr !== null && cr !== undefined ? CR_XP[String(cr)] : undefined
    if (value === undefined) noCr++
    else rawXp += value
  }

  // party budget: from PCs' levels if any carry one, else the manual size × level
  const pcLevels = enc.combatants.filter((c) => c.is_pc && c.level != null).map((c) => c.level as number)
  const auto = pcLevels.length > 0
  const levels = auto
    ? pcLevels
    : Array.from({ length: Math.max(1, parseInt(size, 10) || 1) }, () => Math.min(20, Math.max(1, parseInt(manualLevel, 10) || 1)))
  const budget = levels.reduce(
    (acc, lvl) => { const [l, m, h] = XP_BUDGET[Math.min(20, Math.max(1, lvl))]; return [acc[0] + l, acc[1] + m, acc[2] + h] as [number, number, number] },
    [0, 0, 0] as [number, number, number],
  )
  const [bLow, bMod, bHigh] = budget

  const mult = encounterMultiplier(monsterCount)
  const adjXp = Math.round(rawXp * mult)
  const label =
    adjXp === 0 ? null : adjXp <= bLow ? 'Low' : adjXp <= bMod ? 'Moderate' : adjXp <= bHigh ? 'High' : 'Deadly'
  const cls = label === 'Low' ? 'ok' : label === 'Moderate' ? 'warn' : label ? 'crit' : ''

  return (
    <div className="row difficulty">
      {auto ? (
        <span className="muted" title="Budget taken from the levels of the PCs in this encounter">
          Party: {pcLevels.length} PC (levels {pcLevels.join(', ')})
        </span>
      ) : (
        <>
          <span className="muted">Party</span>
          <input type="number" min={1} value={size} title="Party size" onChange={(e) => setSize(e.target.value)} style={{ width: 52 }} />
          <span className="muted">× level</span>
          <input type="number" min={1} max={20} value={manualLevel} title="Party level" onChange={(e) => setManualLevel(e.target.value)} style={{ width: 52 }} />
          <span className="muted" title="Add a PC with a level to compute this automatically">(no PC with a level)</span>
        </>
      )}
      {label ? (
        <span className="diff-result">
          <b className={`diff ${cls}`}>{label}</b>{' '}
          {monsterCount > 1
            ? <>{rawXp} XP × {mult} ({monsterCount} monsters) = <b>{adjXp} XP</b></>
            : <>{adjXp} XP</>}
          <span className="muted"> · budget: {bLow} / {bMod} / {bHigh}</span>
          {noCr > 0 && <span className="muted"> · {noCr} without CR skipped</span>}
        </span>
      ) : (
        <span className="muted">no monsters with CR yet</span>
      )}
    </div>
  )
}

/** The DM's own tag beside a monster's name ("elf", "Skarr") — click to edit in place. */
function NickTag({ nick, name, onSave }: { nick: string | null; name: string; onSave: (nick: string | null) => void }) {
  const [draft, setDraft] = useState<string | null>(null)  // null = not editing

  function commit() {
    if (draft === null) return
    const next = draft.trim() || null
    setDraft(null)
    if (next !== nick) onSave(next)
  }

  if (draft !== null) {
    return (
      <input
        className="nick-input"
        autoFocus
        maxLength={100}
        placeholder="elf, Skarr…"
        aria-label={`Nick for ${name}`}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commit()
          if (e.key === 'Escape') setDraft(null)
        }}
      />
    )
  }
  return (
    <button
      className={`nick ${nick ? 'set' : ''}`}
      title={nick ? 'Edit nick' : 'Add a nick to tell this one apart (race, name, a mark)'}
      aria-label={nick ? `Nick for ${name}: ${nick}. Edit` : `Add a nick for ${name}`}
      onClick={() => setDraft(nick ?? '')}
    >
      {nick ?? '+ nick'}
    </button>
  )
}

type RechargeAbility = { name: string; min: number | null }  // min 5 = "Recharge 5–6"; null = per rest

const RECHARGE_ROLL = /\(\s*recharge\s+(\d)(?:\s*[–—-]\s*6)?\s*\)/i
const RECHARGE_REST = /\(\s*recharges?\s+after\s+a\s+(?:short\s+or\s+)?long\s+rest\s*\)/i

/** Abilities marked "(Recharge 5–6)" / "(Recharge 6)" / "(Recharges after a Short or Long Rest)". */
function rechargeAbilities(m?: Monster): RechargeAbility[] {
  if (!m) return []
  const out: RechargeAbility[] = []
  for (const e of [...m.actions, ...m.reactions, ...m.legendary_actions, ...m.traits]) {
    const roll = RECHARGE_ROLL.exec(e.name ?? '')
    const rest = roll ? null : RECHARGE_REST.exec(e.name ?? '')
    const hit = roll ?? rest
    if (!hit) continue
    const name = e.name.replace(hit[0], '').trim()
    if (!out.some((a) => a.name === name)) out.push({ name, min: roll ? Number(roll[1]) : null })
  }
  return out
}

function CombatantRow({
  c, monster, round, active, encounterId, reserve = false, waveEdit = null, onChange, onError, onShowDetail,
}: {
  c: Combatant
  monster?: Monster
  round: number
  active: boolean
  encounterId: number
  reserve?: boolean          // waiting in a later wave
  waveEdit?: number | null   // lowest wave it may be moved to; null = wave not editable
  onChange: (e: Encounter) => void
  onError: (m: string) => void
  onShowDetail: (monsterId: number) => void
}) {
  const [delta, setDelta] = useState('')
  // one CON save per damage source, resolved in order
  const [concDcs, setConcDcs] = useState<number[]>([])
  // recharge prompts waved off ("didn't recharge"): ability name -> round
  const [rollDismissed, setRollDismissed] = useState<Record<string, number>>({})
  const recharges = rechargeAbilities(monster)

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
      const hp = Math.max(0, c.current_hp - (n - fromTemp))
      // at 0 HP the creature is incapacitated, which ends concentration outright
      const drop = c.concentrating && hp === 0
      patch({ temp_hp: c.temp_hp - fromTemp, current_hp: hp, ...(drop ? { concentrating: false } : {}) })
      if (drop) setConcDcs([])
      else if (c.concentrating) setConcDcs((d) => [...d, Math.min(30, Math.max(10, Math.floor(n / 2)))])
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
    // PCs never carry HP here, so `down` must not grey every player out
    <li className={`combatant ${c.is_pc ? 'is-pc' : ''} ${active ? 'active' : ''} ${reserve ? 'reserve' : ''} ${!c.is_pc && c.current_hp === 0 ? 'down' : ''}`}>
      <div className="init">
        <input
          className="init-input"
          type="number"
          value={c.initiative ?? ''}
          placeholder="–"
          onChange={(e) => patch({ initiative: e.target.value === '' ? null : Number(e.target.value) })}
        />
      </div>

      {/* own column, so shields and medals line up down the list */}
      <div className="ac-slot">
        {c.is_pc ? (
          <span className="pc-medal" title={c.level ? `Level ${c.level}` : 'Player character'}>
            <small>Lvl</small>
            <b>{c.level ?? '—'}</b>
          </span>
        ) : (
          <span className="ac-shield" title={`Armor Class ${c.armor_class}`}>
            <span className="ac-shield-num">{c.armor_class}</span>
          </span>
        )}
      </div>

      <div className="who">
        <div className="who-head">
          {c.monster_id !== null ? (
            <button className="link-strong name-btn" onClick={() => onShowDetail(c.monster_id!)}>
              {c.name}
            </button>
          ) : (
            <strong>{c.name}</strong>
          )}
          {!c.is_pc && <NickTag nick={c.nick} name={c.name} onSave={(nick) => patch({ nick })} />}
        </div>
        <span className="tags">
          {/* level lives on the medal now — no need to say it twice */}
          {c.is_pc
            ? <span className="tag pc">Player</span>
            : <span className="tag npc">NPC</span>}
          {waveEdit != null && (
            <label className="tag wave-pick" title="Wave this combatant arrives in (0 = there from the start)">
              wave
              <input
                type="number" min={waveEdit} max={50} value={c.wave}
                aria-label={`Wave for ${c.name}`}
                onChange={(e) => {
                  const w = Number(e.target.value)
                  if (e.target.value !== '' && Number.isInteger(w) && w >= waveEdit && w <= 50) patch({ wave: w })
                }}
              />
            </label>
          )}
          <button
            className={`tag conc ${c.concentrating ? 'on' : ''}`}
            title="Concentration — toggle; taking damage shows the CON save DC"
            onClick={() => { setConcDcs([]); patch({ concentrating: !c.concentrating }) }}
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
        {recharges.length > 0 && (
          <span className="recharge">
            {recharges.map((a) => {
              const used = c.recharge_used.find((u) => u.name === a.name)
              const range = a.min === null ? 'rest' : a.min === 6 ? '6' : `${a.min}–6`
              const ready = () => patch({ recharge_used: c.recharge_used.filter((u) => u.name !== a.name) })
              if (!used) {
                return (
                  <button key={a.name} className="rc-chip" title={`Ready (recharge ${range}) — click when used`}
                    onClick={() => patch({ recharge_used: [...c.recharge_used, { name: a.name, round }] })}>
                    {a.name} <small>{range}</small>
                  </button>
                )
              }
              // recharge roll: start of its own turn, from the round after it was spent
              const rollNow = active && a.min !== null && round > used.round && rollDismissed[a.name] !== round
              if (rollNow) {
                return (
                  <span key={a.name} className="rc-roll">
                    <span>Roll d6 for <b>{a.name}</b>: {range}?</span>
                    <button className="heal" onClick={ready}>Recharged</button>
                    <button className="ghost" onClick={() => setRollDismissed((d) => ({ ...d, [a.name]: round }))}>No</button>
                  </span>
                )
              }
              return (
                <button key={a.name} className="rc-chip used"
                  title={a.min === null ? 'Used — back after a rest; click to mark ready' : 'Used — click to mark ready again'}
                  onClick={ready}>
                  {a.name} <small>used</small>
                </button>
              )
            })}
          </span>
        )}
        {c.concentrating && concDcs.length > 0 && (
          <span className="conc-alert">
            <span>
              ✦ CON save DC <b>{concDcs[0]}</b>
              {concDcs.length > 1 && <span className="muted"> (then {concDcs.slice(1).join(', ')})</span>}
            </span>
            <button className="heal" onClick={() => setConcDcs((d) => d.slice(1))}>Kept</button>
            <button className="danger" onClick={() => { setConcDcs([]); patch({ concentrating: false }) }}>Lost</button>
          </span>
        )}
      </div>

      {/* DM does not track player HP — HP bar/controls shown for monsters only */}
      {c.is_pc ? (
        <div className="hp pc-hp">
          <span className="pc-hp-mark">✦</span>
          <span>HP tracked by player</span>
        </div>
      ) : (
        <div className="hp">
          <div className="hp-row">
            <div className="hp-bar"><div className={`hp-fill ${hpColor}`} style={{ width: `${hpPct}%` }} /></div>
            <span className={`hp-num ${hpColor}`}>
              <b>{c.current_hp}</b><i>/{c.max_hp}</i>
              {c.temp_hp ? <em>+{c.temp_hp}</em> : null}
            </span>
          </div>
          <div className="hp-ctrl">
            <input
              type="number"
              inputMode="numeric"
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
      )}

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
  encounterId, currentWave, monsters, onAdded, onError,
}: {
  encounterId: number
  currentWave: number
  monsters: Monster[]
  onAdded: (e: Encounter) => void
  onError: (m: string) => void
}) {
  const [mode, setMode] = useState<'pc' | 'monster'>('monster')
  const [name, setName] = useState('')
  const [level, setLevel] = useState('')
  const [init, setInit] = useState('')
  const [monsterId, setMonsterId] = useState<number | ''>('')
  const [count, setCount] = useState('1')
  const [wave, setWave] = useState('')  // empty = the wave fighting now
  const [saveToParty, setSaveToParty] = useState(true)
  const [party, setParty] = useState<Character[]>([])

  const loadParty = useCallback(() => { api.characters.list().then(setParty).catch(() => {}) }, [])
  useEffect(loadParty, [loadParty])

  async function addSaved(ch: Character) {
    try {
      onAdded(await api.encounters.addCombatant(encounterId, {
        name: ch.name, is_pc: true, level: ch.level, max_hp: ch.max_hp,
      }))
    } catch (err) { onError((err as Error).message) }
  }

  async function removeSaved(id: number) {
    try { await api.characters.remove(id); loadParty() }
    catch (err) { onError((err as Error).message) }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const initiative = init === '' ? null : Number(init)
      if (mode === 'monster') {
        if (monsterId === '') return
        const n = Math.min(20, Math.max(1, parseInt(count, 10) || 1))
        const w = wave === '' ? undefined : Math.min(50, Math.max(currentWave, parseInt(wave, 10) || 0))
        onAdded(await api.encounters.addCombatant(encounterId, { monster_id: Number(monsterId), initiative, count: n, wave: w }))
      } else {
        if (!name.trim()) return
        const lvl = level ? Math.min(20, Math.max(1, Number(level))) : undefined
        // DM does not track player HP — max_hp is a placeholder, never shown/edited
        onAdded(await api.encounters.addCombatant(encounterId, {
          name: name.trim(), is_pc: true, initiative, level: lvl, max_hp: 1,
        }))
        if (saveToParty && !party.some((p) => p.name.toLowerCase() === name.trim().toLowerCase())) {
          await api.characters.create({ name: name.trim(), max_hp: 1, level: lvl ?? 1 })
          loadParty()
        }
      }
      setName(''); setLevel(''); setInit(''); setMonsterId(''); setCount('1')
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

      {mode === 'pc' && party.length > 0 && (
        <div className="row party-roster">
          <span className="muted">Party:</span>
          {party.map((p) => (
            <span key={p.id} className="party-chip">
              <button type="button" className="party-add" title={`Add ${p.name} (Lvl ${p.level})`} onClick={() => addSaved(p)}>
                {p.name} <span className="muted">L{p.level}</span>
              </button>
              <button type="button" className="party-del" title="Remove from party" onClick={() => removeSaved(p.id)}>✕</button>
            </span>
          ))}
        </div>
      )}

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
            <input type="number" placeholder="init" value={init} onChange={(e) => setInit(e.target.value)} style={{ width: 70 }} />
            <input
              type="number" min={currentWave} max={50} placeholder="wave" value={wave}
              title={`Wave to arrive in. Empty = in the fight now (wave ${currentWave}). A later wave waits until you start it.`}
              onChange={(e) => setWave(e.target.value)} style={{ width: 74 }}
            />
            <button type="submit">+ Add</button>
          </>
        ) : (
          <>
            <input placeholder="PC name" value={name} onChange={(e) => setName(e.target.value)} />
            <input type="number" placeholder="Lvl" min={1} max={20} value={level} onChange={(e) => setLevel(e.target.value)} style={{ width: 62 }} />
            <input type="number" placeholder="init" value={init} onChange={(e) => setInit(e.target.value)} style={{ width: 70 }} />
            <label className="save-party" title="Save to party for later">
              <input type="checkbox" checked={saveToParty} onChange={(e) => setSaveToParty(e.target.checked)} /> save
            </label>
            <button type="submit">+ Add</button>
          </>
        )}
      </div>
    </form>
  )
}
