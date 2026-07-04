const BASE = '/api/v1'

// ---- Types (mirror backend schemas) ----

export interface Monster {
  id: number
  name: string
  slug: string | null
  source: string
  is_homebrew: boolean
  size: string | null
  type: string | null
  alignment: string | null
  armor_class: number
  armor_desc: string | null
  hit_points: number
  hit_dice: string | null
  speed: Record<string, number>
  strength: number
  dexterity: number
  constitution: number
  intelligence: number
  wisdom: number
  charisma: number
  challenge_rating: string | null
  cr: number | null
  traits: { name: string; desc: string }[]
  actions: { name: string; desc: string }[]
  reactions: { name: string; desc: string }[]
  legendary_desc: string | null
  legendary_actions: { name: string; desc: string }[]
  dex_modifier: number
}

export interface ConditionEntry {
  name: string
  rounds: number | null // remaining rounds; null = until removed
}

export interface Combatant {
  id: number
  monster_id: number | null
  name: string
  is_pc: boolean
  initiative: number | null
  dex_modifier: number
  armor_class: number
  max_hp: number
  current_hp: number
  temp_hp: number
  conditions: ConditionEntry[]
  concentrating: boolean
  legendary_actions_max: number
  legendary_actions_remaining: number
}

export interface Encounter {
  id: number
  name: string
  notes: string | null
  round: number
  current_turn_index: number
  combatants: Combatant[]
}

export interface Open5eRow {
  slug: string
  name: string
  type: string | null
  challenge_rating: string | null
  cr: number | null
  hit_points: number | null
  document: string | null
}

export interface Open5eBrowse {
  count: number
  page: number
  num_pages: number
  results: Open5eRow[]
}

export interface Open5eSource {
  slug: string
  name: string | null
}

// ---- Fetch wrapper ----

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

function qs(params: Record<string, string | number | undefined>): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
  return parts.length ? `?${parts.join('&')}` : ''
}

// ---- API ----

export const api = {
  monsters: {
    list: (search?: string) =>
      request<Monster[]>(`/monsters/${qs({ search })}`),
    get: (id: number) => request<Monster>(`/monsters/${id}`),
    create: (data: Partial<Monster>) =>
      request<Monster>('/monsters/', { method: 'POST', body: JSON.stringify(data) }),
    remove: (id: number) =>
      request<void>(`/monsters/${id}`, { method: 'DELETE' }),
  },

  open5e: {
    browse: (params: { q?: string; cr?: string; type?: string; document?: string; page?: number }) =>
      request<Open5eBrowse>(`/open5e/monsters${qs(params)}`),
    preview: (slug: string) => request<Monster>(`/open5e/monsters/${slug}`),
    sources: () => request<Open5eSource[]>('/open5e/sources'),
    importOne: (slug: string) =>
      request<Monster>(`/open5e/import/${slug}`, { method: 'POST' }),
    importBulk: (slugs: string[]) =>
      request<{ imported: string[]; failed: string[] }>('/open5e/import', {
        method: 'POST',
        body: JSON.stringify({ slugs }),
      }),
  },

  encounters: {
    list: () => request<Encounter[]>('/encounters/'),
    get: (id: number) => request<Encounter>(`/encounters/${id}`),
    create: (name: string) =>
      request<Encounter>('/encounters/', { method: 'POST', body: JSON.stringify({ name }) }),
    remove: (id: number) =>
      request<void>(`/encounters/${id}`, { method: 'DELETE' }),
    addCombatant: (id: number, body: Partial<Combatant> & { monster_id?: number; count?: number }) =>
      request<Encounter>(`/encounters/${id}/combatants`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    updateCombatant: (id: number, cid: number, body: Partial<Combatant>) =>
      request<Encounter>(`/encounters/${id}/combatants/${cid}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    removeCombatant: (id: number, cid: number) =>
      request<Encounter>(`/encounters/${id}/combatants/${cid}`, { method: 'DELETE' }),
    start: (id: number) => request<Encounter>(`/encounters/${id}/start`, { method: 'POST' }),
    end: (id: number) => request<Encounter>(`/encounters/${id}/end`, { method: 'POST' }),
    nextTurn: (id: number) => request<Encounter>(`/encounters/${id}/next-turn`, { method: 'POST' }),
    prevTurn: (id: number) => request<Encounter>(`/encounters/${id}/prev-turn`, { method: 'POST' }),
  },
}
