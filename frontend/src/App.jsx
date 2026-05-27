import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Compass,
  Search,
  Cpu,
  ExternalLink,
  Copy,
  Check,
  Sun,
  Moon,
  RefreshCw,
  AlertTriangle,
  Flame,
  Image,
  Layers,
  Sparkles,
  ArrowRight,
  TrendingUp
} from 'lucide-react'

// Curated preset example URLs from the benchmark dataset
const PRESETS = [
  {
    id: 'ftb',
    subreddit: 'r/feedthebeast',
    title: 'Minecraft Farmhouse & Windmill',
    url: 'https://www.reddit.com/r/feedthebeast/comments/1tnjexc/farmhouse_again/'
  },
  {
    id: 'boys',
    subreddit: 'r/TheBoys',
    title: 'Season Finale Leak & Spoilers',
    url: 'https://www.reddit.com/r/TheBoys/comments/1tbauua/the_boys_season_finale_spoiler/'
  },
  {
    id: 'tech',
    subreddit: 'r/technology',
    title: 'Erin Brockovich Data Center Map',
    url: 'https://www.reddit.com/r/technology/comments/1toe7m2/erin_brockovich_launches_map_of_over_4200_data/'
  },
  {
    id: 'nba',
    subreddit: 'r/nba',
    title: 'NYC Mayor on Knicks Finals sweep',
    url: 'https://www.reddit.com/r/nba/comments/1todljl/nyc_mayor_on_knicks_making_the_finals_you_cant/'
  },
  {
    id: 'ow',
    subreddit: 'r/Overwatch',
    title: 'Overwatch Update (Winton memes)',
    url: 'https://www.reddit.com/r/Overwatch/comments/1tofrzh/new_overwatch_update/'
  },
  {
    id: 'cringe',
    subreddit: 'r/TikTokCringe',
    title: 'Epstein Files NYC Pop-up exhibit',
    url: 'https://www.reddit.com/r/TikTokCringe/comments/1tofk98/a_nyc_popup_just_opened_displaying_all_35_million/'
  }
]

// Animated agent loading phases
const LOADING_STEPS = [
  { text: 'Extracting Reddit metadata, body content & top comments...', duration: 3000 },
  { text: 'Retrieving external web context & search queries...', duration: 8000 },
  { text: 'Generating text embeddings & scoring RAG search results...', duration: 8000 },
  { text: 'Synthesizing final structured, objective context...', duration: 15000 }
]

function App() {
  const [url, setUrl] = useState('')
  const [model, setModel] = useState('gpt-4o-mini')
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [copied, setCopied] = useState(false)
  const [theme, setTheme] = useState(() => {
    // Sync with system preferences
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme')
      if (saved) return saved
      return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
    }
    return 'dark'
  })
  const [latency, setLatency] = useState(0)

  // Sync theme to root HTML element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  // Stepper state rotation logic
  useEffect(() => {
    let timer
    if (loading) {
      setCurrentStep(0)
      const runStep = (stepIdx) => {
        if (stepIdx >= LOADING_STEPS.length) return
        timer = setTimeout(() => {
          setCurrentStep(stepIdx + 1)
          runStep(stepIdx + 1)
        }, LOADING_STEPS[stepIdx].duration)
      }
      runStep(0)
    }
    return () => clearTimeout(timer)
  }, [loading])

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  const handlePresetClick = (presetUrl) => {
    setUrl(presetUrl)
    setError(null)
  }

  const handleCopy = () => {
    if (!result) return
    const textToCopy = result.explanation.map((bullet) => `• ${bullet}`).join('\n')
    navigator.clipboard.writeText(textToCopy).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)
    const startTime = performance.now()
    try {
      const backendPort = process.env.BACKEND_PORT || '8000'
      const response = await fetch(`http://localhost:${backendPort}/explain`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url.trim(), model })
      })

      if (!response.ok) {
        const errText = await response.text()
        let parsedErr
        try {
          parsedErr = JSON.parse(errText)
        } catch {
          parsedErr = { detail: errText }
        }
        throw new Error(parsedErr.detail || 'An error occurred while fetching explanation.')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message || 'Connection to the backend API failed.')
    } finally {
      const endTime = performance.now()
      setLatency(((endTime - startTime) / 1000).toFixed(2))
      setLoading(false)
    }
  }

  // Extract root domain name from URL for clean citations representation
  const cleanDomain = (urlStr) => {
    try {
      const hostname = new URL(urlStr).hostname
      return hostname.replace('www.', '')
    } catch {
      return urlStr
    }
  }

  // Helper to truncate very long URLs to prevent layout distortion, adding browser tooltip on hover
  const truncateUrl = (urlStr, maxLen = 45) => {
    if (urlStr.length <= maxLen) return urlStr
    return urlStr.substring(0, maxLen - 3) + '...'
  }

  return (
    <div className="app-container">
      {/* Brand Header */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">
            <Compass size={24} />
          </div>
          <h1>Reddit Context Agent</h1>
        </div>
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label="Toggle Theme"
        >
          {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </header>

      {/* Main Form */}
      <section className="main-card">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Reddit Post URL
            </label>
            <div className="input-container">
              <Search className="input-icon" size={20} />
              <input
                type="url"
                className="url-input"
                placeholder="https://www.reddit.com/r/subreddit/comments/..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={loading}
                required
              />
            </div>
          </div>

          <div className="controls-row">
            <div className="model-select-wrapper">
              <label htmlFor="model-select">LLM Model:</label>
              <select
                id="model-select"
                className="model-select"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                disabled={loading}
              >
                <option value="gpt-4o-mini">gpt-4o-mini (Faster)</option>
                <option value="gpt-4o">gpt-4o (More powerful)</option>
              </select>
            </div>

            <button type="submit" className="submit-btn" disabled={loading || !url}>
              {loading ? (
                <>
                  <RefreshCw className="spinner-circle" style={{ animation: 'rotate 1s linear infinite' }} size={18} />
                  Analyzing...
                </>
              ) : (
                <>
                  <Cpu size={18} />
                  Explain Post
                </>
              )}
            </button>
          </div>
        </form>

        {/* Preset Links */}
        {!loading && (
          <div className="presets-section">
            <h2 className="presets-title">Quick Test Presets</h2>
            <div className="presets-grid">
              {PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  className="preset-card"
                  onClick={() => handlePresetClick(preset.url)}
                >
                  <span className="preset-subreddit">{preset.subreddit}</span>
                  <span className="preset-title-text">{preset.title}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Loading Stepper state */}
      {loading && (
        <section className="loading-card">
          <div className="spinner-wrapper">
            <div className="spinner-glow" />
            <svg className="spinner-circle" viewBox="0 0 50 50">
              <circle
                cx="25"
                cy="25"
                r="20"
                fill="none"
                strokeWidth="4"
                stroke="var(--border-color)"
              />
              <path
                d="M 25 5 A 20 20 0 0 1 45 25"
                fill="none"
                strokeWidth="4"
              />
            </svg>
          </div>

          <div className="loading-steps">
            {LOADING_STEPS.map((step, idx) => {
              const isActive = idx === currentStep
              const isCompleted = idx < currentStep
              return (
                <div
                  key={idx}
                  className={`step-item ${isActive ? 'active' : ''} ${
                    isCompleted ? 'completed' : ''
                  }`}
                >
                  <div className="step-icon-wrapper">
                    {isCompleted ? (
                      <Check size={16} className="step-icon-wrapper completed" />
                    ) : (
                      <Sparkles
                        size={16}
                        className={`step-icon-wrapper ${isActive ? 'active' : ''}`}
                        style={isActive ? { animation: 'pulseBorder 1.5s infinite' } : {}}
                      />
                    )}
                  </div>
                  <span className="step-text">{step.text}</span>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Errors */}
      {error && (
        <section className="error-card">
          <div className="error-icon-wrapper">
            <AlertTriangle size={24} />
          </div>
          <div className="error-details">
            <h3>Extraction & Context Retrieval Failed</h3>
            <p>{error}</p>
            <button className="error-retry-btn" onClick={() => handleSubmit()}>
              Retry Request
            </button>
          </div>
        </section>
      )}

      {/* Result Panel */}
      {result && !loading && (
        <section className="result-card">
          <div className="result-header">
            <div className="result-info">
              <div className="result-meta">
                <span className="sub-badge">r/{result.subreddit || 'Reddit'}</span>
                <span className="latency-badge">🕒 {latency}s</span>
              </div>
              <h2 className="result-title">{result.title || 'Reddit Context Explanation'}</h2>
            </div>
            <div className="actions-row">
              <button className="action-btn" onClick={handleCopy}>
                {copied ? <Check size={16} style={{ color: 'var(--success)' }} /> : <Copy size={16} />}
                {copied ? 'Copied!' : 'Copy Explanation'}
              </button>
            </div>
          </div>

          {/* Multimodal Preview Image */}
          {result.image_url && (
            <div className="media-container">
              <img
                src={result.image_url}
                alt="Reddit multimodal content preview"
                className="media-image"
                onError={(e) => { e.target.style.display = 'none' }} // hide if image fails to load
              />
              <div className="media-overlay">
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Image size={14} /> Multimodal Media Context Ingested
                </span>
              </div>
            </div>
          )}

          {/* Details split */}
          <div className="columns-grid">
            {/* Left Column: Markdown Bullets */}
            <div className="column-section">
              <h3 className="column-title">
                <Layers size={18} style={{ color: 'var(--primary-accent)' }} />
                Synthesized Context Explanation
              </h3>
              <div className="explanation-content">
                <ul>
                  {result.explanation.map((bullet, idx) => (
                    <li key={idx}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{bullet}</ReactMarkdown>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Right Column: Citations Grid */}
            <div className="column-section">
              <h3 className="column-title">
                <TrendingUp size={18} style={{ color: 'var(--secondary-accent)' }} />
                Retrieved Source Citations
              </h3>
              <div className="citations-list">
                {result.citations && result.citations.length > 0 ? (
                  result.citations.map((citeUrl, idx) => {
                    const domain = cleanDomain(citeUrl)
                    const faviconUrl = `https://www.google.com/s2/favicons?sz=64&domain=${domain}`
                    return (
                      <a
                        key={idx}
                        href={citeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="citation-card"
                      >
                        <div className="favicon-wrapper">
                          <img
                            src={faviconUrl}
                            alt=""
                            className="favicon"
                            onError={(e) => {
                              e.target.src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%236b7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/></svg>'
                            }}
                          />
                        </div>
                        <div className="citation-info">
                          <span className="citation-domain">{domain}</span>
                          <span className="citation-url" title={citeUrl}>{truncateUrl(citeUrl, 45)}</span>
                        </div>
                        <ExternalLink size={14} className="citation-arrow" />
                      </a>
                    )
                  })
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                    No citations required/referenced.
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

export default App
