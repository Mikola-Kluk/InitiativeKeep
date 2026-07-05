import { useState } from 'react'
import { api, type Monster } from '../api/client'

type Entry = { name: string; desc: string }
type AbilityKey = 'strength' | 'dexterity' | 'constitution' | 'intelligence' | 'wisdom' | 'charisma'

const ABILITIES: [AbilityKey, string][] = [
  ['strength', 'STR'], ['dexterity', 'DEX'], ['constitution', 'CON'],
  ['intelligence', 'INT'], ['wisdom', 'WIS'], ['charisma', 'CHA'],
]
const SPEED_KEYS = ['walk', 'fly', 'swim', 'climb', 'burrow']

// "1/4" -> 0.25, "5" -> 5. Used for CR sorting / XP.
function parseCr(s: string): number | null {
  const t = s.trim()
  if (!t) return null
  if (t.includes('/')) {
    const [a, b] = t.split('/').map(Number)
    return b ? a / b : null
  }
  const n = Number(t)
  return isNaN(n) ? null : n
}

type Draft = {
  name: string
  size: string
  type: string
  alignment: string
  armor_class: number
  armor_desc: string
  hit_points: number
  hit_dice: string
  speed: Record<string, number>
  strength: number; dexterity: number; constitution: number
  intelligence: number; wisdom: number; charisma: number
  challenge_rating: string
  damage_vulnerabilities: string
  damage_resistances: string
  damage_immunities: string
  condition_immunities: string
  senses: string
  languages: string
  traits: Entry[]
  actions: Entry[]
  reactions: Entry[]
  legendary_desc: string
  legendary_actions: Entry[]
}

function toDraft(m?: Monster): Draft {
  return {
    name: m?.name ?? '',
    size: m?.size ?? 'Medium',
    type: m?.type ?? '',
    alignment: m?.alignment ?? '',
    armor_class: m?.armor_class ?? 12,
    armor_desc: m?.armor_desc ?? '',
    hit_points: m?.hit_points ?? 10,
    hit_dice: m?.hit_dice ?? '',
    speed: m?.speed && Object.keys(m.speed).length ? { ...m.speed } : { walk: 30 },
    strength: m?.strength ?? 10, dexterity: m?.dexterity ?? 10, constitution: m?.constitution ?? 10,
    intelligence: m?.intelligence ?? 10, wisdom: m?.wisdom ?? 10, charisma: m?.charisma ?? 10,
    challenge_rating: m?.challenge_rating ?? '',
    damage_vulnerabilities: m?.damage_vulnerabilities ?? '',
    damage_resistances: m?.damage_resistances ?? '',
    damage_immunities: m?.damage_immunities ?? '',
    condition_immunities: m?.condition_immunities ?? '',
    senses: m?.senses ?? '',
    languages: m?.languages ?? '',
    traits: m?.traits ? m.traits.map((t) => ({ ...t })) : [],
    actions: m?.actions ? m.actions.map((t) => ({ ...t })) : [],
    reactions: m?.reactions ? m.reactions.map((t) => ({ ...t })) : [],
    legendary_desc: m?.legendary_desc ?? '',
    legendary_actions: m?.legendary_actions ? m.legendary_actions.map((t) => ({ ...t })) : [],
  }
}

const SIZES = ['Tiny', 'Small', 'Medium', 'Large', 'Huge', 'Gargantuan']

export default function MonsterEditor({
  monster, onClose, onSaved,
}: {
  monster?: Monster
  onClose: () => void
  onSaved: () => void
}) {
  const [d, setD] = useState<Draft>(() => toDraft(monster))
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const editing = monster !== undefined && !monster.is_homebrew ? false : monster !== undefined

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setD((prev) => ({ ...prev, [key]: value }))
  }
  function setSpeed(key: string, value: string) {
    setD((prev) => {
      const speed = { ...prev.speed }
      if (value === '') delete speed[key]
      else speed[key] = Number(value)
      return { ...prev, speed }
    })
  }
  function num(v: string, fallback: number) { const n = Number(v); return isNaN(n) ? fallback : n }

  async function save(e: React.FormEvent) {
    e.preventDefault()
    if (!d.name.trim()) { setError('Name is required.'); return }
    setSaving(true)
    setError(null)
    const clean = (list: Entry[]) => list.filter((x) => x.name.trim() || x.desc.trim())
    const payload: Partial<Monster> = {
      name: d.name.trim(),
      size: d.size || null,
      type: d.type.trim() || null,
      alignment: d.alignment.trim() || null,
      armor_class: d.armor_class,
      armor_desc: d.armor_desc.trim() || null,
      hit_points: Math.max(1, d.hit_points),
      hit_dice: d.hit_dice.trim() || null,
      speed: d.speed,
      strength: d.strength, dexterity: d.dexterity, constitution: d.constitution,
      intelligence: d.intelligence, wisdom: d.wisdom, charisma: d.charisma,
      challenge_rating: d.challenge_rating.trim() || null,
      cr: parseCr(d.challenge_rating),
      damage_vulnerabilities: d.damage_vulnerabilities.trim() || null,
      damage_resistances: d.damage_resistances.trim() || null,
      damage_immunities: d.damage_immunities.trim() || null,
      condition_immunities: d.condition_immunities.trim() || null,
      senses: d.senses.trim() || null,
      languages: d.languages.trim() || null,
      traits: clean(d.traits),
      actions: clean(d.actions),
      reactions: clean(d.reactions),
      legendary_desc: d.legendary_desc.trim() || null,
      legendary_actions: clean(d.legendary_actions),
    }
    try {
      if (editing && monster) await api.monsters.update(monster.id, payload)
      else await api.monsters.create(payload)
      onSaved()
    } catch (err) {
      setError((err as Error).message)
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal editor" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2>{editing ? 'Edit statblock' : 'New statblock'}</h2>
        {error && <p className="error">{error}</p>}

        <form onSubmit={save}>
          <div className="ed-grid">
            <label className="ed-wide">Name
              <input value={d.name} onChange={(e) => set('name', e.target.value)} placeholder="e.g. Bandit Warlord" />
            </label>
            <label>Size
              <select value={d.size} onChange={(e) => set('size', e.target.value)}>
                {SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <label>Type
              <input value={d.type} onChange={(e) => set('type', e.target.value)} placeholder="humanoid, dragon…" />
            </label>
            <label>Alignment
              <input value={d.alignment} onChange={(e) => set('alignment', e.target.value)} placeholder="chaotic evil" />
            </label>
          </div>

          <div className="ed-grid">
            <label>AC
              <input type="number" value={d.armor_class} onChange={(e) => set('armor_class', num(e.target.value, 10))} />
            </label>
            <label className="ed-wide">Armor note
              <input value={d.armor_desc} onChange={(e) => set('armor_desc', e.target.value)} placeholder="natural armor, plate…" />
            </label>
            <label>HP
              <input type="number" value={d.hit_points} onChange={(e) => set('hit_points', num(e.target.value, 1))} />
            </label>
            <label>Hit dice
              <input value={d.hit_dice} onChange={(e) => set('hit_dice', e.target.value)} placeholder="4d8+8 (rerolled on start)" />
            </label>
          </div>

          <fieldset className="ed-fs">
            <legend>Speed (ft.)</legend>
            <div className="ed-speed">
              {SPEED_KEYS.map((k) => (
                <label key={k}>{k}
                  <input type="number" min={0} value={d.speed[k] ?? ''} onChange={(e) => setSpeed(k, e.target.value)} placeholder="—" />
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className="ed-fs">
            <legend>Ability scores</legend>
            <div className="ed-abilities">
              {ABILITIES.map(([key, label]) => {
                const v = d[key]
                const mod = Math.floor((v - 10) / 2)
                return (
                  <label key={label}>{label} <span className="muted">({mod >= 0 ? '+' : ''}{mod})</span>
                    <input type="number" min={1} max={30} value={v} onChange={(e) => set(key, num(e.target.value, 10))} />
                  </label>
                )
              })}
            </div>
          </fieldset>

          <div className="ed-grid">
            <label>Challenge rating
              <input value={d.challenge_rating} onChange={(e) => set('challenge_rating', e.target.value)} placeholder="5, 1/4, 1/2…" />
            </label>
            <span className="ed-crhint muted">
              {d.challenge_rating.trim() ? `→ CR ${parseCr(d.challenge_rating) ?? '?'} (drives XP / difficulty)` : 'set for encounter difficulty & XP'}
            </span>
          </div>

          <fieldset className="ed-fs">
            <legend>Defenses & senses</legend>
            <div className="ed-grid">
              <label className="ed-wide">Damage immunities
                <input value={d.damage_immunities} onChange={(e) => set('damage_immunities', e.target.value)} placeholder="fire, poison" />
              </label>
              <label className="ed-wide">Damage resistances
                <input value={d.damage_resistances} onChange={(e) => set('damage_resistances', e.target.value)} placeholder="cold; bludgeoning from nonmagical attacks" />
              </label>
              <label className="ed-wide">Damage vulnerabilities
                <input value={d.damage_vulnerabilities} onChange={(e) => set('damage_vulnerabilities', e.target.value)} placeholder="radiant" />
              </label>
              <label className="ed-wide">Condition immunities
                <input value={d.condition_immunities} onChange={(e) => set('condition_immunities', e.target.value)} placeholder="charmed, frightened, poisoned" />
              </label>
              <label className="ed-wide">Senses
                <input value={d.senses} onChange={(e) => set('senses', e.target.value)} placeholder="darkvision 120 ft., passive Perception 23" />
              </label>
              <label className="ed-wide">Languages
                <input value={d.languages} onChange={(e) => set('languages', e.target.value)} placeholder="Common, Draconic" />
              </label>
            </div>
          </fieldset>

          <EntryList label="Traits" entries={d.traits} onChange={(v) => set('traits', v)} placeholder={{ name: 'Pack Tactics', desc: 'Advantage on attacks when an ally is within 5 ft. of the target.' }} />
          <EntryList label="Actions" entries={d.actions} onChange={(v) => set('actions', v)} placeholder={{ name: 'Greataxe', desc: 'Melee Attack: +6 to hit, 1d12+4 slashing.' }} />
          <EntryList label="Reactions" entries={d.reactions} onChange={(v) => set('reactions', v)} placeholder={{ name: 'Parry', desc: '+2 AC against one melee attack.' }} />

          <fieldset className="ed-fs">
            <legend>Legendary actions</legend>
            <label className="ed-block">Intro
              <input value={d.legendary_desc} onChange={(e) => set('legendary_desc', e.target.value)} placeholder="Can take 3 legendary actions…" />
            </label>
            <EntryList label="" entries={d.legendary_actions} onChange={(v) => set('legendary_actions', v)} placeholder={{ name: 'Tail Attack', desc: 'The creature makes a tail attack.' }} />
            <p className="muted ed-note">Add any here and combatants spawned from this get a 3-orb legendary pool.</p>
          </fieldset>

          <div className="row ed-actions">
            <button type="submit" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Create statblock'}</button>
            <button type="button" className="ghost" onClick={onClose}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EntryList({
  label, entries, onChange, placeholder,
}: {
  label: string
  entries: Entry[]
  onChange: (v: Entry[]) => void
  placeholder: Entry
}) {
  function add() { onChange([...entries, { name: '', desc: '' }]) }
  function update(i: number, patch: Partial<Entry>) {
    onChange(entries.map((e, j) => (j === i ? { ...e, ...patch } : e)))
  }
  function remove(i: number) { onChange(entries.filter((_, j) => j !== i)) }

  return (
    <fieldset className="ed-fs">
      <legend>{label || 'Entries'}</legend>
      {entries.length === 0 && <p className="muted ed-note">None yet.</p>}
      {entries.map((e, i) => (
        <div key={i} className="ed-entry">
          <input className="ed-entry-name" value={e.name} placeholder={placeholder.name} onChange={(ev) => update(i, { name: ev.target.value })} />
          <textarea className="ed-entry-desc" value={e.desc} placeholder={placeholder.desc} rows={2} onChange={(ev) => update(i, { desc: ev.target.value })} />
          <button type="button" className="danger ed-entry-del" onClick={() => remove(i)}>✕</button>
        </div>
      ))}
      <button type="button" className="ed-add" onClick={add}>＋ Add {label ? label.toLowerCase().replace(/s$/, '') : 'entry'}</button>
    </fieldset>
  )
}
