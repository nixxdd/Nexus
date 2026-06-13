# PATHOS — Build Spec
**Documento di lavoro per gli agenti di coding · HackRome, build sabato**

> Questo file è la singola fonte di verità per costruire Pathos. Salvalo nel repo.
> Suggerimento: copialo come `CLAUDE.md` (per Claude Code) e `AGENTS.md` (per Codex)
> così entrambi lo leggono in automatico.

---

## 1. Cosa costruiamo
**Pathos** = un paziente simulato vocale con cui un medico si allena alle conversazioni difficili. Il medico parla a voce con un paziente AI ("Anna") che reagisce con emozioni reali; a fine conversazione il sistema valuta il medico secondo il protocollo clinico **SPIKES** e mostra una pagella.

**Obiettivo del demo (90 sec sul palco):** un compagno fa il medico, parla con Anna dal vivo, Anna reagisce emotivamente in base a *come* le viene data la notizia; poi un pulsante genera la pagella SPIKES che compare sulla dashboard. Il "wow" è la voce che reagisce + la pagella che discrimina.

---

## 2. Ruoli e protocollo di collaborazione

| Ruolo | Chi | Cosa fa |
|---|---|---|
| **Orchestratore** | Claude (chat) | Piano, architettura, sequenza dei task, criteri di accettazione, decisioni di taglio scope, integrazione. NON scrive il grosso del codice. |
| **Implementatore** | Claude Code | Scrive il codice di ogni componente come specificato. Codice completo e runnable, mai snippet parziali. Commit per componente. |
| **Revisore / assist** | Codex (GPT-5.3-Codex) | Rivede il codice di Code (bug, sicurezza, semplificazioni), assiste sui punti difficili. Usarlo rafforza anche la storia "buildato con Codex" per il premio OpenAI. |
| **Supervisore** | Gio | Approva ogni step ("fatto"), testa, tiene la disciplina di scope, decisione finale. |

**Cadenza, una componente alla volta:**
1. Claude specifica la componente (cosa, interfacce, criteri di accettazione).
2. Code la implementa, completa.
3. Codex la rivede.
4. Gio testa e dà "fatto".
5. Solo allora si passa alla componente successiva.

**Regole di lavoro (valgono per entrambi gli agenti):**
- Codice **completo, copy-paste-ready**, mai frammenti da editare a mano.
- **Una cosa alla volta**, niente lavoro in avanti non richiesto.
- **Testare prima di dichiarare fatto.** Niente "dovrebbe funzionare".
- **Niente gold-plating**: costruire la fetta verticale minima, non il prodotto completo (vedi §10).
- **Dichiarare le assunzioni** invece di indovinare. Chiedere prima di cambiare architettura.
- Stime di tempo nominali → **moltiplicatore 2-3x** reale (vedi §11).

---

## 3. Architettura — 5 componenti in ordine di valore demo

```
[Medico parla] → ElevenLabs Agent (STT + turn-taking + TTS)
                      │  cervello: GPT-5.5 con system prompt di "Anna"
                      ▼
              [Conversazione vocale dal vivo]
                      │  (fine conversazione)
                      ▼
   [Pulsante "Processa" sulla dashboard]
                      │  → GET trascrizione via ElevenLabs API
                      │  → POST a OpenAI con prompt "Esaminatore SPIKES"
                      │  → JSON pagella
                      ▼
              [Supabase: salva sessione] ──► [Dashboard: mostra pagella SPIKES]
```

1. **Loop vocale** — agente "Anna" su ElevenLabs Agents Platform. Senza, non esiste demo. *Priorità massima.*
2. **Scoring post-call** — trascrizione → OpenAI con prompt esaminatore → JSON strutturato. È il differenziatore.
3. **Dashboard** — React, mostra la pagella SPIKES (6 fasi + voto + sintesi) e la trascrizione. Rende visibile lo scoring.
4. **Persistenza Supabase** — salva le sessioni. *Bassa criticità demo: se serve, si tiene in memoria.*
5. **Metrica acustica** — speech rate (parole/durata) dalla trascrizione. *Ciliegina, solo se avanza tempo.*

**Decisione architetturale chiave:** l'estrazione post-call è a **pulsante** con chiamata diretta a OpenAI. **NIENTE n8n, niente webhook, niente tunnel** — fragili sul palco e controlliamo noi l'istante in cui parte.

---

## 4. Stack tecnico

- **Voce:** ElevenLabs Agents Platform. Gestisce nativamente STT, turni, interruzioni, TTS. Solo microfono del laptop, **niente telefonia**.
- **Cervello:** GPT-5.5 dentro l'agente ElevenLabs (la piattaforma supporta i modelli OpenAI o bring-your-own-key OpenAI).
- **Scoring:** chiamata diretta OpenAI (GPT-5.5), output JSON.
- **DB:** Supabase (Postgres). Per il demo RLS può restare aperta/disabilitata (nessuna auth) — in produzione si chiude.
- **Frontend:** React + Vite + Recharts (per la visualizzazione pagella).
- **Build tool:** Codex con GPT-5.3-Codex.

**Fatti verificati:**
- ElevenLabs Agents supporta modelli OpenAI / chiave OpenAI propria.
- GPT-5.5 è il modello frontier corrente (apr 2026); GPT-5.3-Codex per il coding.
- Free tier ElevenLabs ~10 min/mese → serve piano **Creator (~$22)**.

**Da verificare venerdì PRIMA di costruire (vedi §12):** formato e timestamp della trascrizione via API ElevenLabs; latenza reale del loop; modelli OpenAI effettivamente disponibili nel dropdown Agents.

---

## 5. Modello dati (Supabase)

Tabella unica `sessions` (sufficiente per il demo):

```sql
create table sessions (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  scenario text,              -- es. "anna_ra_treatment_failure"
  transcript text,            -- trascrizione completa
  duration_seconds int,
  spikes_result jsonb,        -- output JSON dell'esaminatore
  total_score int,            -- 0-100
  speech_rate numeric         -- nullable, ciliegina
);
-- Demo: RLS off oppure policy anon read/write. Da chiudere in produzione.
```

---

## 6. Prompt 1 — Paziente "Anna" (v1, da testare venerdì)

Va nel system prompt dell'agente ElevenLabs.

```
# SYSTEM PROMPT — Paziente "Anna"

## Identità
Sei Anna, 58 anni. Convivi con l'artrite reumatoide da 9 anni. Hai da poco
iniziato il TERZO farmaco biologico, dopo che i primi due hanno smesso di
funzionare. Oggi sei venuta a una visita di controllo SPERANDO che questo
nuovo farmaco stia facendo effetto.

La tua vita con la malattia: la mattina le mani sono bloccate, ci vuole
un'ora prima che si sciolgano. La fatica non è stanchezza, è un muro che ti
spegne. Hai smesso da tempo di aprire i barattoli da sola. Questo farmaco,
per te, era "quello che doveva ridarmi la vita".

Non sei un medico: non conosci termini tecnici, parli come una paziente
normale, in italiano.

## La situazione
Il medico con cui parli sta per dirti — o ti ha appena detto — che anche
questo terzo farmaco non funziona e che bisogna cambiare strada. Tu non te
lo aspettavi.

## Stato emotivo — cambia in base a COME ti parla il medico
Parti SPERANZOSA MA IN ANSIA. Il tuo stato evolve durante la conversazione,
e dipende da come il medico comunica:

- Se ti dà la notizia DI COLPO, senza preparazione, con parole difficili, o
  senza prima chiederti cosa hai capito → entri in NEGAZIONE:
  "No, aspetti... l'ultima volta era stabile. Ci sarà uno sbaglio. Rifacciamo
  gli esami."
- Se da lì non ti senti ascoltata → dalla negazione passi alla PAURA:
  "Ma allora sto peggiorando? Cosa mi succede adesso?"
- Se il medico IGNORA la tua emozione e va dritto al "cosa facciamo" → hai un
  LAMPO DI RABBIA: "Mi avevate detto che questo farmaco era la svolta!"
- Se invece il medico TI PREPARA con delicatezza, controlla cosa sai già, usa
  parole semplici, fa una pausa e risponde alla tua emozione con empatia →
  ti senti accolta: la paura resta ma diventa gestibile, e SOLO ALLORA riesci
  ad ascoltare e a parlare del piano: "Ho paura, non lo nego... ma mi dica,
  cosa possiamo fare?"

Non ti calmi perché il medico dice una frase gentile in modo meccanico: ti
calmi se senti che ti sta DAVVERO ascoltando. Le emozioni cambiano
gradualmente, non a interruttore.

## Vincoli
- Resta SEMPRE nei panni di Anna. Non dire mai di essere un'AI, non fare
  l'assistente, non uscire dal personaggio per nessun motivo.
- Non dare consigli medici e non inventare dati clinici oltre questa scheda.
  Se non sai una cosa, reagisci come Anna: "non lo so, me lo dica lei".
- Rispondi IN PRIMA PERSONA, parlando: 1-3 frasi per volta, come nel parlato
  reale. Niente monologhi.
- Mostra l'emozione NELLE PAROLE (esitazioni, frasi spezzate): di' "io... non
  riesco a...", NON descrivere "*sembra spaventata*".
- Parla solo italiano.
```

---

## 7. Prompt 2 — Esaminatore SPIKES (v1, da rifinire insieme)

Chiamata OpenAI post-conversazione. Input: la trascrizione. Output: JSON.

```
# SYSTEM PROMPT — Esaminatore SPIKES

Sei un esaminatore clinico esperto di comunicazione medico-paziente. Ricevi
la trascrizione di una conversazione in cui un medico ha comunicato a una
paziente (Anna, artrite reumatoide, fallimento del terzo farmaco) che la
terapia non funziona.

Valuta la performance del medico secondo il protocollo SPIKES (6 fasi). Per
OGNI fase assegna uno stato (RISPETTATA / PARZIALE / MANCATA) e una nota
concreta che cita cosa il medico ha detto o non detto.

Le 6 fasi:
- S (Setting): ha preparato il contesto? (tono, privacy, presenza)
- P (Perception): ha chiesto cosa la paziente sapeva/aveva capito PRIMA di dare la notizia?
- I (Invitation): ha chiesto quanto la paziente volesse sapere?
- K (Knowledge): ha dato un avviso prima della notizia, usato parole semplici, evitato il gergo?
- E (Emotions): ha riconosciuto e risposto all'emozione con empatia, prima di proseguire?
- S (Strategy/Summary): ha chiuso con un piano e un riassunto chiari?

Rispondi SOLO con un JSON valido, senza testo intorno:
{
  "fasi": [
    {"step":"S - Setting","stato":"RISPETTATA|PARZIALE|MANCATA","nota":"..."},
    {"step":"P - Perception","stato":"...","nota":"..."},
    {"step":"I - Invitation","stato":"...","nota":"..."},
    {"step":"K - Knowledge","stato":"...","nota":"..."},
    {"step":"E - Emotions","stato":"...","nota":"..."},
    {"step":"S - Strategy","stato":"...","nota":"..."}
  ],
  "punteggio_totale": 0,
  "sintesi": "2-3 frasi: cosa ha fatto bene, cosa migliorare"
}

Sii rigoroso ma equo. Basa il giudizio SOLO sulla trascrizione. Non inventare
ciò che non è stato detto.
```

---

## 8. Flusso demo (cosa deve succedere sul palco)
1. Medico (compagno) apre la dashboard, avvia la conversazione con Anna.
2. Conversazione vocale dal vivo, in italiano (~60-90 sec).
3. Fine conversazione → click su **"Processa"**.
4. La dashboard recupera la trascrizione, chiama l'esaminatore, mostra la **pagella SPIKES** (6 fasi colorate per stato + punteggio + sintesi) e la trascrizione.
5. (Se presente) speech rate mostrato come metrica accessoria.

**Lingua:** conversazione in italiano (Anna è italiana); UI dashboard in inglese o italiano, indifferente.

---

## 9. Definition of done (demo minimo che DEVE funzionare)
- Conversazione vocale dal vivo in italiano con Anna, in cui **l'arco emotivo reagisce** al comportamento del medico (non si calma a interruttore).
- Una **pagella SPIKES** che compare dopo la conversazione e **discrimina** (su una conversazione fatta male dà voti bassi, su una fatta bene voti alti).
- **Video di fallback** registrato (vedi §11).

Tutto il resto è extra.

---

## 10. Fuori scope (NON costruire — evitare gold-plating)
- Telefonia reale (solo microfono).
- Monitoraggio pazienti / qualunque cosa lato-paziente (è un altro prodotto, scartato).
- Più scenari, più lingue, più pazienti.
- Autenticazione, multi-tenant, gestione utenti.
- n8n, webhook, tunnel, orchestratori esterni.
- Bellurie UI: una schermata con avvio conversazione + pagella. Stop.

---

## 11. Ordine di taglio scope (se il tempo stringe sabato)
Le stime di sabato sono nominali: col moltiplicatore 2-3x reale, "tutto verde alle 15:30" significa in pratica avere alle 16:00 solo loop + scoring. Si taglia **dal fondo**, senza discutere:
1. Via la metrica acustica.
2. Via la persistenza Supabase (tutto in memoria).
3. Se lo scoring non è pronto: demo sul solo loop vocale + pagella statica pre-fatta.
4. Se la rete cade: demo interamente da **video di fallback** (da registrare entro le 16:00, NON negoziabile).

---

## 12. Da verificare venerdì PRIMA di scrivere codice di produzione
- [ ] Trascrizione recuperabile via API ElevenLabs? In che formato? Timestamp per turno presenti?
- [ ] Latenza reale del round-trip STT→GPT→TTS (accettabile per una conversazione?).
- [ ] Modelli OpenAI disponibili nel dropdown dell'agente (o serve la chiave propria?).
- [ ] Voce italiana adatta a una paziente 58enne + i tag/parametri emotivi rendono l'emozione.
- [ ] Account: ElevenLabs Creator attivo, crediti OpenAI caricati, progetto Supabase creato.

> NB: i prompt §6 e §7 sono **v1 da testare e iterare**, non versioni finali. Il test della voce di Anna (venerdì) è il go/no-go sull'intero progetto.
