// SPIKES post-call scorer (PATHOS_BUILD_SPEC.md §3.2, §7).
//
// Standalone, dependency-free module: takes a transcript string, asks an
// OpenAI-compatible chat API to grade it against the SPIKES protocol, and
// returns a validated "pagella" object. Uses the native `fetch`, so it runs
// both in Node (tests) and in the browser (the future dashboard).
//
// Provider-agnostic: defaults target Groq (free, OpenAI-compatible), but base
// URL, model, and key are all overridable via env vars or options — to switch
// back to OpenAI just change the env, not the code.
//   - key:      GROQ_API_KEY  (or LLM_API_KEY / OPENAI_API_KEY) — never hardcoded
//   - base URL: LLM_BASE_URL  (default https://api.groq.com/openai/v1)
//   - model:    LLM_MODEL     (default llama-3.3-70b-versatile)
import { SPIKES_SYSTEM_PROMPT } from './spikesPrompt.js'

const DEFAULT_BASE_URL = 'https://api.groq.com/openai/v1'
const DEFAULT_MODEL = 'llama-3.3-70b-versatile'
const DEFAULT_TIMEOUT_MS = 60_000
// Low temperature: grading should be as consistent/repeatable as possible.
const DEFAULT_TEMPERATURE = 0.2
// llama-3.3 is not a reasoning model, so the standard `max_tokens` applies. The
// pagella JSON is small; 2000 is ample. (For an OpenAI reasoning model you'd
// switch this to `max_completion_tokens` — see the body below.)
const DEFAULT_MAX_TOKENS = 2000

const VALID_STATES = ['RISPETTATA', 'PARZIALE', 'MANCATA']

// Typed error so callers (test runner, future UI) can branch on `code` and show
// an Italian message to the user.
export class SpikesScoreError extends Error {
  constructor(code, message, details) {
    super(message)
    this.name = 'SpikesScoreError'
    this.code = code
    this.details = details
  }
}

function resolveApiKey(explicit) {
  if (explicit) return explicit
  // Optional chaining keeps this safe in the browser, where `process` is undefined.
  const env = globalThis.process?.env
  return env?.LLM_API_KEY || env?.GROQ_API_KEY || env?.OPENAI_API_KEY || null
}

// Walk the string and return the first balanced {...} object, ignoring braces
// that live inside JSON string literals. Handles the "model wrapped the JSON in
// prose" case without a fragile regex.
function firstBalancedObject(text) {
  const start = text.indexOf('{')
  if (start === -1) return null
  let depth = 0
  let inString = false
  let escaped = false
  for (let i = start; i < text.length; i++) {
    const ch = text[i]
    if (inString) {
      if (escaped) escaped = false
      else if (ch === '\\') escaped = true
      else if (ch === '"') inString = false
      continue
    }
    if (ch === '"') inString = true
    else if (ch === '{') depth++
    else if (ch === '}') {
      depth--
      if (depth === 0) return text.slice(start, i + 1)
    }
  }
  return null
}

// Robustly pull a JSON object out of a model response that may include
// surrounding prose, a ```json fence, or trailing text. Kept as a fallback even
// though we request response_format: json_object.
export function extractJson(raw) {
  if (typeof raw !== 'string' || raw.trim() === '') {
    throw new SpikesScoreError('EMPTY_RESPONSE', 'Risposta del modello vuota.')
  }
  const text = raw.trim()

  // 1) Straight parse (the happy path with response_format: json_object).
  try {
    return JSON.parse(text)
  } catch {
    // fall through
  }

  // 2) Strip a ```json ... ``` (or ``` ... ```) fence and retry.
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/i)
  if (fenced) {
    try {
      return JSON.parse(fenced[1])
    } catch {
      // fall through
    }
  }

  // 3) Scan for the first balanced {...} object embedded in prose.
  const candidate = firstBalancedObject(text)
  if (candidate) {
    try {
      return JSON.parse(candidate)
    } catch {
      // fall through
    }
  }

  throw new SpikesScoreError(
    'BAD_JSON',
    'Impossibile estrarre un JSON valido dalla risposta del modello.',
    { raw },
  )
}

// Fallback score if the model omits/garbles punteggio_totale: average the 6
// phase states (RISPETTATA=1, PARZIALE=0.5, MANCATA=0) onto a 0-100 scale.
function deriveScore(fasi) {
  if (fasi.length === 0) return 0
  const weights = { RISPETTATA: 1, PARZIALE: 0.5, MANCATA: 0 }
  const sum = fasi.reduce((acc, f) => acc + (weights[f.stato] ?? 0), 0)
  return (sum / fasi.length) * 100
}

// Validate and normalize the raw parsed object into a stable pagella shape.
function normalizeResult(parsed) {
  if (!parsed || typeof parsed !== 'object' || !Array.isArray(parsed.fasi)) {
    throw new SpikesScoreError(
      'BAD_SHAPE',
      'Il JSON della pagella non ha il campo "fasi" atteso.',
      { parsed },
    )
  }

  const fasi = parsed.fasi.map((f, i) => ({
    step: typeof f?.step === 'string' ? f.step : `Fase ${i + 1}`,
    stato: VALID_STATES.includes(f?.stato) ? f.stato : 'MANCATA',
    nota: typeof f?.nota === 'string' ? f.nota : '',
  }))

  let total = Number(parsed.punteggio_totale)
  if (!Number.isFinite(total)) total = deriveScore(fasi)
  total = Math.max(0, Math.min(100, Math.round(total)))

  const sintesi = typeof parsed.sintesi === 'string' ? parsed.sintesi : ''

  return { fasi, punteggio_totale: total, sintesi }
}

/**
 * Score a transcript against the SPIKES protocol.
 *
 * @param {string} transcript - full conversation transcript.
 * @param {object} [options]
 * @param {string} [options.apiKey] - API key; defaults to GROQ_API_KEY / LLM_API_KEY / OPENAI_API_KEY env.
 * @param {string} [options.baseUrl] - API base URL; defaults to LLM_BASE_URL env or Groq.
 * @param {string} [options.model] - model id; defaults to LLM_MODEL env or "llama-3.3-70b-versatile".
 * @param {number} [options.timeoutMs] - request timeout; defaults to 60000.
 * @param {number} [options.temperature] - sampling temperature; defaults to 0.2.
 * @param {number} [options.maxTokens] - max completion tokens; defaults to 2000.
 * @param {Function} [options.fetch] - fetch impl (injectable for tests).
 * @returns {Promise<{fasi: Array, punteggio_totale: number, sintesi: string}>}
 * @throws {SpikesScoreError}
 */
export async function scoreSpikes(transcript, options = {}) {
  if (typeof transcript !== 'string' || transcript.trim().length < 10) {
    throw new SpikesScoreError('BAD_INPUT', 'Trascrizione mancante o troppo corta.')
  }

  const apiKey = resolveApiKey(options.apiKey)
  if (!apiKey) {
    throw new SpikesScoreError(
      'NO_API_KEY',
      "Chiave API non trovata: imposta GROQ_API_KEY (o LLM_API_KEY/OPENAI_API_KEY) nel .env o nell'ambiente, oppure passala in options.apiKey.",
    )
  }

  const env = globalThis.process?.env
  const baseUrl = (options.baseUrl || env?.LLM_BASE_URL || DEFAULT_BASE_URL).replace(/\/+$/, '')
  const model = options.model || env?.LLM_MODEL || DEFAULT_MODEL
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const temperature = options.temperature ?? DEFAULT_TEMPERATURE
  const maxTokens = options.maxTokens ?? DEFAULT_MAX_TOKENS
  const fetchImpl = options.fetch || globalThis.fetch
  if (typeof fetchImpl !== 'function') {
    throw new SpikesScoreError('NO_FETCH', 'fetch non disponibile in questo ambiente.')
  }

  const body = {
    model,
    messages: [
      { role: 'system', content: SPIKES_SYSTEM_PROMPT },
      { role: 'user', content: transcript },
    ],
    // JSON mode: the system prompt mentions "JSON", satisfying the API requirement.
    response_format: { type: 'json_object' },
    temperature,
    max_tokens: maxTokens,
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  let response
  try {
    response = await fetchImpl(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
  } catch (err) {
    if (err?.name === 'AbortError') {
      throw new SpikesScoreError('TIMEOUT', `Timeout dopo ${timeoutMs} ms in attesa del provider.`)
    }
    throw new SpikesScoreError('NETWORK', `Errore di rete verso il provider: ${err?.message ?? err}`, {
      cause: err,
    })
  } finally {
    clearTimeout(timer)
  }

  if (!response.ok) {
    let errText = ''
    try {
      errText = await response.text()
    } catch {
      // ignore
    }
    throw new SpikesScoreError(
      'HTTP_ERROR',
      `Il provider ha risposto ${response.status} ${response.statusText}.`,
      { status: response.status, body: errText.slice(0, 1000) },
    )
  }

  let data
  try {
    data = await response.json()
  } catch (err) {
    throw new SpikesScoreError('BAD_JSON', 'Risposta HTTP del provider non in formato JSON.', {
      cause: err,
    })
  }

  const content = data?.choices?.[0]?.message?.content
  const parsed = extractJson(content)
  return normalizeResult(parsed)
}
