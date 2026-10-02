// Shared reference for the monster statblock JSON shape (MonsterCreate in
// backend/app/schemas/monster.py). Used by Paste JSON and the statblock editor.

export const EXAMPLE_JSON = `{
  "name": "Goblin Boss",
  "size": "Small",
  "type": "humanoid",
  "alignment": "neutral evil",
  "armor_class": 17,
  "armor_desc": "chain shirt, shield",
  "hit_points": 21,
  "hit_dice": "6d6",
  "speed": { "walk": 30 },
  "strength": 10,
  "dexterity": 14,
  "constitution": 10,
  "intelligence": 10,
  "wisdom": 8,
  "charisma": 10,
  "challenge_rating": "1",
  "cr": 1,
  "senses": "darkvision 60 ft., passive Perception 9",
  "languages": "Common, Goblin",
  "traits": [
    { "name": "Nimble Escape", "desc": "Disengages or Hides as a bonus action." }
  ],
  "actions": [
    { "name": "Scimitar", "desc": "Melee: +4 to hit, 5 ft., one target. Hit: 5 (1d6 + 2) slashing." }
  ],
  "reactions": [
    { "name": "Redirect Attack", "desc": "Swaps places with a nearby ally to take a hit." }
  ],
  "legendary_actions": []
}`

export const EXAMPLE_LIST_JSON = `[
  { "name": "Goblin", "armor_class": 15, "hit_points": 7, "hit_dice": "2d6", "dexterity": 14, "cr": 0.25 },
  { "name": "Wolf", "armor_class": 13, "hit_points": 11, "hit_dice": "2d8+2", "dexterity": 15, "cr": 0.25 }
]`

type FieldDoc = [field: string, type: string, def: string, notes: string]

export const SCHEMA_FIELDS: FieldDoc[] = [
  ['name', 'string', 'required', 'The only required field.'],
  ['size', 'string', '—', 'Tiny, Small, Medium, Large, Huge, Gargantuan'],
  ['type', 'string', '—', 'humanoid, beast, dragon, …'],
  ['alignment', 'string', '—', ''],
  ['armor_class', 'integer ≥ 0', '10', ''],
  ['armor_desc', 'string', '—', 'e.g. "natural armor"'],
  ['hit_points', 'integer ≥ 1', '1', 'Average HP'],
  ['hit_dice', 'string', '—', 'NdM+K, e.g. "2d8+2". HP is rolled from it when combat starts.'],
  ['speed', 'object', '{}', '{ "walk": 30, "fly": 60, "swim": 20, … }'],
  ['strength … charisma', 'integer 1–30', '10', 'strength, dexterity, constitution, intelligence, wisdom, charisma. Dexterity sets the initiative bonus.'],
  ['challenge_rating', 'string', '—', 'Display form: "1/4", "5"'],
  ['cr', 'number', '—', 'Numeric form: 0.25, 5. Used for filtering and difficulty.'],
  ['damage_vulnerabilities', 'string', '—', 'Free text'],
  ['damage_resistances', 'string', '—', 'Free text'],
  ['damage_immunities', 'string', '—', 'Free text'],
  ['condition_immunities', 'string', '—', 'Free text'],
  ['senses', 'string', '—', 'e.g. "darkvision 60 ft., passive Perception 9"'],
  ['languages', 'string', '—', ''],
  ['traits', '[{name, desc}]', '[]', "Also accepted as Open5e's special_abilities."],
  ['actions', '[{name, desc}]', '[]', ''],
  ['reactions', '[{name, desc}]', '[]', ''],
  ['legendary_desc', 'string', '—', 'Intro text for legendary actions'],
  ['legendary_actions', '[{name, desc}]', '[]', 'If not empty, the creature gets 3 legendary actions per round in combat.'],
]


export function SchemaTable() {
  return (
    <>
      <p className="muted">
        Only <code>name</code> is required. Missing fields get their default, and unknown
        keys are ignored.
      </p>
      <div className="schema-table-wrap">
        <table className="schema-table">
          <thead>
            <tr><th>Field</th><th>Type</th><th>Default</th><th>Notes</th></tr>
          </thead>
          <tbody>
            {SCHEMA_FIELDS.map(([f, t, d, n]) => (
              <tr key={f}>
                <td><code>{f}</code></td>
                <td>{t}</td>
                <td>{d === 'required' ? <strong>required</strong> : <code>{d}</code>}</td>
                <td>{n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
