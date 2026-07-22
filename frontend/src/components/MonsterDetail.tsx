import { useEffect, useState } from 'react'
import { api, type Monster } from '../api/client'

const ABILITIES: [keyof Monster, string][] = [
  ['strength', 'STR'], ['dexterity', 'DEX'], ['constitution', 'CON'],
  ['intelligence', 'INT'], ['wisdom', 'WIS'], ['charisma', 'CHA'],
]

function mod(score: number): string {
  const m = Math.floor((score - 10) / 2)
  return m >= 0 ? `+${m}` : `${m}`
}

export default function MonsterDetail({
  monsterId,
  open5eSlug,
  onClose,
  variant = 'modal',
}: {
  monsterId?: number
  open5eSlug?: string
  onClose: () => void
  variant?: 'modal' | 'panel'
}) {
  const [m, setM] = useState<Monster | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load =
      open5eSlug !== undefined
        ? api.open5e.preview(open5eSlug)
        : api.monsters.get(monsterId!)
    load.then(setM).catch((e) => setError(e.message))
  }, [monsterId, open5eSlug])

  const body = (
    <>
      <button className="modal-close" onClick={onClose}>✕</button>
      {error && <p className="error">{error}</p>}
      {!m ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
            <h2>{m.name}</h2>
            <p className="sb-sub">
              {[m.size, m.type, m.alignment].filter(Boolean).join(' · ')}
            </p>

            <hr className="sb-rule" />

            <div className="sb-line">
              <span><b>AC</b> {m.armor_class}{m.armor_desc ? ` (${m.armor_desc})` : ''}</span>
              <span><b>HP</b> {m.hit_points}{m.hit_dice ? ` (${m.hit_dice})` : ''}</span>
              <span><b>CR</b> {m.challenge_rating ?? '—'}</span>
            </div>

            {m.speed && Object.keys(m.speed).length > 0 && (
              <p className="sb-line">
                <b>Speed</b>{' '}
                {Object.entries(m.speed).map(([k, v]) => `${k} ${v} ft.`).join(', ')}
              </p>
            )}

            {(m.damage_vulnerabilities || m.damage_resistances || m.damage_immunities ||
              m.condition_immunities || m.senses || m.languages) && (
              <div className="sb-defenses">
                {m.damage_vulnerabilities && <p className="sb-line"><b>Vulnerabilities</b> {m.damage_vulnerabilities}</p>}
                {m.damage_resistances && <p className="sb-line"><b>Resistances</b> {m.damage_resistances}</p>}
                {m.damage_immunities && <p className="sb-line"><b>Damage Immunities</b> {m.damage_immunities}</p>}
                {m.condition_immunities && <p className="sb-line"><b>Condition Immunities</b> {m.condition_immunities}</p>}
                {m.senses && <p className="sb-line"><b>Senses</b> {m.senses}</p>}
                {m.languages && <p className="sb-line"><b>Languages</b> {m.languages}</p>}
              </div>
            )}

            <hr className="sb-rule" />

            <div className="abilities">
              {ABILITIES.map(([key, label]) => {
                const score = m[key] as number
                return (
                  <div key={label} className="ability">
                    <div className="ability-label">{label}</div>
                    <div className="ability-score">{score} <span className="muted">({mod(score)})</span></div>
                  </div>
                )
              })}
            </div>

            {m.traits.length > 0 && (
              <div className="sb-section">
                <h3>Traits</h3>
                {m.traits.map((t, i) => (
                  <p key={i}><b>{t.name}.</b> {t.desc}</p>
                ))}
              </div>
            )}

            {m.actions.length > 0 && (
              <div className="sb-section">
                <h3>Actions</h3>
                {m.actions.map((a, i) => (
                  <p key={i}><b>{a.name}.</b> {a.desc}</p>
                ))}
              </div>
            )}

            {(m.reactions ?? []).length > 0 && (
              <div className="sb-section">
                <h3>Reactions</h3>
                {m.reactions.map((r, i) => (
                  <p key={i}><b>{r.name}.</b> {r.desc}</p>
                ))}
              </div>
            )}

            {((m.legendary_actions ?? []).length > 0 || m.legendary_desc) && (
              <div className="sb-section">
                <h3>Legendary Actions</h3>
                {m.legendary_desc && <p className="muted">{m.legendary_desc}</p>}
                {(m.legendary_actions ?? []).map((a, i) => (
                  <p key={i}><b>{a.name}.</b> {a.desc}</p>
                ))}
              </div>
            )}
        </>
      )}
    </>
  )

  if (variant === 'panel') {
    return (
      <aside className="statblock-panel statblock">
        {body}
      </aside>
    )
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal statblock" onClick={(e) => e.stopPropagation()}>
        {body}
      </div>
    </div>
  )
}
