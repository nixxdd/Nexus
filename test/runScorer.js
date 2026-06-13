// Manual test: run the SPIKES scorer on a good and a bad transcript and check
// it discriminates (high score for the good one, low for the bad one).
//
// Run with:  npm run test:scorer
// (reads OPENAI_API_KEY from a local .env if present, else from the environment)
import { scoreSpikes, SpikesScoreError } from '../src/lib/spikesScorer.js'
import { GOOD_TRANSCRIPT, BAD_TRANSCRIPT } from './transcripts.js'

function printPagella(label, result) {
  console.log(`\n===== ${label} =====`)
  console.log(`Punteggio totale: ${result.punteggio_totale}/100`)
  for (const f of result.fasi) {
    console.log(`  ${f.step.padEnd(16)} ${f.stato.padEnd(11)} ${f.nota}`)
  }
  console.log(`Sintesi: ${result.sintesi}`)
}

function handleError(err) {
  if (err instanceof SpikesScoreError) {
    console.error(`\nERRORE [${err.code}]: ${err.message}`)
    if (err.details) {
      console.error('Dettagli:', JSON.stringify(err.details).slice(0, 600))
    }
    if (err.code === 'NO_API_KEY') {
      console.error(
        '\nSuggerimento: copia .env.example in .env e inserisci la chiave,\n' +
          'oppure esporta OPENAI_API_KEY nel terminale, poi rilancia.',
      )
    }
  } else {
    console.error('\nErrore inatteso:', err)
  }
  process.exitCode = 1
}

async function run() {
  console.log(
    'Avvio scorer SPIKES sulle due trascrizioni di esempio ' +
      `(provider via .env, default Groq ${process.env.LLM_MODEL || 'llama-3.3-70b-versatile'})...`,
  )

  let good
  let bad
  try {
    good = await scoreSpikes(GOOD_TRANSCRIPT)
    printPagella('TRASCRIZIONE BUONA (segue SPIKES)', good)
  } catch (err) {
    handleError(err)
    return
  }
  try {
    bad = await scoreSpikes(BAD_TRANSCRIPT)
    printPagella('TRASCRIZIONE CATTIVA (notizia di colpo, niente empatia)', bad)
  } catch (err) {
    handleError(err)
    return
  }

  console.log('\n===== VERDETTO DISCRIMINAZIONE =====')
  const delta = good.punteggio_totale - bad.punteggio_totale
  console.log(
    `Buona: ${good.punteggio_totale}/100 · Cattiva: ${bad.punteggio_totale}/100 · Delta: ${delta}`,
  )
  const pass = good.punteggio_totale >= 65 && bad.punteggio_totale <= 45 && delta >= 25
  if (pass) {
    console.log('PASS - Lo scorer discrimina correttamente: alto sulla buona, basso sulla cattiva.')
  } else {
    console.log(
      'CHECK - La discriminazione e\' piu\' debole del previsto. Rivedere prompt o soglie.',
    )
    process.exitCode = 1
  }
}

run()
