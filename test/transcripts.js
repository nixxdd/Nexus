// Two sample transcripts used to verify the SPIKES scorer discriminates.
// Italian dialogue (Anna is Italian). Doctor turns are the thing being graded.

// GOOD: the doctor follows SPIKES end to end — sets the scene, checks Anna's
// perception, asks how much she wants to know, gives a warning shot in plain
// words, responds to her emotion with empathy, then closes with a clear plan.
export const GOOD_TRANSCRIPT = `Medico: Buongiorno Anna, si accomodi pure. Ho chiuso la porta cosi' possiamo parlare con calma, senza che nessuno ci disturbi. Come sta oggi?
Anna: Buongiorno dottore. Sono un po' agitata, a dire il vero. Speravo di avere buone notizie su questa nuova cura.
Medico: La capisco. Prima di entrare nei dettagli, mi dica: in queste settimane con il nuovo farmaco, lei come si e' sentita? Cosa ha notato?
Anna: Eh... sinceramente non un granche'. Le mani la mattina sono ancora bloccate, e la stanchezza non se n'e' andata. Ma magari ci vuole tempo, no?
Medico: Grazie di avermelo detto cosi' chiaramente, e' importante per me. Le va se le spiego cosa dicono gli esami e poi decidiamo insieme i passi successivi? Preferisce che le dica tutto, oppure andiamo per gradi?
Anna: No, no, mi dica tutto. Preferisco sapere.
Medico: Va bene. Allora... purtroppo ho una notizia non facile da darle. Gli esami ci dicono che anche questo terzo farmaco non sta facendo l'effetto che speravamo. La malattia e' ancora attiva.
Anna: No... aspetti. Ma come... era quello che doveva ridarmi la vita. Io... non me l'aspettavo.
Medico: (pausa) Lo so. Vedo che e' un colpo, e ha tutto il diritto di esserlo. Si prenda un momento. Mi rendo conto di quanto ci avesse sperato.
Anna: Ho paura, dottore. Non lo nego. Cosa mi succede adesso?
Medico: E' giusto avere paura, e io sono qui con lei. Le do anche una notizia buona pero': non siamo affatto senza strade. Ci sono altre terapie che non abbiamo ancora provato. Facciamo cosi': la settimana prossima ci rivediamo e guardiamo insieme le opzioni; intanto sistemiamo la terapia per il dolore alle mani, cosi' sta un po' meglio da subito. Le riassumo: oggi sappiamo che questo farmaco va cambiato, sappiamo che ci sono alternative, e ci risentiamo a breve per scegliere insieme. Le torna?
Anna: Si'... si', mi sento un po' piu' tranquilla cosi'. Grazie per la pazienza.
`

// BAD: the doctor dumps the news cold, in jargon, never checks what Anna knows
// or wants, ignores her fear, and rushes to "what we do next" with no shared
// plan or summary.
export const BAD_TRANSCRIPT = `Medico: Anna, allora, ho qui i risultati. Il terzo biologico ha fallito, la PCR e' ancora alta e c'e' progressione radiografica. Dobbiamo switchare a un'altra molecola, probabilmente un inibitore JAK.
Anna: Come... aspetti, non ho capito. Cosa vuol dire che ha fallito?
Medico: Vuol dire che non funziona, gli indici infiammatori sono sopra soglia. Comunque le prescrivo il nuovo farmaco, lo inizia da lunedi'. C'e' un piccolo rischio trombo-embolico ma lo monitoriamo.
Anna: Ma... io speravo tanto in questa cura. Mi avevate detto che era la svolta.
Medico: Eh, la reumatoide e' cosi', a volte i farmaci smettono di rispondere, capita. L'importante e' non perdere tempo. Le faccio anche gli esami per il pre-screening del nuovo farmaco.
Anna: Sto peggiorando allora? Ho paura...
Medico: Guardi, per adesso pensiamo a cambiare terapia. Le lascio la ricetta e il foglio degli esami. Per altre domande chieda pure in segreteria. La saluto, arrivederci.
`
