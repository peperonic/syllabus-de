# Curricula source inventory: Sachsen (SN), Sachsen-Anhalt (ST), Thüringen (TH), Saarland (SL)

Scope: Mathematik, Chemie, Physik; Grundschule (Mathematik, Sachunterricht science strand), all general-education Sek I forms, integrated science in lower Sek I, gymnasiale Oberstufe. Excluded: berufliche Schulen, Förderschulen. Research date: 2026-11-07 (UTC). Machine-readable versions: `inventory/SN.yaml`, `ST.yaml`, `TH.yaml`, `SL.yaml` (schema curricula-inventory/v1).

Method note: direct curl from this sandbox is blocked by the proxy (403 CONNECT) for all four state portals; all verification was done with WebFetch and WebSearch. "verified" below means the page/PDF was fetched on 2026-11-07; "listed" means the URL was seen in a fetched page or search index but not opened; "unverified" means taken from prior knowledge.

---

## 1. Sachsen (SN)

### Institutions
- Ministry: Sächsisches Staatsministerium für Kultus (SMK), https://www.smk.sachsen.de/ (unverified). Herausgeber of all Lehrpläne (Impressum of fetched PDFs).
- Landesinstitut: Landesamt für Schule und Bildung (LaSuB), https://www.lasub.smk.sachsen.de/ (unverified). LaSuB does the Teilüberarbeitungen (Impressum of fetched Lehrplan PDF). Predecessors: Comenius-Institut, Sächsisches Bildungsinstitut (SBI).
- Portal: Lehrplandatenbank. https://www.schule.sachsen.de/lpdb/ is a meta-refresh redirect (verified) to https://www.schulportal.sachsen.de/lplandb/ . The index page is **robots-disallowed** for WebFetch (verified 2026-11-07), but individual PDF files under `/lplandb/lehrplan/file/<id>/<token>` were fetched successfully.

### Legal basis
- "Verwaltungsvorschrift des Sächsischen Staatsministeriums für Kultus über Lehrpläne und Stundentafeln für Grundschulen, Förderschulen, Oberschulen, Gymnasien (Sekundarstufe I), Abendoberschulen, Abendgymnasien und Kollegs ... (VwV Stundentafeln)" vom 20. Juni 2018 (MBl. SMK S. 347), revosax Nr. 17744. Current consolidated text "Stand 31.10.2026": https://revosax.sachsen.de/vorschrift_gesamt/17744/49961.html (verified). Latest amendment 23 July 2026 (MBl. SMK S. 118), Ziff. I for 2026/27, Ziff. II for 2027/28 (future Fassung from 01.08.2027: .../17744/49962.html, listed).
- Ziffer II: "Im Unterricht sind die Lehrpläne anzuwenden, die in der Landesliste der Lehrpläne ..." aufgeführt sind; the Landesliste is issued annually by the oberste Schulaufsichtsbehörde. So curricula are incorporated by reference via the Landesliste (relevant for § 5 UrhG: Abs. 2 "amtliche Werke" likely, Abs. 1 arguable; assessment, not legal advice).
- Ziffer VII: Gemeinschaftsschule uses Grundschule plans in the Primarstufe and Oberschule or Gymnasium plans in Sek I according to the pupil's Anforderungsniveau; Abitur track needs at least 265 Wochenstunden in Kl. 5-12. **No separate Gemeinschaftsschule Lehrpläne exist.** Oberschule+ uses Grundschule plans (primary part) and Oberschule plans (secondary).
- Oberstufe: Oberstufen- und Abiturprüfungsverordnung (OAVO), revosax Nr. 9362, https://revosax.sachsen.de/vorschrift/9362 (listed).
- Landesliste der Lehrpläne, August 2026, Schuljahr 2026/27, Redaktionsschluss 31.07.2026: https://publikationen.sachsen.de/bdb/artikel/50836/documents/78638 (verified). Entries marked * changed vs. 2025/26.

### Current Lehrpläne (from Landesliste 2026/27)
| Fach | Schulart | Fassungen | Note |
|---|---|---|---|
| Mathematik | Grundschule | 2004/2009/2019/2025/2026* | Anpassung 2026 |
| Mathematik | Oberschule | 2004/2009/2019 | |
| Mathematik | Gymnasium (5-12 incl. Oberstufe) | 2004/2009/2011/2013/2019/2021 | |
| Chemie | Oberschule | 2004/2009/2019/2025 | starts Kl. 8 (verified in PDF) |
| Chemie | Gymnasium | 2004/2007/2009/2011/2019/2022/2025 | |
| Physik | Oberschule | 2004/2009/2019/2025 | |
| Physik | Gymnasium | 2004/2007/2009/2011/2019/2022/2025/2026* | Anpassung 2026 |
| Sachunterricht | Grundschule | 2004/2009/2019 | |
No "Naturwissenschaften" integrated subject and no Gemeinschaftsschule entries in the Landesliste.

Verified PDF: Lehrplan Oberschule Chemie (Fassungen 2004/2009/2019/2025), https://www.schulportal.sachsen.de/lplandb/lehrplan/file/126/3dX0LbmYg3xg1RQdZ6di . Klassenstufen 8-9 (Hauptschulbildungsgang) and 8-10 (Realschulbildungsgang); Lernbereiche with Ustd., Wahlbereiche (e.g. Kl. 8 "Stoffe, die uns umgeben", "Untersuchen von Stoffen", "Stoffe wandeln sich um"). This structure (Lernbereiche per Klassenstufe with Zeitrichtwerte, Lernziele, Wahlbereiche) is ideal for a learning assistant.

### School structure
- Grundschule 1-4; Oberschule 5-10 (Hauptschul- and Realschulbildungsgang from Kl. 7); Oberschule+ (pilot, 1-10); Gymnasium 5-12 (G8, Abitur after 12); Gemeinschaftsschule (since SchulG change 2020, very few schools, 1-12 possible).
- Chemie: Oberschule from Kl. 8 (verified); Gymnasium from Kl. 7 (unverified). Physik: from Kl. 6 at Oberschule and Gymnasium (unverified).
- Stundentafeln: Anlagen 1a (GS), 3a (OS), 4a (GY) of the VwV Stundentafeln, linked but not reproduced on the revosax HTML; PDF version e.g. https://www.revosax.sachsen.de/vorschrift_gesamt/17744/49962.pdf (listed, not opened).
- Oberstufe (Jgst. 11-12): Grundkurs / Leistungskurs; Gymnasium Lehrpläne cover 5-12 in one document per subject, with separate Gk/Lk sections (Gk/Lk distinction confirmed in the Berufliches Gymnasium PDF; for allgemeinbildendes Gymnasium unverified).

### Scraper facts
- Kind: database (Lehrplandatenbank) with PDF downloads. File URL pattern `https://www.schulportal.sachsen.de/lplandb/lehrplan/file/<numeric id>/<20-char token>`; token is required, so URLs must be harvested from the index (robots-disallowed for crawlers; check with the operator or use the Landesliste plus manual mapping). Many file IDs are indexed by search engines (e.g. 71, 78, 83, 98, 100, 102, 111, 116, 125, 126, 128, 130, 131, 140, 143, 198, 220, 461, 521, 523, 545, 630, 913) but only 126 (OS Chemie) and 913 (BGY Technik, out of scope) were identified.
- The annual Landesliste PDF (publikationen.sachsen.de) is the authoritative change log: diff it yearly.
- Licence: fetched PDFs carry an Impressum (Herausgeber SMK) but no explicit copyright or open-licence statement. Portal terms not seen (index blocked).

### Supplementary (official)
- Abitur and Abschlussprüfungen Oberschule: SMK/schule.sachsen.de pages (unverified); past papers are generally not published openly by SN (unverified).
- Kompetenztests (Kl. 3 VERA, Kl. 6 and 8): run by LaSuB (unverified).
- Handreichungen, Zeitleiste for GS/OS Lehrplan changes: https://cms.sachsen.schule/fileadmin/_special/gruppen/836/Zeitleiste_GS_OS.pdf (listed).

### Gaps SN
- Mapping of file IDs to Mathematik GS/OS/GY, Physik OS/GY, Chemie GY, Sachunterricht GS not done (index blocked).
- Stundentafel hours not extracted; Physik/Chemie start grades at Gymnasium unverified.
- Content of the 2026 Anpassungen (Mathematik GS, Physik GY) not checked.

---

## 2. Sachsen-Anhalt (ST)

### Institutions
- Ministry: Ministerium für Bildung des Landes Sachsen-Anhalt (MB), https://mb.sachsen-anhalt.de/ (unverified; ministry name verified from press release 28.02.2025).
- Landesinstitut: Landesinstitut für Schulqualität und Lehrerbildung Sachsen-Anhalt (LISA), Halle, https://lisa.sachsen-anhalt.de/ (verified). Lehrplan page https://lisa.sachsen-anhalt.de/schulqualitaet/lehrplaene-rahmenrichtlinien (verified) only links to the Bildungsserver per Schulform; also "Anhörungsverfahren/Erprobung" and "Prüfungen/Zentrale Leistungserhebungen" pages.
- Portal: Bildungsserver Sachsen-Anhalt https://www.bildung-lsa.de/ , Lehrplan pages per Schulform (all verified as pages, "Stand vom 05.11.2026"):
  - Grundschule: .../informationsportal/unterricht/grundschule/schulformbezogene_informationen/lehrplan.htm
  - Sekundarschule: .../informationsportal/unterricht/sekundarschule/schulformbezogene_informationen/lehrplan.htm ("Grundsatzband und Fachlehrpläne")
  - Gemeinschaftsschule: .../informationsportal/unterricht/gemeinschaftsschule/lehrplan.htm
  - Gymnasium: .../informationsportal/unterricht/gymnasium/schulformbezogene_informationen/lehrplan.htm
  - No separate Gesamtschule page.

### Licences (important, and unusually open)
- Bildungsserver Lehrplan articles: CC BY-SA 4.0 (attribution "Redaktion bildung-lsa.de auf dem Bildungsserver Sachsen-Anhalt"); site metadata says CC BY 3.0 DE for texts (conflict noted).
- Embedded LISA documents on the Gymnasium page: licence table shows CC BY-NC-ND 4.0 (6 items), CC BY-NC-SA 4.0 (1), CC BY-SA 4.0 (6, Redaktion); Sekundarschule page: CC BY-ND 4.0.
- Inside PDFs: Fachlehrplan Mathematik Gymnasium (Stand 01.07.2019) states "Quelle: Landesportal Sachsen-Anhalt (http://lisa.sachsen-anhalt.de) | Lizenz: Creative Commons (CC BY-SA 3.0)"; Fachlehrplan Mathematik Grundschule (in Kraft ab 01.08.2026) states "Lizenz: CC BY-SA 4.0", Quelle LISA. Per-document licence must be recorded; the PDF's own statement should take precedence over the page table (assessment).

### Documents
| Fach | Schulform | Grades | File | Stand / in force | Status |
|---|---|---|---|---|---|
| Grundsatzband | Grundschule | 1-4 | https://www.bildung-lsa.de/files/7c5f6ff122fa27b7eb9822ab54ee6396/GSB_GS_LT_01082026.pdf | 01.08.2026 | current (listed) |
| Mathematik | Grundschule | 1-4 | https://www.bildung-lsa.de/files/7c5f6ff122fa27b7eb9822ab54ee6396/FLP_GS_Mathe_LT_01082026.pdf | in Kraft ab 01.08.2026 | current (verified) |
| Sachunterricht | Grundschule | 1-4 | https://www.bildung-lsa.de/files/7c5f6ff122fa27b7eb9822ab54ee6396/FLP_GS_Sachunt_LT_01082026.pdf | 01.08.2026 | current (listed) |
| Mathematik (old) | Grundschule | 1-4 | https://back.bildung-lsa.de/files/7c5f6ff122fa27b7eb9822ab54ee6396/lp_gs_mathe_01_08_2019.pdf | 01.08.2019 | superseded (transition unclear) |
| Mathematik | Sekundarschule | 5-10 | https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_mathe_01_08_2019.pdf | 01.08.2019 (base 2012) | current until 2027/28 (listed) |
| Chemie | Sekundarschule | 7-10 (unverified) | https://lisa.sachsen-anhalt.de/fileadmin/Bibliothek/Politik_und_Verwaltung/MK/LISA/Unterricht/Lehrplaene/Sek/lp_sks_chemie.pdf | 2012/2019 (edition unverified) | current until 2027/28 (listed) |
| Physik | Sekundarschule | 6-10 (unverified) | https://lisa.sachsen-anhalt.de/fileadmin/Bibliothek/Politik_und_Verwaltung/MK/LISA/Unterricht/Lehrplaene/Sek/lp_sks_physik.pdf | 2012/2019 (edition unverified) | current until 2027/28 (listed) |
| Grundsatzband | Gymnasium | 5-12 | https://lisa.sachsen-anhalt.de/fileadmin/Bibliothek/Politik_und_Verwaltung/MK/LISA/Unterricht/Lehrplaene/Gym/GSB_Gym_LT.pdf | unknown | listed |
| Mathematik | Gymnasium / Berufliches Gymnasium | 5-12 | https://www.bildung-lsa.de/files/b45de329c361a40a2f0a7211902d5815/Mathematik_FLP_Gym_01_07_2019.pdf | Stand 01.07.2019 | current (verified) |
| Chemie | Gymnasium | 7-12 (unverified) | https://www.bildung-lsa.de/files/b45de329c361a40a2f0a7211902d5815/Chemie_FLP_Gym_01_07_2019.pdf | 01.07.2019 | current (listed) |
| Physik | Gymnasium | 6-12 (unverified) | https://www.bildung-lsa.de/files/b45de329c361a40a2f0a7211902d5815/FLP_Physik_Gym_01082022_swd.pdf | 01.08.2022 | current (listed) |

Mathematik Gymnasium structure (verified): Doppeljahrgänge 5/6, 7/8, Schuljahrgang 9, 10 = Einführungsphase, 11/12 = Qualifikationsphase with grundlegendem und erhöhtem Anforderungsniveau; Kompetenzschwerpunkte e.g. 9 "Potenzen und Logarithmen, Trigonometrie, quadratische Gleichungen und Funktionen".

Reform: press release MB 28.02.2025: all Sekundarschule Fachlehrpläne and the Grundsatzband (from 2012, adapted 2019) are being rewritten by 22 LISA commissions on the basis of the new KMK Bildungsstandards (Mathematik ESA/MSA; Biologie/Chemie/Physik MSA); binding from **Schuljahr 2027/28**, also for other school forms awarding Haupt-/Realschulabschluss (i.e. Gemeinschaftsschule, Gesamtschule).

### School structure
- Grundschule 1-4 (Schuleingangsphase 1/2); Sekundarschule 5-10; Gemeinschaftsschule 5-10 (or 5-13 with Oberstufe); Gesamtschule (integrierte/kooperative); Gymnasium 5-12 (G8, verified via FLP: Einführungsphase = 10, Qualifikationsphase 11/12).
- Gemeinschaftsschule and Gesamtschule use Sekundarschule and Gymnasium Fachlehrpläne (unverified, inferred from press release and portal structure).
- Integrated science 5/6: not confirmed. The task brief mentions "Naturwissenschaften 5/6"; no such Fachlehrplan surfaced in searches (gap).
- Chemie/Physik start grades: not verified (Physik likely 6, Chemie 7; unverified).
- Stundentafel: Erlass "Unterrichtsorganisation" / Stundentafeln (not located).
- Legal basis for Inkraftsetzung: Runderlass of MB not located; documents carry "In Kraft ab" dates.

### Scraper facts
- bildung-lsa.de: server-rendered CMS pages; document links not exposed to WebFetch (rendered as "Dokument von LISA" rows without hrefs; possibly JS-rendered or embedded media). PDFs live under `https://www.bildung-lsa.de/files/<32-hex folder hash>/<filename>.pdf` (mirror host back.bildung-lsa.de); folder hashes observed: 7c5f6ff1... (Grundschule), 164f3f97... (Sekundarschule), b45de329... (Gymnasium). Filenames encode Stand date (e.g. _01082026, _01_07_2019). Older copies under lisa.sachsen-anhalt.de/fileadmin/Bibliothek/Politik_und_Verwaltung/MK/LISA/Unterricht/Lehrplaene/{Sek,Gym,Konzepte}/ .
- Use a headless browser on the four lehrplan.htm pages to harvest links.

### Supplementary (official)
- LISA Prüfungen/Zentrale Leistungserhebungen: https://lisa.sachsen-anhalt.de/schulqualitaet/pruefungen-zentrale-leistungserhebungen (listed): Abitur, Abschlussprüfungen Sekundarschule, VERA.
- Niveaubestimmende Aufgaben (NBA): published on bildung-lsa.de per Fach and Schulform (unverified URL).
- "Fachliche Orientierung Mathe": https://back.bildung-lsa.de/files/0cf06e8b1aa571c799b255202ea18103/Fachliche_Orientierung_Mathe.pdf (listed).
- "Anforderungen Gymnasium Bildung in der digitalen Welt": https://lisa.sachsen-anhalt.de/fileadmin/Bibliothek/Politik_und_Verwaltung/MK/LISA/Unterricht/Lehrplaene/Konzepte/Anforderungen_Gymnasium_Bildung_digitale_Welt.pdf (listed).
- LISA Pub 01/2022 "Was ist neu? Anpassung im Rahmen der Erprobung": https://back.bildung-lsa.de/files/a78543c49cd4edf5850514d31aa4078f/LISA_Pub_01_2022_Was_ist_neu_Anpassung_im_Rahmen_der_Erprobung.pdf (listed).

### Gaps ST
- Exact current editions of Sekundarschule Chemie/Physik (2019 Anpassung vs lisa fileadmin copy).
- Naturwissenschaften 5/6 not found; Gesamtschule/Gemeinschaftsschule rules unverified; Stundentafel and Inkraftsetzungserlass not located.
- Transition rule for new Grundschule plans (all grades from 01.08.2026 or aufwachsend) not checked.

---

## 3. Thüringen (TH)

**Verification status: weak.** The Thüringer Schulportal could not be fetched: https://www.schulportal-thueringen.de/lehrplaene and https://www.schulportal-thueringen.de/web/guest/lehrplaene both returned client_error to WebFetch (2026-11-07); the home page returned only an outdated (about 2017) cached page. Web search did not index individual Thüringen Lehrplan PDFs. Most facts below are prior knowledge and marked unverified.

### Institutions
- Ministry: Thüringer Ministerium für Bildung, Wissenschaft und Kultur (TMBWK; until 2024 TMBJS), https://bildung.thueringen.de/ (unverified).
- Landesinstitut: Thüringer Institut für Lehrerfortbildung, Lehrplanentwicklung und Medien (ThILLM), Bad Berka (name and seat confirmed on the cached portal page), https://www.thillm.de/ (unverified).
- Portal: Thüringer Schulportal, Lehrpläne in the "Mediothek"; the Deutscher Bildungsserver (page updated 08.10.2026, verified) links https://www.schulportal-thueringen.de/web/guest/lehrplaene and describes it as "Lehrpläne für allgemein- und berufsbildende Schulen zum Download in der Mediothek ... Links führen zu Übersichten je Schulart". The brief's URL https://www.schulportal-thueringen.de/lehrplaene is the short form.

### Expected documents (all unverified; titles follow Thüringen naming conventions)
- Grundschule: "Lehrplan für die Grundschule und für die Förderschule mit dem Bildungsgang der Grundschule": Mathematik (2010, revised 2015?), Heimat- und Sachkunde (HSK, the Thüringen name for Sachunterricht; 2010/2015?).
- Regelschule (and Gemeinschaftsschule/Gesamtschule Sek I): "Lehrplan für den Erwerb des Hauptschul- und Realschulabschlusses": Mathematik, Chemie, Physik; Mensch-Natur-Technik (MNT) Klassenstufe 5/6 (integrated Biologie/Physik/Chemie basics).
- Gymnasium: "Lehrplan für den Erwerb der allgemeinen Hochschulreife": Mathematik, Chemie, Physik (Kl. 5/7 to 12, including Qualifikationsphase 11/12); MNT 5/6 also at Gymnasium.
- Gemeinschaftsschule: no separate subject plans expected; uses the above by Abschluss target (unverified).
- Kursplan Medienkunde Grundschule in force 21.02.2017 (confirmed on cached portal page; out of scope).

### School structure (unverified)
- Grundschule 1-4; Regelschule 5-10; Gemeinschaftsschule 1-12/13; Gesamtschule; Gymnasium 5-12 (G8, Abitur after 12, as in the brief).
- MNT in 5/6 replaces separate science subjects; Physik and Chemie as separate subjects from Kl. 7 (Chemie possibly from 7 or 8; unverified).
- Stundentafeln: Anlagen to the Thüringer Schulordnung (ThürSchulO); Oberstufe also in ThürSchulO (gymnasiale Oberstufe, Kurse auf grundlegendem / erhöhtem Anforderungsniveau; unverified).

### Scraper facts
- Liferay-based portal (path /web/guest/...), rejected automated fetch from this environment. Plan for a headless browser and contact ThILLM about bulk access. PDF URL pattern unknown.

### Supplementary (unverified)
- Thüringer Kompetenztests (Kl. 3, 6, 8) run with Friedrich-Schiller-Universität Jena, https://www.kompetenztest.de/ (unverified).
- Abitur and Realschulabschluss exam information on the Schulportal (unverified).

### Gaps TH
- Everything document-level: titles, years, URLs, in-force dates, status. Re-run with a browser tool (Claude in Chrome) or from a non-proxied network.

---

## 4. Saarland (SL)

**Verification status: weak.** saarland.de returned client_error to WebFetch for the Lehrplan overview and the Gymnasium Lehrplan page (2026-11-07). Page URLs below come from the Deutscher Bildungsserver (verified) and the search index (listed).

### Institutions
- Ministry: Ministerium für Bildung und Kultur Saarland (MBK), https://www.saarland.de/mbk/ (listed; minister Christine Streichert-Clivot named in news4teachers 2023).
- Landesinstitut: Landesinstitut für Pädagogik und Medien (LPM), https://www.lpm.uni-sb.de/ (unverified).
- Portal: Bildungsserver Saarland within saarland.de (Government Site Builder CMS):
  - Overview: https://www.saarland.de/mbk/DE/portale/bildungsserver/schulen-und-bildungswege/lehrplaene/lehrplaene.allgemeinbildende (linked by Deutscher Bildungsserver; covers Grundschule, Förderschule, Gemeinschaftsschule, Gymnasium, gymnasiale Oberstufe, Schengen-Lyzeum, Europäische Schule Saarland; documents as PDF).
  - Gymnasium: .../lehrplaene.allgemeinbildende/gymnasium.lehrplaene (listed).
  - Grundschule, Gemeinschaftsschule, gymnasiale Oberstufe sub-pages expected with the same naming (unverified).

### School structure
- Grundschule 1-4; Gemeinschaftsschule 5-10 (Oberstufe to 13 at some schools); Gymnasium.
- G9: Landtag decided the return to G9 in March 2023; pupils in Klassenstufen 5-7 in 2023/24 take the Abitur after nine years (news4teachers, verified). First G9 Abitur therefore 2030 (inference). Older cohorts finish G8. Informatik introduced, Sozialkunde strengthened.
- G9 implies new or revised Gymnasium Lehrpläne written aufwachsend from 2023/24 (unverified).
- Gemeinschaftsschule: Novellierung of GemS presented in Oct 2024 (school presentation 241028_Praesentation_zur_Novellierung_GemS_Info-IV.pdf, listed; content not checked).
- Integrated science: Naturwissenschaften at Gemeinschaftsschule lower Sek I (per brief; grades and transition to Physik/Chemie unverified). Gymnasium: separate subjects, start grades unverified.
- Oberstufe: Einführungsphase plus Hauptphase, courses on grundlegendem / erhöhtem Niveau (unverified).

### Scraper facts
- saarland.de blocks this environment's fetcher (client_error). GSB-style CMS; documents typically under /mbk/DE/... /SharedDocs/Downloads/... with `?__blob=publicationFile` (unverified). Use a browser.

### Supplementary (unverified)
- LPM: Handreichungen, Abitur materials, VERA; Abitur Hinweise from MBK.

### Gaps SL
- All document-level details (titles, URLs, years, Erprobung status of G9 Lehrpläne, Gemeinschaftsschule Naturwissenschaften). Legal basis and licence not seen.

---

## Addendum to ST (found late)
- Possible legal basis: MB Erlass list "Rahmenrichtlinien ab 2023/2024": https://mb.sachsen-anhalt.de/fileadmin/Bibliothek/Landesjournal/Bildung_und_Wissenschaft/Erlasse/Rahmenrichtlinien_ab2023_2024.pdf (listed, not opened).
- LISA folder for Gemeinschaftsschule/Gesamtschule: .../LISA/Unterricht/Lehrplaene/GemS-GeS/ e.g. Fachliche_Orientierung_Physik.pdf (listed) suggests own "Fachliche Orientierung" documents for GemS/GeS.

---

## Additions: Biologie and Politik/Wirtschaft

Research date 2026-11-07. Subject values used in the YAML: "Biologie", "Politik/Wirtschaft", "Arbeitslehre/WAT"; the Land's exact subject name is in title and notes. Grundschule (Sachunterricht / HSK) not repeated. Berufliche Schulen and Förderschulen excluded (Sachsen Berufliches Gymnasium Biologie, file 193, and Förderschwerpunkt Lernen Biologie, file 144, were opened by accident and are not recorded). Method as before: WebSearch/WebFetch only.

### Sachsen (SN): 11 new entries
- Landesliste 2026/27 (verified): Oberschule Biologie 2004/2009/2019/2025; Gemeinschaftskunde/Rechtserziehung 2019; Technik/Computer 2004/2009/2019; Wirtschaft-Technik-Haushalt/Soziales 2004/2009/2019. Gymnasium Biologie 2004/2007/2009/2011/2017/2019/2022/2025; GRW 2019 Lk for Landesgymnasium Sankt Afra; Technik/Computer 2004/2009/2019; fächerverbindender Grundkurs "Auf dem Weg ins Berufsleben" 2016; schulspezifisches Profil "Unternehmerische Bildung" 2025. None of these rows marked * (unchanged vs 2025/26).
- Subject names: Oberschule "Gemeinschaftskunde/Rechtserziehung" (GK, no Wirtschaft), Gymnasium "Gemeinschaftskunde/Rechtserziehung/Wirtschaft" (GRW). Economics at Oberschule sits in WTH.
- PDFs opened: OS GK (file 70; Kl. 7-10; in force 2019 Kl. 7/8, 2020 Kl. 9, 2021 Kl. 10), GY GRW (file 76; Kl. 7-10 + Jgst. 11/12 Gk and Lk), OS WTH (file 112; Kl. 7-9), OS Technik/Computer (file 123; Kl. 5-6), GY Biologie superseded Fassung 2019 (file 83; 5-12, Gk/Lk).
- The general Gymnasium GRW row was not returned by the Landesliste text extraction although the 2019 GRW PDF exists; check manually.
- Gaps: current file URLs for OS Biologie and GY Biologie Fassung 2025; GY Technik/Computer grades; Profil/Grundkurs documents.

### Sachsen-Anhalt (ST): 10 new entries
- Opened: Fachlehrplan Sekundarschule Wirtschaft (Stand 01.08.2019, base 2012; Schuljahrgänge 7/8, 9/10; CC BY-SA 3.0). It describes Hauswirtschaft, Technik and Wirtschaft as one subject group with a shared competence model for Berufswahl, so it is filed as Arbeitslehre/WAT. Fachlehrplan Wirtschaftslehre Gymnasium (Stand 15.05.2017, Anpassung 01.08.2024; Schuljahrgänge 9, 10, 11/12 Kurse 1-4; CC BY-SA 4.0).
- Listed (search index): Biologie FLP Gym 01.07.2019; Sekundarschule Technik and Hauswirtschaft 01.08.2019 (lp_sks_tech / lp_sks_hausw); Sekundarschule Biologie (pool URL needs login).
- Gemeinschaftsschule page (Stand 17.09.2026, verified): Grundsatzband GemS plus Sekundarschule Fachlehrpläne; Gymnasium requirements from Schuljahrgang 9 in the Abitur track; "Fachliche Orientierungen" for Biologie, Chemie, Deutsch, Englisch, Geschichte, Mathematik, Physik. No Gesellschaftswissenschaften subject and no Sozialkunde/Wirtschaft guidance for GemS.
- No combined "Wirtschaft und Technik" subject: Wirtschaft, Technik, Hauswirtschaft are separate plans. Gymnasium also has a Technik subject page.
- Sozialkunde (Sekundarschule and Gymnasium): subject pages exist, PDF URLs not found. Any path under bildung-lsa.de/files/ returns binary to WebFetch (even a test for a file that does not exist), so URLs guessed from the pattern cannot be checked; those are recorded only in notes.
- Gaps: Sozialkunde PDFs and grades; Biologie Sekundarschule current URL; Technik/Hauswirtschaft grades; new Sekundarschule plans (Biologie, Sozialkunde, Wirtschaft etc.) binding 2027/28, draft/Anhörung versions not located.

### Thüringen (TH): 6 new entries (all unverified)
- No Thüringen Lehrplan PDF is in the search index; the Schulportal could not be fetched. Entries follow Thüringen naming: Biologie (Regelschule and Gymnasium, after MNT 5/6), Sozialkunde (Regelschule, Gymnasium), Wirtschaft und Recht (Gymnasium), Wirtschaft-Recht-Technik (Regelschule).
- Indirect evidence only: Klett Stoffverteilungsplan PRISMA Biologie 7/8 Thüringen cites "Lehrplan für die Regelschule in Thüringen 2011"; 2026 job ads from Thüringen Regelschulen use "Wirtschaftslehre/Recht, Wirtschaftslehre/Technik".
- Gaps: everything document-level; needs a browser or ThILLM contact.

### Saarland (SL): 7 new entries (all unverified placeholders)
- site:saarland.de searches returned only the Gymnasium Lehrplan overview page; no PDFs indexed. Entries: Biologie (GemS, Gymnasium G9, Oberstufe), Gesellschaftswissenschaften (GemS), Politik or Sozialkunde (Gymnasium G9; exact name unverified), Politik/Wirtschaft Oberstufe, Arbeitslehre (GemS).
- Gaps: exact subject names (Politik vs Sozialkunde; Arbeitslehre vs Wirtschaftslehre), grades, G9 editions, GemS Novellierung effects.
