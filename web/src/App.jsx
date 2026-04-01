import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [restaurantName, setRestaurantName] = useState('')
  const [location, setLocation] = useState('')
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

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!restaurantName || !location) return

    setLoading(true)
    setError(null)
    setResults(null)

    const payload = {
      restaurant_name: restaurantName,
      location: location,
      profiles: [
        { name: 'MSG Scanner', restrictions: ['Strict MSG Detection (All Forms & Hidden Aliases)'] }
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
            <h2 className="modal-title">MSG Danger Protocol</h2>
            <div className="modal-text">
              <p style={{ marginBottom: '1rem' }}>
                PlatedPure is an <strong>Enterprise MSG-Sweeper</strong>, NOT a medical guarantor.
              </p>
              <p style={{ marginBottom: '1rem' }}>
                Because restaurants legally hide high-glutamate ingredients under deceptive names like <strong>"Yeast Extract"</strong> and <strong>"Natural Flavors"</strong>, AI analysis alone is never 100% safe.
              </p>
              <p>
                You must <strong>ALWAYS</strong> use the provided "Server Scripts" to verify sauce and rub sourcing with the restaurant staff before eating.
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
        <div className="header-badge">Enterprise MSG Detection Engine</div>
      </header>

      <main>
        <div className="glass-card search-form">
          <form onSubmit={handleSearch}>
            {/* Restaurant Fields */}
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
              disabled={loading}
            >
              {loading ? 'Executing MSG Sweep...' : 'Scan For Hidden MSG'}
            </button>
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
