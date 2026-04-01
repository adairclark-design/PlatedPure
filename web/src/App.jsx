import { useState, useEffect } from 'react'
import './App.css'

// Full allergen/diet restriction list
const RESTRICTIONS = [
  { id: 'gluten',    label: 'Gluten-Free',      emoji: '🌾' },
  { id: 'msg',       label: 'MSG-Free',          emoji: '🧪' },
  { id: 'peanuts',   label: 'Peanut-Free',       emoji: '🥜' },
  { id: 'tree_nuts', label: 'Tree Nut-Free',     emoji: '🌰' },
  { id: 'dairy',     label: 'Dairy-Free',        emoji: '🥛' },
  { id: 'eggs',      label: 'Egg-Free',          emoji: '🥚' },
  { id: 'shellfish', label: 'Shellfish-Free',    emoji: '🦞' },
  { id: 'fish',      label: 'Fish-Free',         emoji: '🐟' },
  { id: 'soy',       label: 'Soy-Free',          emoji: '🫘' },
  { id: 'keto',      label: 'Keto',              emoji: '🥩' },
  { id: 'vegan',     label: 'Vegan',             emoji: '🌿' },
  { id: 'vegetarian',label: 'Vegetarian',        emoji: '🥦' },
]

function App() {
  const [restaurantName, setRestaurantName] = useState('')
  const [location, setLocation] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [hasAcceptedTOS, setHasAcceptedTOS] = useState(true) // Default true to avoid flash, updated in effect

  useEffect(() => {
    const accepted = localStorage.getItem('platedpure_tos_accepted')
    if (!accepted) {
      setHasAcceptedTOS(false)
    }
  }, [])

  const handleAcceptTOS = () => {
    localStorage.setItem('platedpure_tos_accepted', 'true')
    setHasAcceptedTOS(true)
  }

  const toggleRestriction = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!restaurantName || !location || selected.size === 0) return

    setLoading(true)
    setError(null)
    setResults(null)

    // Build restriction labels from selected IDs
    const activeRestrictions = RESTRICTIONS
      .filter(r => selected.has(r.id))
      .map(r => r.label)

    const payload = {
      restaurant_name: restaurantName,
      location: location,
      profiles: [
        { name: 'You', restrictions: activeRestrictions }
      ]
    }

    try {
      const API_ENDPOINT = import.meta.env.VITE_API_URL || 'http://localhost:8000/analyze'
      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!response.ok) throw new Error('Analysis failed. Please try again.')
      setResults(await response.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getDishClass = (status) => {
    switch(status?.toLowerCase()) {
      case 'safe':   return 'dish-safe'
      case 'unsafe': return 'dish-unsafe'
      default:       return 'dish-unknown'
    }
  }

  const getBadgeClass = (status) => {
    switch(status?.toLowerCase()) {
      case 'safe':   return 'status-badge-safe'
      case 'unsafe': return 'status-badge-unsafe'
      default:       return 'status-badge-unknown'
    }
  }

  // Pre-filter results if they exist
  const safeDishes = results?.results?.filter(d => d.status.startsWith('SAFE')) || []
  const unknownDishes = results?.results?.filter(d => d.status.includes('UNKNOWN')) || []
  const unsafeDishes = results?.results?.filter(d => d.status.includes('UNSAFE')) || []

  // Helper component to dry up the Safe/Unknown rendering logic
  const renderDishCard = (dish, idx) => (
    <div key={idx} className={`glass-card dish-card ${getDishClass(dish.status)}`}>
      <div className="dish-header">
        <h3 className="dish-name">{dish.dish_name}</h3>
        <span className={`dish-status ${getBadgeClass(dish.status)}`}>
          {dish.status}
        </span>
      </div>
      <p className="dish-reasoning">{dish.reasoning}</p>
      
      {dish.validation_questions && dish.validation_questions.length > 0 && (
        <div className="server-script-box">
          <div className="server-script-header">
            💬 Ask Your Server
          </div>
          <ul className="server-script-list">
            {dish.validation_questions.map((q, qIdx) => (
              <li key={qIdx}>{q}</li>
            ))}
          </ul>
        </div>
      )}

      {dish.confidence && (
        <div className="confidence-tag">
          {dish.confidence === 'HIGH' ? '🎯' : '⚠️'} Confidence: {dish.confidence}
        </div>
      )}
    </div>
  )

  return (
    <div className="container">
      {/* ── Liability Modal ── */}
      {!hasAcceptedTOS && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-icon">⚠️</div>
            <h2 className="modal-title">Medical Disclaimer</h2>
            <div className="modal-text">
              <p style={{ marginBottom: '1rem' }}>
                PlatedPure is an <strong>AI-powered investigative tool</strong>, NOT a medical advisor or safety guarantor.
              </p>
              <p style={{ marginBottom: '1rem' }}>
                Because restaurants frequently change recipes, use third-party sauces with hidden ingredients (like yeast extract for MSG), and have cross-contamination risks, <strong>AI analysis alone is never 100% safe.</strong>
              </p>
              <p>
                You must <strong>ALWAYS</strong> use the provided "Server Scripts" to verify hidden ingredients with the restaurant staff before eating.
              </p>
            </div>
            <button className="accept-btn" onClick={handleAcceptTOS}>
              I Understand & Agree
            </button>
          </div>
        </div>
      )}

      <header className="header">
        <h1>PlatedPure</h1>
        <div className="header-badge">AI-Powered Allergen &amp; Additive Navigation</div>
      </header>

      <main>
        <div className="glass-card search-form">
          <form onSubmit={handleSearch}>
            {/* Allergen Selector */}
            <div className="input-group">
              <div className="section-label">What Are We Avoiding?</div>
              <p className="selector-hint">Select all dietary restrictions that apply</p>
              <div className="restriction-grid">
                {RESTRICTIONS.map(r => (
                  <button
                    key={r.id}
                    type="button"
                    className={`restriction-tag ${selected.has(r.id) ? 'active' : ''}`}
                    onClick={() => toggleRestriction(r.id)}
                  >
                    <span className="tag-emoji">{r.emoji}</span>
                    <span className="tag-label">{r.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Restaurant Fields */}
            <div className="section-divider" />
            <div className="input-group">
              <div className="section-label">Restaurant Name</div>
              <input
                type="text"
                className="search-input"
                placeholder="e.g. Olive Garden"
                value={restaurantName}
                onChange={e => setRestaurantName(e.target.value)}
                required
              />
            </div>

            <div className="input-group">
              <div className="section-label">City / Location</div>
              <input
                type="text"
                className="search-input"
                placeholder="e.g. Pasadena, CA"
                value={location}
                onChange={e => setLocation(e.target.value)}
                required
              />
            </div>

            <button
              type="submit"
              className="submit-btn"
              disabled={loading || selected.size === 0}
            >
              {loading ? 'AI scanning menu...' : 'Analyze Menu'}
            </button>

            {selected.size === 0 && !loading && (
              <p className="hint-text">👆 Select at least one restriction above to get started</p>
            )}
          </form>

          {error && <div className="error-msg">{error}</div>}
        </div>

        {/* Loading */}
        {loading && (
          <div className="loading-skeleton">
            <h3>Gathering Menu Context &amp; Reasoning...</h3>
            <p style={{ fontSize: '0.9rem' }}>Checking ingredients against your restrictions</p>
          </div>
        )}

        {/* Results */}
        {results && !loading && (
          <div style={{ marginTop: '2rem' }}>
            <div className="results-header glass-card">
              <h2>{results.restaurant?.name}</h2>
              <p className="context">{results.restaurant?.search_context}</p>
            </div>

            <div className="dishes-feed">
              {/* ✅ Safe Options */}
              {safeDishes.length > 0 && (
                <div className="dish-tier">
                  <h3 className="tier-header" style={{ color: 'var(--brand-emerald)', marginBottom: '1rem', borderBottom: '2px solid var(--brand-emerald)', paddingBottom: '0.5rem' }}>✅ Top Safe Recommendations</h3>
                  {safeDishes.map((dish, idx) => renderDishCard(dish, `safe-${idx}`))}
                </div>
              )}

              {/* Empty Safe State */}
              {safeDishes.length === 0 && (
                <div className="glass-card dish-card dish-unsafe" style={{ textAlign: 'center', marginBottom: '2rem' }}>
                  <h3 style={{ color: 'var(--unsafe)', marginBottom: '0.5rem' }}>No Guaranteed Safe Items Found</h3>
                  <p style={{ color: 'var(--text-light)', fontSize: '0.9rem' }}>The AI could not confidently identify any strictly safe dishes. Please review the items below cautiously.</p>
                </div>
              )}

              {/* 💬 Unknown / Conditionals */}
              {unknownDishes.length > 0 && (
                <div className="dish-tier" style={{ marginTop: '2rem' }}>
                  <h3 className="tier-header" style={{ color: 'var(--brand-amber)', marginBottom: '1rem', borderBottom: '2px solid var(--brand-amber)', paddingBottom: '0.5rem' }}>💬 Proceed With Caution</h3>
                  {unknownDishes.map((dish, idx) => renderDishCard(dish, `unk-${idx}`))}
                </div>
              )}

              {/* ⛔ Unsafe Items (Condensed) */}
              {unsafeDishes.length > 0 && (
                <div className="dish-tier" style={{ marginTop: '2.5rem' }}>
                  <h3 className="tier-header" style={{ color: 'var(--unsafe)', marginBottom: '1rem', borderBottom: '2px solid var(--unsafe)', paddingBottom: '0.5rem' }}>⛔ Unsafe Items</h3>
                  <div className="unsafe-condensed-list glass-card">
                    {unsafeDishes.map((dish, idx) => (
                      <div className="unsafe-list-item" key={`unsf-${idx}`}>
                        <div className="unsafe-name"><strong>{dish.dish_name}</strong></div>
                        <div className="unsafe-reason">{dish.reasoning}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="disclaimer">
              <strong>⚠️ MEDICAL DISCLAIMER:</strong> This AI analysis is an investigative guide, not a guarantee. Menus, third-party sauces, and protocols change constantly. <strong>Always physically verify with your server</strong> using the provided questions before consuming any food.
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
