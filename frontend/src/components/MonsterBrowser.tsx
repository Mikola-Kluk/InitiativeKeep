import { useEffect, useState } from 'react'
import { api, type Monster, type Open5eBrowse, type Open5eSource } from '../api/client'
import MonsterDetail from './MonsterDetail'

export default function MonsterBrowser() {
  const [tab, setTab] = useState<'open5e' | 'library'>('open5e')
  return (
    <section>
      <div className="row">
        <button className={tab === 'open5e' ? 'active' : ''} onClick={() => setTab('open5e')}>Open5e (3200+)</button>
        <button className={tab === 'library' ? 'active' : ''} onClick={() => setTab('library')}>My Library</button>
      </div>
      {tab === 'open5e' ? <Open5eBrowser /> : <Library />}
    </section>
  )
}

function Open5eBrowser() {
  const [q, setQ] = useState('')
  const [cr, setCr] = useState('')
  const [type, setType] = useState('')
  const [document, setDocument] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<Open5eBrowse | null>(null)
  const [sources, setSources] = useState<Open5eSource[]>([])
  const [imported, setImported] = useState<Record<string, 'ok' | 'busy'>>({})
  const [previewSlug, setPreviewSlug] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { api.open5e.sources().then(setSources).catch(() => {}) }, [])

  function search(p = 1) {
    setPage(p)
    api.open5e.browse({ q, cr, type, document, page: p }).then(setData).catch((e) => setError(e.message))
  }

  useEffect(() => { search(1) /* initial */ }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function imp(slug: string) {
    setImported((s) => ({ ...s, [slug]: 'busy' }))
    try {
      await api.open5e.importOne(slug)
      setImported((s) => ({ ...s, [slug]: 'ok' }))
    } catch (e) {
      setError((e as Error).message)
      setImported((s) => { const n = { ...s }; delete n[slug]; return n })
    }
  }

  return (
    <div>
      <form className="row filters" onSubmit={(e) => { e.preventDefault(); search(1) }}>
        <input placeholder="Search name…" value={q} onChange={(e) => setQ(e.target.value)} />
        <input placeholder="CR (e.g. 1, 1/4)" value={cr} onChange={(e) => setCr(e.target.value)} style={{ width: 110 }} />
        <input placeholder="Type (e.g. dragon)" value={type} onChange={(e) => setType(e.target.value)} />
        <select value={document} onChange={(e) => setDocument(e.target.value)}>
          <option value="">All sources</option>
          {sources.map((s) => <option key={s.slug} value={s.slug}>{s.name ?? s.slug}</option>)}
        </select>
        <button type="submit">Search</button>
      </form>

      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <p className="muted">{data.count} results · page {data.page}/{data.num_pages}</p>
          <table className="grid">
            <thead>
              <tr><th>Name</th><th>Type</th><th>CR</th><th>HP</th><th>Source</th><th></th></tr>
            </thead>
            <tbody>
              {data.results.map((m) => (
                <tr key={m.slug}>
                  <td><button className="link-strong name-btn" onClick={() => setPreviewSlug(m.slug)}>{m.name}</button></td>
                  <td>{m.type}</td>
                  <td>{m.challenge_rating}</td>
                  <td>{m.hit_points}</td>
                  <td className="muted">{m.document}</td>
                  <td>
                    <button
                      disabled={imported[m.slug] === 'busy' || imported[m.slug] === 'ok'}
                      onClick={() => imp(m.slug)}
                    >
                      {imported[m.slug] === 'ok' ? '✓ Imported' : imported[m.slug] === 'busy' ? '…' : 'Import'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="row">
            <button disabled={data.page <= 1} onClick={() => search(page - 1)}>← Prev</button>
            <button disabled={data.page >= data.num_pages} onClick={() => search(page + 1)}>Next →</button>
          </div>
        </>
      )}

      {previewSlug !== null && (
        <MonsterDetail open5eSlug={previewSlug} onClose={() => setPreviewSlug(null)} />
      )}
    </div>
  )
}

function Library() {
  const [monsters, setMonsters] = useState<Monster[]>([])
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [hp, setHp] = useState('')
  const [ac, setAc] = useState('')
  const [detailId, setDetailId] = useState<number | null>(null)
  const [filter, setFilter] = useState('')

  function load() { api.monsters.list().then(setMonsters).catch((e) => setError(e.message)) }
  useEffect(load, [])

  const q = filter.trim().toLowerCase()
  const shown = q
    ? monsters.filter((m) =>
        m.name.toLowerCase().includes(q) ||
        (m.type ?? '').toLowerCase().includes(q) ||
        String(m.challenge_rating ?? '').toLowerCase().includes(q))
    : monsters

  async function create(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    try {
      await api.monsters.create({
        name: name.trim(),
        hit_points: hp ? Number(hp) : 1,
        armor_class: ac ? Number(ac) : 10,
      })
      setName(''); setHp(''); setAc(''); load()
    } catch (err) { setError((err as Error).message) }
  }

  return (
    <div>
      <form onSubmit={create} className="row">
        <input placeholder="Homebrew name" value={name} onChange={(e) => setName(e.target.value)} />
        <input type="number" placeholder="HP" value={hp} onChange={(e) => setHp(e.target.value)} style={{ width: 70 }} />
        <input type="number" placeholder="AC" value={ac} onChange={(e) => setAc(e.target.value)} style={{ width: 70 }} />
        <button type="submit">+ Add homebrew</button>
      </form>

      {error && <p className="error">{error}</p>}
      {monsters.length === 0 && <p className="muted">Library empty. Import from Open5e or add homebrew.</p>}

      {monsters.length > 0 && (
        <div className="row filters">
          <input placeholder="Filter library… (name, type, CR)" value={filter} onChange={(e) => setFilter(e.target.value)} />
          <span className="muted">{shown.length}/{monsters.length}</span>
        </div>
      )}

      <table className="grid">
        <thead><tr><th>Name</th><th>Type</th><th>CR</th><th>HP</th><th>AC</th><th>Source</th><th></th></tr></thead>
        <tbody>
          {shown.map((m) => (
            <tr key={m.id}>
              <td><button className="link-strong name-btn" onClick={() => setDetailId(m.id)}>{m.name}</button></td>
              <td>{m.type}</td>
              <td>{m.challenge_rating}</td>
              <td>{m.hit_points}</td>
              <td>{m.armor_class}</td>
              <td className="muted">{m.is_homebrew ? 'homebrew' : m.slug}</td>
              <td>
                <button className="danger" onClick={async () => { await api.monsters.remove(m.id); load() }}>✕</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {detailId !== null && <MonsterDetail monsterId={detailId} onClose={() => setDetailId(null)} />}
    </div>
  )
}
