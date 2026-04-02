import { useState, useEffect } from 'react'
import './App.css'

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/analyze').replace('/analyze', '')

function App() {
  const [restaurantName, setRestaurantName] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  // Pre-warm the Render backend the moment the page loads.
  // Render spins down after inactivity — this silent ping wakes it up
  // while the user is still reading the page and typing their restaurant name.
  useEffect(() => {
    fetch(`${BASE_URL}/ping`).catch(() => {/* silent — just warming the server */})
  }, [])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!restaurantName.trim()) return

    setLoading(true)
    setError(null)
    setResults(null)

    const payload = {
      restaurant_name: restaurantName,
      location: 'Oregon',
      profiles: [
        { name: 'MSG Scanner', restrictions: ['Strict MSG Detection (All Forms & Hidden Aliases)'] }
      ]
    }

    const doFetch = () => fetch(`${BASE_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    try {
      let response = await doFetch()

      // If server returned an error (e.g. still waking from cold-start), retry once after 3s
      if (!response.ok) {
        await new Promise(r => setTimeout(r, 3000))
        response = await doFetch()
      }

      if (!response.ok) throw new Error('Analysis failed. Please try again.')
      setResults(await response.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getDishClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'safe':   return 'dish-safe'
      case 'unsafe': return 'dish-unsafe'
      default:       return 'dish-uncertain'
    }
  }

  const getBadgeClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'safe':   return 'status-badge-safe'
      case 'unsafe': return 'status-badge-unsafe'
      default:       return 'status-badge-uncertain'
    }
  }

  const safeDishes    = results?.results?.filter(d => d.status.startsWith('SAFE'))    || []
  const uncertainDishes = results?.results?.filter(d => d.status.includes('UNCERTAIN'))   || []
  const unsafeDishes  = results?.results?.filter(d => d.status.includes('UNSAFE'))    || []

  const renderDishCard = (dish, key) => {
    // Determine if we have ingredient data
    const hasIngredients = Array.isArray(dish.ingredients) && dish.ingredients.length > 0;
    const isSpoonacular = dish.ingredient_source === 'SPOONACULAR_DB';
    const isPerplexity = dish.ingredient_source === 'PERPLEXITY_LIVE_SCRAPE';
    
    // UI badge configuration based on layer
    let badgeText = '⚙️ Synthetic Commercial Formulation';
    let badgeColor = 'var(--brand-sage)'; // Orange/Gray
    
    if (isSpoonacular) {
      badgeText = '🟢 Spoonacular Database Verification';
      badgeColor = 'var(--brand-emerald)';
    } else if (isPerplexity) {
      badgeText = '🔵 Perplexity Live-Web Verification';
      badgeColor = '#3b82f6'; // Bright blue
    }
    
    return (
      <div key={key} className={`glass-card dish-card ${getDishClass(dish.status)}`}>
        <div className="dish-header">
          <h3 className="dish-name">{dish.dish_name}</h3>
          <span className={`dish-status ${getBadgeClass(dish.status)}`}>
            {dish.status}
          </span>
        </div>
        
        {dish.migraine_reported && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#ef4444',
            padding: '0.5rem 0.8rem',
            borderRadius: '6px',
            fontSize: '0.85rem',
            fontWeight: '600',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <span style={{fontSize: '1.1rem'}}>🤕</span> User Review Warning: Customers report migraines with this dish.
          </div>
        )}

        <div className="research-log-box">
          <div className="log-header">🛡️ AI MATRIX LOG</div>
          
          {hasIngredients ? (
            <div className="verified-ingredients" style={{ marginBottom: '1rem', paddingBottom: '0.8rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <strong style={{ display: 'block', fontSize: '0.85rem', color: badgeColor, letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                {badgeText}
              </strong>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {dish.ingredients.map((ing, i) => {
                  const isFlagged = dish.flagged_by && dish.flagged_by.some(f => ing.toLowerCase().includes(f.toLowerCase())) || 
                                    ing.toLowerCase().includes('flavor') || ing.toLowerCase().includes('carrageenan') || ing.toLowerCase().includes('maltodextrin');
                  return (
                    <span key={i} style={{ 
                      background: isFlagged ? 'rgba(235, 174, 52, 0.15)' : 'rgba(255,255,255,0.1)', 
                      border: isFlagged ? '1px solid rgba(235, 174, 52, 0.3)' : '1px solid transparent',
                      color: isFlagged ? '#ebae34' : 'inherit',
                      padding: '0.2rem 0.6rem', 
                      borderRadius: '4px', 
                      fontSize: '0.85rem' 
                    }}>
                      {ing}
                    </span>
                  );
                })}
              </div>
            </div>
          ) : null}

          <p className="log-content">{dish.culinary_inference || dish.research_log || dish.reasoning}</p>
        </div>

        {dish.server_question && dish.server_question !== 'None' && dish.server_question !== 'N/A' && dish.server_question.length > 5 && (
          <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(235, 174, 52, 0.1)', border: '1px solid rgba(235, 174, 52, 0.3)', borderRadius: '8px', boxShadow: '0 4px 15px rgba(235,174,52,0.05)' }}>
            <div style={{ color: 'var(--brand-amber)', fontWeight: 'bold', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              <span>🗣️</span> READ THIS TO YOUR SERVER:
            </div>
            <p style={{ color: 'var(--text-main)', fontSize: '0.95rem', fontStyle: 'italic', margin: 0, lineHeight: '1.4' }}>
              "{dish.server_question}"
            </p>
          </div>
        )}

        {dish.confidence && (
          <div className="confidence-tag">
            {dish.confidence === 'HIGH' ? '🎯' : '⚠️'} Confidence: {dish.confidence}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="container">
      <header className="header">
        <h1>Additive Detective</h1>
        <div className="header-badge">Universal Scanning Engine</div>
      </header>

      <main>
        <div className="glass-card search-form">
          <form onSubmit={handleSearch}>
            <div className="input-group">
              <div className="section-label">Search Restaurant or Grocery Brand</div>
              <input
                type="text"
                className="search-input"
                placeholder="Search anything..."
                value={restaurantName}
                onChange={e => setRestaurantName(e.target.value)}
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

        {/* Loading State */}
        {loading && (
          <div className="loading-skeleton">
            <h3>Gathering Menu Context &amp; Reasoning...</h3>
            <p style={{ fontSize: '0.9rem' }}>Checking ingredients against your restrictions</p>
          </div>
        )}

        {/* Results */}
        {results && !loading && (
          <div style={{ marginTop: '2rem' }}>

            {/* Telemetry Dashboard */}
            {results.telemetry && (
              <div className="telemetry-dashboard glass-card">
                <div className="telemetry-title">⚡ Deep Scrape Intelligence Protocol</div>
                <div className="telemetry-metrics">
                  <div className="metric">
                    <span className="metric-icon">🌐</span>
                    <strong>{results.telemetry.urls_crawled || 0}</strong> Local URLs Crawled
                  </div>
                  <div className="metric">
                    <span className="metric-icon">📄</span>
                    <strong>{results.telemetry.chars_scraped ? Math.round(results.telemetry.chars_scraped / 5).toLocaleString() : 0}</strong> Words of Review Data Scanned
                  </div>
                  <div className="metric" style={{ borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: '1rem' }}>
                    <span className="metric-icon">🧪</span>
                    <strong>{results.telemetry.chemicals_checked || 32}</strong> FDA Chemical Loopholes Checked
                  </div>
                </div>
              </div>
            )}

            {/* Restaurant Summary */}
            <div className="results-header glass-card">
              <h2>{results.restaurant?.name}</h2>
              <p className="context">{results.restaurant?.search_context}</p>
            </div>

            <div className="dishes-feed">
              {/* ✅ Safe Options */}
              {safeDishes.length > 0 && (
                <div className="dish-tier">
                  <h3 className="tier-header" style={{ color: 'var(--brand-emerald)', marginBottom: '1rem', borderBottom: '2px solid var(--brand-emerald)', paddingBottom: '0.5rem' }}>
                    ✅ Top Safe Recommendations
                  </h3>
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

              {/* 💬 Proceed With Caution */}
              {uncertainDishes.length > 0 && (
                <div className="dish-tier" style={{ marginTop: '2rem' }}>
                  <h3 className="tier-header" style={{ color: 'var(--brand-amber)', marginBottom: '1rem', borderBottom: '2px solid var(--brand-amber)', paddingBottom: '0.5rem' }}>
                    💬 Proceed With Caution
                  </h3>
                  {uncertainDishes.map((dish, idx) => renderDishCard(dish, `unc-${idx}`))}
                </div>
              )}

              {/* ⛔ Unsafe Items */}
              {unsafeDishes.length > 0 && (
                <div className="dish-tier" style={{ marginTop: '2.5rem' }}>
                  <h3 className="tier-header" style={{ color: 'var(--unsafe)', marginBottom: '1rem', borderBottom: '2px solid var(--unsafe)', paddingBottom: '0.5rem' }}>
                    ⛔ Unsafe Items
                  </h3>
                  <div className="unsafe-condensed-list glass-card">
                    {unsafeDishes.map((dish, idx) => (
                      <div className="unsafe-list-item" key={`unsf-${idx}`}>
                        <div className="unsafe-name" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                          <strong>{dish.dish_name}</strong>
                          {dish.migraine_reported && (
                            <span style={{ 
                              background: '#ef4444', 
                              color: '#fff', 
                              fontSize: '0.75rem', 
                              padding: '2px 8px', 
                              borderRadius: '4px', 
                              fontWeight: 'bold',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}>
                              🤕 Migraine Reports
                            </span>
                          )}
                        </div>
                        <div className="unsafe-reason">{dish.culinary_inference || dish.research_log || dish.reasoning}</div>
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
