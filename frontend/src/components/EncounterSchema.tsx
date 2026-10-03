// Reference for the prepared-encounter JSON shape (EncounterPrepare in
// backend/app/schemas/encounter.py — update by hand when the schema changes).
// Used by Paste JSON on the encounter list.

import type { Monster } from '../api/client'

type FieldDoc = [field: string, type: string, def: string, notes: string]

export const ENCOUNTER_FIELDS: FieldDoc[] = [
  ['name', 'string', 'required', 'Encounter name.'],
  ['notes', 'string', '—', 'Free text for the DM.'],
  ['enemies', '[{…}]', '[]', 'Up to 50 entries. Leave empty for a bare encounter.'],
  ['enemies[].monster', 'string', 'one of the two', 'Name of a monster in your library, any letter case (see the Library tab).'],
  ['enemies[].monster_id', 'integer', 'one of the two', 'Its id instead of the name. Needed when two different statblocks share a name.'],
  ['enemies[].count', 'integer 1–20', '1', 'Copies to spawn, numbered automatically: Goblin (1), Goblin (2), …'],
  ['enemies[].name', 'string', '—', 'Replaces the statblock name for this entry.'],
  ['enemies[].nick', 'string ≤ 100', '—', 'Tag shown beside the name, e.g. "elf". Goes on every copy; editable in the tracker.'],
]

/** Example payload; uses real library names when there are any, so it works as pasted. */
export function exampleEncounterJson(monsters: Monster[]): string {
  const [a, b] = monsters
  const enemies = [
    `    { "monster": ${JSON.stringify(a?.name ?? 'Goblin')}, "count": 3 }`,
    `    { "monster": ${JSON.stringify(a?.name ?? 'Goblin')}, "nick": "elf, has the key" }`,
    `    { "monster": ${JSON.stringify(b?.name ?? a?.name ?? 'Young Red Dragon')}, "name": "Old Smoky" }`,
  ]
  return `{
  "name": "Ambush at the ford",
  "notes": "Goblins hide under the bridge.",
  "enemies": [
${enemies.join(',\n')}
  ]
}`
}

export function EncounterSchemaTable() {
  return (
    <>
      <p className="muted">
        Only <code>name</code> is required. Enemies come from your monster library, picked by{' '}
        <code>monster</code> (name) or <code>monster_id</code>; one unknown monster rejects the
        whole encounter. Players are not part of this — add
        them in the tracker afterwards.
      </p>
      <div className="schema-table-wrap">
        <table className="schema-table">
          <thead>
            <tr><th>Field</th><th>Type</th><th>Default</th><th>Notes</th></tr>
          </thead>
          <tbody>
            {ENCOUNTER_FIELDS.map(([f, t, d, n]) => (
              <tr key={f}>
                <td><code>{f}</code></td>
                <td>{t}</td>
                <td>{d === 'required' || d === 'one of the two' ? <strong>{d}</strong> : <code>{d}</code>}</td>
                <td>{n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

export function MonsterIdTable({ monsters }: { monsters: Monster[] }) {
  if (monsters.length === 0) {
    return <p className="muted">Your library is empty. Import or create monsters on the Monsters tab first.</p>
  }
  const sharing = new Map<string, number>()
  for (const m of monsters) {
    const key = m.name.trim().toLowerCase()
    sharing.set(key, (sharing.get(key) ?? 0) + 1)
  }
  const shared = (m: Monster) => (sharing.get(m.name.trim().toLowerCase()) ?? 0) > 1
  return (
    <div className="schema-table-wrap">
      {monsters.some(shared) && (
        <p className="muted">
          ⚠ marks a name used by more than one statblock. Exact copies are fine — the oldest is
          used. If they differ, pick one by <code>monster_id</code>.
        </p>
      )}
      <table className="schema-table">
        <thead>
          <tr><th>monster</th><th>monster_id</th><th>CR</th><th>HP</th><th>Source</th></tr>
        </thead>
        <tbody>
          {monsters.map((m) => (
            <tr key={m.id}>
              <td>{m.name}{shared(m) && <span title="Name shared with another statblock"> ⚠</span>}</td>
              <td><code>{m.id}</code></td>
              <td>{m.challenge_rating ?? '—'}</td>
              <td>{m.hit_points}</td>
              <td>{m.slug ?? m.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
