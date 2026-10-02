import { useEffect, useState } from 'react'
import { api, type BulkMonsterImport, type Monster, type Open5eBrowse, type Open5eSource } from '../api/client'
import MonsterDetail from './MonsterDetail'
import MonsterEditor from './MonsterEditor'
import { EXAMPLE_JSON, EXAMPLE_LIST_JSON, SchemaTable } from './StatblockSchema'

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
          <div className="table-scroll">
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
          </div>
          <div className="row">
            <button disabled={data.page <= 1} onClick={() => search(page - 1)}>← Prev</button>
            <button disabled={data.page >= data.num_pages} onClick={() => search(page + 1)}>Next →</button>
          </div>
        </>
      )}

      {previewSlug !== null && (
        <MonsterDetail open5eSlug={previewSlug} variant="panel" onClose={() => setPreviewSlug(null)} />
      )}
    </div>
  )
}

function Library() {
  const [monsters, setMonsters] = useState<Monster[]>([])
  const [error, setError] = useState<string | null>(null)
  const [detailId, setDetailId] = useState<number | null>(null)
  const [filter, setFilter] = useState('')
  // null = editor closed, 'new' = create, Monster = edit that statblock
  const [editing, setEditing] = useState<Monster | 'new' | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [pasting, setPasting] = useState(false)

  function load() { api.monsters.list().then(setMonsters).catch((e) => setError(e.message)) }
  useEffect(load, [])

  const hasImported = monsters.some((m) => !m.is_homebrew)

  async function refresh() {
    setRefreshing(true)
    setError(null)
    try {
      const res = await api.open5e.refresh()
      load()
      alert(`Refreshed ${res.updated.length} imported statblock${res.updated.length === 1 ? '' : 's'} from Open5e` +
        (res.failed.length ? ` · ${res.failed.length} failed` : ''))
    } catch (err) { setError((err as Error).message) }
    finally { setRefreshing(false) }
  }

  const q = filter.trim().toLowerCase()
  const shown = q
    ? monsters.filter((m) =>
        m.name.toLowerCase().includes(q) ||
        (m.type ?? '').toLowerCase().includes(q) ||
        String(m.challenge_rating ?? '').toLowerCase().includes(q))
    : monsters

  return (
    <div>
      <div className="row">
        <button className="run" onClick={() => setEditing('new')}>＋ Create statblock</button>
        <button className="ghost" onClick={() => setPasting(true)} title="Paste a JSON statblock (native or Open5e shape)">📋 Paste JSON</button>
        <span className="muted">Build a custom NPC or boss — full stats, attacks, traits, legendary actions.</span>
        {hasImported && (
          <button className="ghost" disabled={refreshing} onClick={refresh} title="Re-fetch imported statblocks from Open5e (defenses, senses, reactions, legendary actions)">
            {refreshing ? 'Refreshing…' : '⟳ Refresh imported'}
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}
      {monsters.length === 0 && <p className="muted">Library empty. Import from Open5e or create a statblock.</p>}

      {monsters.length > 0 && (
        <div className="row filters">
          <input placeholder="Filter library… (name, type, CR)" value={filter} onChange={(e) => setFilter(e.target.value)} />
          <span className="muted">{shown.length}/{monsters.length}</span>
        </div>
      )}

      <div className="table-scroll">
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
              <td className="row-actions">
                {m.is_homebrew && <button className="ghost" title="Edit" onClick={() => setEditing(m)}>✎</button>}
                <button className="danger" onClick={async () => { if (confirm(`Delete "${m.name}"?`)) { await api.monsters.remove(m.id); load() } }}>✕</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>

      {pasting && <PasteJson onClose={() => setPasting(false)} onSaved={() => { setPasting(false); load() }} />}
      {detailId !== null && <MonsterDetail monsterId={detailId} variant="panel" onClose={() => setDetailId(null)} />}
      {editing !== null && (
        <MonsterEditor
          monster={editing === 'new' ? undefined : editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load() }}
        />
      )}
    </div>
  )
}

/** A list, or an object wrapping one (`results` as on an Open5e page, or `monsters`). */
function isMonsterList(v: unknown): boolean {
  if (Array.isArray(v)) return true
  if (v && typeof v === 'object') {
    const o = v as Record<string, unknown>
    return Array.isArray(o.results) || Array.isArray(o.monsters)
  }
  return false
}

function PasteJson({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [help, setHelp] = useState<'fields' | 'example' | null>(null)
  const [result, setResult] = useState<BulkMonsterImport | null>(null)

  async function save() {
    setError(null)
    setResult(null)
    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch {
      setError('Invalid JSON. Check for a stray comma or a missing quote.')
      return
    }
    setBusy(true)
    try {
      if (isMonsterList(parsed)) {
        const r = await api.monsters.importJsonBulk(parsed)
        if (r.failed.length === 0) {
          onSaved()
          alert(`Added ${r.imported.length} monster${r.imported.length === 1 ? '' : 's'} to your library.`)
        } else {
          // keep the dialog open so the failures can be read and fixed
          setResult(r)
        }
      } else {
        const m = await api.monsters.importJson(parsed)
        onSaved()
        alert(`Added "${m.name}" to your library.`)
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  function applyExample(example: string) {
    setText(example)
    setHelp(null)
  }

  // after a partial import, closing must still refresh the library
  const close = result && result.imported.length > 0 ? onSaved : onClose

  return (
    <div className="modal-backdrop" onClick={close}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={close}>✕</button>
        <h2>
          Paste JSON statblocks{' '}
          <button
            className="ghost help-btn"
            title="Show the JSON format"
            aria-label="Show the JSON format"
            onClick={() => setHelp((h) => (h ? null : 'fields'))}
          >?</button>
        </h2>
        <p className="muted">
          Paste one monster as a JSON object, or several as a list. Both this app's shape and
          Open5e statblocks work, including a whole Open5e page (<code>{'{"results": [...]}'}</code>).
          Up to 500 at once. They're saved as homebrew.
        </p>
        {help && (
          <div className="json-help">
            <div className="row">
              <button className={help === 'fields' ? 'active' : ''} onClick={() => setHelp('fields')}>Fields</button>
              <button className={help === 'example' ? 'active' : ''} onClick={() => setHelp('example')}>Examples</button>
            </div>
            {help === 'fields' ? (
              <SchemaTable />
            ) : (
              <>
                <p className="muted">
                  One monster:
                  <button className="link-strong" onClick={() => applyExample(EXAMPLE_JSON)}>Use this</button>
                </p>
                <pre className="json-example"><code>{EXAMPLE_JSON}</code></pre>
                <p className="muted">
                  Several monsters:
                  <button className="link-strong" onClick={() => applyExample(EXAMPLE_LIST_JSON)}>Use this</button>
                </p>
                <pre className="json-example"><code>{EXAMPLE_LIST_JSON}</code></pre>
              </>
            )}
          </div>
        )}
        <textarea
          rows={16}
          spellCheck={false}
          placeholder='{ "name": "Goblin Boss", ... }   or   [ { "name": "Goblin" }, { "name": "Wolf" } ]'
          value={text}
          onChange={(e) => setText(e.target.value)}
          style={{ width: '100%', fontFamily: 'monospace' }}
        />
        {error && <p className="error">{error}</p>}
        {result && (
          <div className="bulk-result">
            <p>
              Added <strong>{result.imported.length}</strong>, failed <strong>{result.failed.length}</strong>.
              {result.imported.length > 0 && <> The added ones are already in your library.</>}
            </p>
            <ul>
              {result.failed.map((f) => (
                <li key={f.index}>
                  <strong>#{f.index + 1}{f.name ? ` ${f.name}` : ''}</strong>: <span className="error">{f.error}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="row">
          <button className="run" disabled={busy || !text.trim()} onClick={save}>
            {busy ? 'Adding…' : 'Add to library'}
          </button>
          <button className="ghost" onClick={close}>{result ? 'Close' : 'Cancel'}</button>
        </div>
      </div>
    </div>
  )
}
