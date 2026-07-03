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
  onClose,
}: {
  monsterId: number
  onClose: () => void
}) {
  const [m, setM] = useState<Monster | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.monsters.get(monsterId).then(setM).catch((e) => setError(e.message))
  }, [monsterId])

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal statblock" onClick={(e) => e.stopPropagation()}>
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
          </>
        )}
      </div>
    </div>
  )
}
