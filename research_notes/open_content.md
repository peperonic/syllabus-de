# Open and curriculum-aligned learning content, topic taxonomies and aggregators for German school Mathematik, Chemie, Physik (status November 2026)

Method note: all "verified 2026-11-07" marks mean the URL resolved through WebFetch or appeared as a live result in WebSearch on 2026-11-07. Direct curl to the sites (including robots.txt) was blocked by the sandbox egress proxy (HTTP 403 on CONNECT for every education domain tried), so robots.txt files could not be read directly. Where WebFetch itself reported "robots_disallowed", the site's robots.txt forbids generic crawlers for that path; this is noted per resource. Where WebFetch reported "client_error" (LEIFIphysik subpages, lehrerfortbildung-bw copyright page), the site refused the automated request and the page content is unverified.

## Key question 1: Serlo (serlo.org)

### Takeaway
Serlo is the strongest full-text ingest candidate: content is CC BY-SA 4.0 by contributor agreement, there is a public GraphQL API (https://api.serlo.org/___graphql) plus an AMB-compliant Metadata API, and Mathematik has a "Themen nach Lehrplan" tree with all 16 Länder and five Schularten. But in November 2026 the per-Land trees are almost all marked as still being built (only Bayern is populated without a status note and NRW has ZP exam material), so Serlo is a topic-structure source for Bayern first and a content source for everything else.

### Cited Findings
- Mathematik landing page lists six top areas (Zahlen & Größen, Terme & Gleichungen, Geometrie, Funktionen, Stochastik, Sonstiges) plus the links "Themen nach Lehrplan" (/mathe/16030/deutschland), "Abschlussprüfungen & Lösungen" and "Alle Themen"; footer links "Nutzungsbedingungen und Urheberrecht" to https://de.serlo.org/terms [verified 2026-11-07] - [Serlo Mathe](https://de.serlo.org/mathe)
- Terms: contributors must put their content "unter die Lizenz http://creativecommons.org/licenses/by-sa/4.0/"; exception: some maths exercises are not under CC BY-SA and carry a licence note below the solution; only CC BY-SA compatible content may be imported; the Gesellschaft für freie Bildung e.V. may move content to another free licence or a newer version; the terms say nothing about scraping or automated access [verified 2026-11-07] - [Serlo Terms](https://de.serlo.org/terms)
- "Themen nach Lehrplan" (Deutschland) lists all 16 Bundesländer with paths (e.g. /mathe/32455/baden-wuerttemberg, /mathe/16032/bayern, /mathe/32462/nordrhein-westfalen, /mathe/32470/thueringen); 14 are labelled as still in progress, Bayern has no status text, Nordrhein-Westfalen offers ZP NRW tasks and model solutions; Schularten listed: Gymnasium (/mathe/16042/gymnasium), Realschule, Mittelschule (Hauptschule), FOS & BOS, Hochschule; also "Serlo-Lehrplan" (/mathe/148069/serlo-lehrplan) and "Bundesweite Abituraufgaben (vom IQB)" (/mathe/330177/..., marked coming soon); no Klassenstufen on that page [verified 2026-11-07] - [Serlo Lehrplan tree](https://de.serlo.org/mathe/16030/deutschland)
- GitHub organisation has 120 repositories; api.serlo.org is the "Public GraphQL API" (Apache-2.0) with the endpoint https://api.serlo.org/___graphql; frontend (Next.js, Apache-2.0); database-layer and db-migrations are archived; no database-dump repository is listed on the first page; the .github profile repo is CC-BY-SA-4.0 and says learning materials "can be used, shared and modified by everybody" [verified 2026-11-07] - [github.com/serlo](https://github.com/serlo); [api.serlo.org repo](https://github.com/serlo/api.serlo.org)
- Metadata API page: "Fully compliant with the state of the art AMB standard", "Easy to use GraphQL interface", "Retrieve metadata of all our articles, videos, courses and quizzes", counts 3,000+ articles, 600+ courses, 4,000+ exercises, "Licensed under, CC-BY-SA 4.0", usage "completely free of cost"; technical documentation is delegated to the GitHub wiki [verified 2026-11-07] - [Serlo Metadata API](https://de.serlo.org/metadata)
- The api.serlo.org README documents only local development (yarn start, playground at localhost:3000/___graphql, yarn auth, Ory Kratos, Keycloak SSO for nbp and vidis providers), not public rate limits or dumps [verified 2026-11-07] - [README](https://github.com/serlo/api.serlo.org)

### Inferences
- Taxonomy structure: Serlo URLs are /<fach>/<taxonomy-id>/<slug>; the taxonomy is a tree of TaxonomyTerm nodes (Fach > Lehrplan-Land > Schulart > Jahrgang > Thema) exposed via the GraphQL uuid query. The Metadata API delivers AMB JSON-LD per resource, which is the most convenient bulk route (no scraping) and carries licence per item, so the few non-CC exercises can be filtered out automatically.
- Because the Lehrplan views for 14 Länder are placeholders, Serlo cannot be used alone to prove topic coverage per Land; use its Bayern tree (LehrplanPLUS-aligned, historically Serlo's origin) and the generic "Alle Themen" tree as a cross-check list, and ingest article and exercise text for the knowledge base.

### Gaps
- Chemie and Physik on Serlo (de.serlo.org/chemie, de.serlo.org/physik) were not fetched in this session; their depth and Lehrplan trees are unverified.
- Exact GraphQL metadata query syntax, pagination and rate limits were not confirmed (the wiki page https://github.com/serlo/api.serlo.org/wiki/Metadata-API did not resolve to documentation via WebFetch).
- Whether anonymised MySQL dumps are still offered to developers was not confirmed (database-layer repo is archived).

## Key question 2: WirLernenOnline / OpenEduHub

### Takeaway
WirLernenOnline (edu-sharing.net e.V., BMBF and EU funded) is a metadata aggregator and search engine over OER, not a content host; its own editorial content is CC BY 4.0, partner content keeps its own licence. The valuable asset for topic coverage is the OpenEduHub SKOS vocabulary set (CC0, ~90 Turtle files incl. discipline, educationalContext, schoolType, oehTopics), published at w3id.org/openeduhub/vocabs and browsable at vocabs.openeduhub.de. No Lehrplan (per-Land) vocabulary exists there.

### Cited Findings
- Operator: "edu-sharing.net e.V.", Am Horn 21a, 99425 Weimar, gemeinnütziger Verein, Amtsgericht Weimar VR 131198; content created by the provider "stehen unter der Creative-Commons-Lizenz CC BY 4.0"; for partner content "achten Sie bitte auf die Lizenzbedingungen der verlinkten Webseiten"; no metadata licence, API or automated-access statement in the Impressum [verified 2026-11-07] - [WLO Impressum](https://wirlernenonline.de/impressum/)
- Homepage: OER search engine and community for Kita, Schule, Berufsbildung, Hochschule; funding logos EU and BMBF; Wikimedia and Bündnis Freie Bildung as partners; 3,658 Themensammlungen; "Die WLO-Inhalte sind offen für jeden, der eine Schnittstelle in Betrieb nimmt"; "Bei uns ist alles open (source)"; search UI at https://suche.wirlernenonline.de/search/de/search; plugins page https://wirlernenonline.de/plugins/ [verified 2026-11-07] - [WLO](https://wirlernenonline.de/)
- 27 Fachportale listed; Mathematik https://wirlernenonline.de/portal/mathematik/, Chemie https://wirlernenonline.de/portal/chemie/, Physik https://wirlernenonline.de/portal/physik/; no Bundesland filter or Lehrplan mapping shown on the overview page [verified 2026-11-07] - [Bildungsmaterialien overview](https://wirlernenonline.de/bildungsmaterialien/)
- vocabs.openeduhub.de is a SkoHub-Vocabs site generated from GitHub (footer: skohub-io/skohub-docker-vocabs; Impressum hbz-nrw.de) [verified 2026-11-07] - [OpenEduHub Vocabs](https://vocabs.openeduhub.de/)
- openeduhub/oeh-metadata-vocabs: SKOS vocabularies as Turtle (.ttl), about 90 files, licence CC0-1.0, published under w3id.org/openeduhub/vocabs, built and deployed via GitHub Actions and SkoHub; files include discipline, oehTopics, topical_categories, educationalContext, educationalLevel, schoolType, intendedEndUserRole, learningResourceType (and new_lrt), medienkompetenzrahmenNRW, orientierungsrahmenNRW; no separate Mathematik/Physik/Chemie Themenbaum file and no Lehrplan file [verified 2026-11-07] - [oeh-metadata-vocabs](https://github.com/openeduhub/oeh-metadata-vocabs)
- openeduhub organisation: 66 repositories incl. oeh-search-etl (Scrapy, Postgres, Elasticsearch crawler backend, Python), oeh-search-frontend (Angular), oeh-search-elasticsearch-relay (GraphQL), metadata-agent-api, tutor-chatbot (Apache-2.0), lernpfadeditor (Apache-2.0), wlo-quellenliste (Apache-2.0) [verified 2026-11-07] - [github.com/openeduhub](https://github.com/openeduhub)

### Inferences
- WLO is built on edu-sharing, so the public edu-sharing REST API of the WLO repository (historically https://redaktion.openeduhub.net/edu-sharing/rest/) is the bulk route for metadata; this endpoint was not fetched in this session and should be treated as unverified.
- The subject Fachportale (Mathematik, Chemie, Physik) expose editorially curated topic pages ("Themensammlungen") which are effectively Fachsystematiken; harvesting their titles via the edu-sharing API gives a topic list usable for cross-check, while the linked materials have heterogeneous licences and must be filtered by the per-item licence field before any full-text ingest.
- The CC0 vocabularies are safe to embed verbatim in the knowledge base as structure (discipline codes, schoolType, educationalContext, oehTopics).

### Gaps
- Content of oehTopics (whether it contains per-subject topic trees for Mathematik, Chemie, Physik) was not inspected.
- No explicit WLO statement on metadata licence (CC0 is customary for edu-sharing metadata but not confirmed).
- Edu-sharing REST API URL and any rate limits unverified.

## Key question 3: ZUM (zum.de, unterrichten.zum.de, apps.zum.de)

### Takeaway
ZUM-Unterrichten is a MediaWiki 1.43 wiki by the volunteer association Zentrale für Unterrichtsmedien im Internet e.V. with 22 subjects incl. Mathematik, Physik, Chemie under CC BY-SA 4.0 (footer logo linked to the CC deed); it has no Lehrplan or Bundesland navigation, so it is a full-text ingest candidate but not a coverage checklist.

### Cited Findings
- ZUM-Unterrichten is "eine offene, nicht-kommerzielle Plattform für Unterrichtsmaterialien und -ideen", a project of the Zentrale für Unterrichtsmedien im Internet e.V.; 22 subjects; Mathematik https://unterrichten.zum.de/wiki/Mathematik, Physik https://unterrichten.zum.de/wiki/Physik, Chemie https://unterrichten.zum.de/wiki/Chemie; generator meta tag "MediaWiki 1.43.11"; footer licence logo "Logo Lizenz CC BY-SA" linking to https://creativecommons.org/licenses/by-sa/4.0/deed.de; no Lehrplan or Bundesland navigation; main page viewed about 8.17 million times [verified 2026-11-07] - [ZUM-Unterrichten Hauptseite](https://unterrichten.zum.de/wiki/Hauptseite)
- ZUM portal lists ZUM-Unterrichten, ZUM-Apps (http://apps.zum.de, H5P hosting), ZUM-Tools, ZUM-Projekte (wiki), ZUM-Grundschule, ZUM Deutsch Lernen; volunteer-run since 1997; a Nov 2026 blog teaser describes browser apps "als OER unter der Lizenz CC BY-SA 4.0"; no general licence policy page linked from the portal [verified 2026-11-07] - [zum.de/portal](https://www.zum.de/portal/)

### Inferences
- As a standard MediaWiki, unterrichten.zum.de exposes api.php (action=query, generator=allpages, prop=revisions) and Special:Export; this is the preferred bulk route over HTML scraping (unverified in session, standard MediaWiki behaviour).
- ZUM-Apps (H5P) content is licensed per item by uploaders; treat per item.

### Gaps
- Page count for Mathematik/Physik/Chemie not retrieved.
- Robots.txt of unterrichten.zum.de not readable (proxy block).

## Key question 4: LEIFIphysik (leifiphysik.de)

### Takeaway
LEIFIphysik has exactly the navigation the learning assistant needs for physics (per Bundesland and Klassenstufe pages such as /baden-wuerttemberg/9-klasse, /berlin/10-klasse, plus Teilgebiete), but it is not OER: the site refused automated fetches of its Nutzungsbedingungen and Impressum, legacy.leifiphysik.de is robots-disallowed, and no CC licence is visible. Use its topic lists as a manual cross-check only; do not ingest.

### Cited Findings
- Homepage: materials, experiments, tasks, tests; navigation "Inhalte nach Klassenstufe und Bundesland" and "Inhalte nach Teilgebieten der Physik"; LekkerWissen explainer videos; no licence text in the fetched content [verified 2026-11-07] - [LEIFIphysik](https://www.leifiphysik.de/)
- Live URLs found via site search: https://www.leifiphysik.de/nutzungsbedingungen, https://www.leifiphysik.de/impressum, https://www.leifiphysik.de/ueber-leifiphysik, https://www.leifiphysik.de/app, https://www.leifiphysik.de/baden-wuerttemberg, https://www.leifiphysik.de/baden-wuerttemberg/9-klasse, https://www.leifiphysik.de/berlin/10-klasse, https://www.leifiphysik.de/hessen, https://www.leifiphysik.de/saarland, https://www.leifiphysik.de/rheinland-pfalz, https://www.leifiphysik.de/schleswig-holstein, https://legacy.leifiphysik.de/saarland/lehrplaene, https://legacy.leifiphysik.de/teilgebiete [URLs seen in search results 2026-11-07; content unverified] - [search result set](https://www.leifiphysik.de/nutzungsbedingungen)
- WebFetch of /nutzungsbedingungen, /impressum and /baden-wuerttemberg returned "client_error" (site refused the automated request); WebFetch of legacy.leifiphysik.de/saarland/lehrplaene returned "robots_disallowed" [2026-11-07].
- Joachim Herz Stiftung legal notice exists at https://www.joachim-herz-stiftung.de/en/legal-notice [URL seen in search results 2026-11-07; publisher relation not verified on leifiphysik.de in this session].

### Inferences
- The URL pattern /<bundesland>/<n>-klasse shows the Lehrplan mapping is per Bundesland and Jahrgangsstufe (not visibly per Schulart in URLs); the legacy site had explicit "Lehrpläne" pages per Land.
- The combination of refused automated access and the absence of any CC statement means LEIFIphysik must be treated as all rights reserved for knowledge-base purposes; a human can still read the per-Land topic lists to validate the physics topic checklist.

### Gaps
- Exact wording of the Nutzungsbedingungen (reuse rights, AI/data-mining clause) could not be retrieved.
- Which Schularten are distinguished per Land was not confirmed.

## Key question 5: Chemistry sites used in German schools

### Takeaway
Of the classic chemistry sites only the Göttingen/Oldenburg "Unterrichtsmaterialien Chemie" collection is openly licensed (CC BY-NC-SA 3.0, 2,123 materials sorted by grade bands 5-6 to 11-13, "angelehnt an das Kerncurriculum"); seilnacht.com requires a paid licence for teachers and forbids copying, Prof. Blumes Bildungsserver is copyrighted by the author (published with Cornelsen), chemie-schule.de is "© chemie-schule.de 2026", and chids.de blocks crawlers. Chemistry therefore needs its topic checklist from the Lehrpläne themselves plus Wikibooks/Serlo, with the Göttingen database as the main experiment corpus (non-commercial use only).

### Cited Findings
- unterrichtsmaterialien-chemie.uni-goettingen.de: run by Timm Wilke and Thomas Waitz (Universität Göttingen and Carl von Ossietzky Universität Oldenburg); 1,420 experiments, 261 worksheets, 402 lab reports, 2 WebQuests, 40 videos; by grade: Klassen 5-6 (654), 7-8 (519), 9-10 (477), 11-13 (473); total 2,123; "angelehnt an das Kerncurriculum"; "Jedes Protokoll gibt es als PDF und als Word-Datei zum Anpassen an Ihre Lerngruppe"; H/P statements and GHS pictograms; "Lizenz CC BY-NC-SA 3.0" linked to https://creativecommons.org/licenses/by-nc-sa/3.0/deed.de [verified 2026-11-07] - [Unterrichtsmaterialien Chemie](https://unterrichtsmaterialien-chemie.uni-goettingen.de/)
- seilnacht.com homepage: "Für die Nutzung durch Lehrkräfte im Unterricht ist eine gültige Lizenz notwendig" (licence shop https://www.seilnacht.ch/shopw/wahlnat.html); legal pages https://www.seilnacht.com/lizenzen.html and https://www.seilnacht.com/nachricht.html; scope: Chemikaliendaten, Periodensystem, Farbe lexicon, Experimente, Didaktik, Physik section, Biology via digitalefolien.de [verified 2026-11-07] - [seilnacht.com](https://www.seilnacht.com/)
- seilnacht lizenzen.html: "Die Dateien dürfen nicht veröffentlicht oder im Internet angeboten werden", "sie dürfen nicht kopiert, weitergegeben oder verliehen werden", single licences are personal, school licences cover all staff of an institution; but "Die Fachinhalte und die Experimentier-Ideen des Werks sind nicht urheberrechtlich geschützt"; disclaimer "Die aufgeführten Daten zu Rechtshinweisen sind nicht rechtsverbindlich"; no Creative Commons [verified 2026-11-07] - [seilnacht Lizenzen](https://www.seilnacht.com/lizenzen.html)
- chemieunterricht.de/dc2 (Prof. Blumes Bildungsserver für Chemie): page metadata names Rüdiger Blume as author and copyright holder and Cornelsen Verlag as publisher; large collection of "Experimenten und Hintergrundtexten" on Umweltchemie, Alltagschemie, Brennstoffzellen, Farbstoffe, Sicherheit im Unterricht etc.; no licence statement, no Creative Commons [verified 2026-11-07] - [Prof. Blumes Bildungsserver](https://www.chemieunterricht.de/dc2/)
- chemie-schule.de: Lexikon, Anorganische Chemie chapters 1-59 (Stoffe und Modelle, Verbrennung, Atombau und PSE, Bindung, Halogene und Alkalimetalle, Säuren und Basen, industrielle Chemie), Organische Chemie section, periodic table, quiz; audience "Schüler und Studenten"; footer "© chemie-schule.de 2026"; photos from Fotolia and DepositPhotos; Impressum at /stnfo.php; no CC statement [verified 2026-11-07] - [chemie-schule.de](https://www.chemie-schule.de/)
- chids.de: WebFetch returned "robots_disallowed" (crawling forbidden by robots.txt) [2026-11-07] - [chids.de](https://www.chids.de/)

### Inferences
- seilnacht's statement that facts and experiment ideas are not copyright-protected is consistent with German law (ideas and facts are free, expression is protected); its chapter structure can be consulted as a cross-check of chemistry topic names, but no text may be copied.
- The Göttingen grade bands (5-6, 7-8, 9-10, 11-13) are a practical scaffold for a chemistry topic checklist; NC licence excludes commercial deployment of the knowledge base unless the operator is non-commercial.
- Prof. Blume's "Tipp des Monats" archive is a frequently used teacher reference but, being a Cornelsen-published copyrighted work, is cross-check only.

### Gaps
- Chemie im Kontext (ChiK) materials: not researched in this session; licence unknown.
- chids.de experiment count, structure and licence: unverified (robots block).
- No open German chemistry textbook beyond the Wikibooks Chemie shelf was identified.

## Key question 6: Physics and maths OER (PhET, GeoGebra, Wikibooks, Wikiversity, Wikipedia, mathe-online, realmath, Aufgabenfuchs, dwu, Khan Academy)

### Takeaway
Wikimedia projects (Wikibooks Regal Schule with Mathematik Grundschule/Mittelstufe/Oberstufe, Physik and Chemie Mittelstufe/Oberstufe shelves; Wikipedia) are CC BY-SA and have dumps, so they are ingestible; PhET is open (CC BY, verified URL but text not retrieved) but is simulations, not topic lists; GeoGebra's platform is non-commercial-only under GeoGebra's own terms; realmath, Aufgabenfuchs, dwu and mathe-online are long-standing teacher sites with no open licence found; Khan Academy Deutsch is CC BY-NC-SA (unverified here). None of these carries a per-Land Lehrplan mapping.

### Cited Findings
- Wikibooks Regal:Schule lists shelves Mathematik (Grundschule, Mittelstufe, Oberstufe und Berufsschule), Physik (Mittelstufe, Oberstufe und Berufsschule), Chemie (Mittelstufe, Oberstufe und Berufsschule) with a status legend from "00% fertig Buchanfang" to "Ausgezeichnetes Buch" [verified 2026-11-07] - [Wikibooks Regal:Schule](https://de.wikibooks.org/wiki/Regal:Schule)
- GeoGebra licence page: installers and web services "for non-commercial purposes only, provided you acknowledge GeoGebra"; "The GeoGebra source code is licensed to you under the terms of the EUPL v1.2"; language files, documentation, UI images under "Creative Commons Attribution-NonCommercial-ShareAlike license (version 4.0 or later)"; "Whether a particular use of the GeoGebra Materials is 'non-commercial' depends on the use, not the user"; "Any use of GeoGebra for a commercial purpose is subject to and requires a special license"; the page does not state the licence of user-created materials [verified 2026-11-07] - [GeoGebra License](https://www.geogebra.org/license)
- PhET /de/licensing page resolved but only header/footer were retrievable: "© 2026 University of Colorado. All Rights Reserved." with links to Privacy Policy and Terms of Use under /de/; the /en/licensing fetch failed due to output size [verified URL 2026-11-07; licence text unverified] - [PhET licensing (de)](https://phet.colorado.edu/de/licensing)
- WebSearch for realmath.de, Aufgabenfuchs and dwu-Unterrichtsmaterialien licence terms returned only third-party pages (e.g. homeandsmart.de articles on realmath.de) and no licence statements [2026-11-07] - [realmath background article](https://www.homeandsmart.de/realmath-de-mathe-lernen)

### Inferences
- Wikimedia content (Wikibooks, Wikiversity, Wikipedia de) is under CC BY-SA 4.0 per the Wikimedia Foundation Terms of Use and is available as XML dumps from dumps.wikimedia.org and via the MediaWiki API; this is standard knowledge, not verified on-page in this session (the Mathe für Nicht-Freaks fetch failed on URL encoding).
- Mathe für Nicht-Freaks targets university first-year mathematics (Analysis, Lineare Algebra) and is less useful for Grundschule to Sek I coverage; the Wikibooks school shelves are the relevant ones, but many are incomplete per the status legend.
- PhET HTML5 simulations are CC BY 4.0 with German translations (widely documented); they are useful as linked media, not as topic structure.
- realmath.de, Aufgabenfuchs, dwu and mathe-online should be treated as all rights reserved (no open licence found); their topic menus mirror Bavarian Realschule (realmath) and general Sek I maths and can serve only as manual cross-checks.

### Gaps
- Exact PhET licence text and GeoGebra Materials user-content licence (CC BY-SA vs. CC BY-NC-SA) not retrieved.
- Wikibooks footer licence and individual book statuses for Physik/Chemie not retrieved.
- Licence statements for realmath.de, aufgabenfuchs.de, dwu-unterrichtsmaterialien.de, mathe-online.at and de.khanacademy.org were not fetched (unverified).

## Key question 7: Aggregators and media portals (MUNDO, Elixier, edutags, OERSI, GEI Curricula Workstation and edumedia-depot)

### Takeaway
The GEI Curricula Workstation no longer exists as a separate site: curricula-workstation.edumeres.net now 302-redirects into the GloTREC catalogue (glotrec.gei.de), which is protected by the Anubis anti-bot wall; the underlying PDFs sit in the DSpace repository edumedia-depot.gei.de (community "Curriculare Dokumente", collection "Curricula"), which is fetchable. The 2014 description names history, geography, social studies and religion/ethics as the subject focus, and no Mathematik/Chemie/Physik Lehrplan was confirmed. MUNDO (FWU, SODIX, DigitalPakt) is a JavaScript-only OER media library with an API in the SODIX architecture; Elixier is the Landesbildungsserver metadata pool with a query-parameter search but no documented API; OERSI is Hochschule-only; edutags is social bookmarking.

### Cited Findings
- https://curricula-workstation.edumeres.net/ and /lehrplaene/lehrplan/ return HTTP 302 to https://glotrec.gei.de/cat/Search/Results?filter[]=textbook_catalogue_str:"GEI"&type=AllFields [verified 2026-11-07] - [Curricula Workstation](https://curricula-workstation.edumeres.net/)
- glotrec.gei.de answers automated requests with "Access Denied" from Anubis bot protection [verified 2026-11-07] - [GloTREC](https://glotrec.gei.de/cat/Search/Results?filter%5B%5D=textbook_catalogue_str%3A%22GEI%22&type=AllFields)
- itbc.gei.de/Record/gei1681048752 ("Lehrplan Grundschule - Deutsch") 302-redirects to https://glotrec.gei.de/cat/Record/gei1681048752; other itbc records found: "Lehrplan Geschichte - Gymnasiale Oberstufe", "Lehrplan Gymnasium - Evangelische Religion", "Lehrplan Berufliches Gymnasium - Evangelische Religion" [verified 2026-11-07] - [itbc record](https://itbc.gei.de/Record/gei1681048752)
- GEI news (2014): Curricula Workstation holds "a current total of almost 5,000" curricula from Germany "and a range of other countries worldwide"; subjects history, geography, social studies/political education, ethics/religious education; only some curricula available electronically; filters by country, education level, subject, year; acts as long-term archive; public beta June 2013, live March 2014 [verified 2026-11-07] - [GEI news](https://www.gei.de/en/gei-news/details/a-collection-of-curricula-from-around-the-world-the-curricula-workstation-is-live)
- edumedia-depot.gei.de is a DSpace repository ("DSpace Repositorium (Manakin basiert)"); item handle 11163/6301 "Lehrplan 21" (2016) in community "Curriculare Dokumente", collection "Curricula", PDF 1687017190.pdf (62.77 MB), no rights statement shown [verified 2026-11-07] - [edumedia-depot item](https://edumedia-depot.gei.de/handle/11163/6301)
- edumedia-depot item "Lehrplan für das Gymnasium: 2014-2018" (handle 11163/6324, PDF 1687229546.pdf 570.89 KB, dc.type Other, accessioned 2020-01-27, no dc.rights) is served under the DSpace 7 path /items/5a85119f-34ce-428a-a121-0709ba8332fc/full [verified 2026-11-07] - [edumedia-depot item full](https://edumedia-depot.gei.de/items/5a85119f-34ce-428a-a121-0709ba8332fc/full)
- MUNDO (bpb, 23.11.2020): developed by FWU; part of the SODIX infrastructure commissioned with DigitalPakt Schule funds; materials described as "offen, lizenz- und qualitätsgeprüft"; 14 subjects incl. maths; mostly videos from public broadcasters plus PDFs; SODIX components: editor, Content Adapter, Content Hub, and "an API that makes the data available as teaching content"; MUNDO hosts materials itself whereas WirLernenOnline links out [verified 2026-11-07] - [bpb on MUNDO](https://www.bpb.de/lernen/digitale-bildung/werkstatt/321605/bildungsplattformen-wie-funktionieren-mundo-und-co)
- mundo.schule homepage delivers only a title and viewport tag to non-JS clients [verified 2026-11-07] - [MUNDO](https://mundo.schule/); further FWU documents: [FWU Projekte 2025](https://web2025.fwu.de/wp-content/uploads/2025/11/FWU_Ueberblick_Projekte.pdf), [FWU Katalog Projekte 2026](https://fwu.de/wp-content/uploads/2026/03/FWU_Katalog_PROJEKTE_2026.pdf), [KMK news](https://www.kmk.org/aktuelles-1/artikelansicht/bildungsportal-mundo-geht-online.html) [URLs from search 2026-11-07, content unverified]
- Elixier simple search: categories "Schule", "math.-naturwiss. Fächer", "Grundschule", "fachunabh. Bildungsthemen", subcategories incl. Mathematik; result lists are driven by URL parameters feldname, feldinhalt, suche=einfach|erweitert; no API, record count, OER filter or metadata licence shown [verified 2026-11-07] - [Elixier](https://www.bildungsserver.de/elixier/)
- edutags: "Social Bookmarking-Plattform"; "Durch edutags haben Sie die Möglichkeit, Lesezeichen zu Lernressourcen im Web zu speichern, zu suchen und zu teilen"; no operator, API or licence in fetched content [verified 2026-11-07] - [edutags](https://www.edutags.de/)
- OERSI: offered since 2020 by hbz and TIB; "eine Suchmaschine für offene Bildungsmaterialien in der Hochschulbildung"; harvests and homogenises metadata, does not host; open API (https://oersi.org/pages/de/docs/integrate/metadata-search/) and regular metadata dumps (https://oersi.org/pages/de/docs/integrate/metadata-dump/); development on https://gitlab.com/oersi [verified 2026-11-07] - [OERSI about](https://oersi.org/resources/pages/de/about/)

### Inferences
- edumedia-depot is DSpace 7 (UUID item paths), so an OAI-PMH endpoint (/oai/request) and REST API (/server/api) are very likely available for harvesting the "Curricula" collection metadata and bitstreams; unverified. The Lehrpläne themselves are official documents (amtliche Werke, § 5 UrhG) regardless of missing dc.rights.
- GloTREC's Anubis wall means the catalogue must be browsed by a human; the repository is the machine route. Whether Mathematik/Chemie/Physik Lehrpläne are in the GEI collection remains unconfirmed; the 2014 scope and the sample records point to humanities subjects, so the GEI route is a cross-check for finding historical/other-Land PDFs, not a primary source for MINT.
- MUNDO's per-item licence display and SODIX API are only reachable via the JS app or FWU partner agreements; treat as cross-check/linking, not ingest.
- Elixier can be scraped via its query parameters, but it is a metadata pool (titles, descriptions, links, Bildungsebene), useful as a cross-check of which topics the Landesbildungsserver tag, not as content.

### Gaps
- Count and subject distribution of the edumedia-depot "Curricula" collection; OAI-PMH availability.
- MUNDO item count, licence display and API documentation (JS-only site).
- Elixier record count and any partner XML interface.
- edutags operator (DIPF/Universität Duisburg-Essen) and data licence not confirmed on-page.

## Key question 8: Landesbildungsserver with curriculum-aligned material trees

### Takeaway
Major change in 2026: the Landesbildungsserver Baden-Württemberg (schule-bw.de) was shut down on 30.09.2026, its content archived and redirected to the Lehrkräftefortbildungsserver lehrerfortbildung-bw.de, which keeps Mathematik, Chemie and Physik trees organised by Schulart and Bildungsplan 2016 and links a "Copyright" page whose URL indicates CC BY-SA. Berlin-Brandenburg's RLP-Online publishes the Rahmenlehrplan 1-10 Teil C for Mathematik, Chemie, Physik with materials; Hessen's Lernarchiv is a link collection without a visible licence; mebis now redirects to the ByCS "Klickpunkt Schule" magazine. Other Landesbildungsserver (NiBiS, Hamburg, RLP, Thüringen, Sachsen) were not reachable in this session.

### Cited Findings
- lehrerfortbildung-bw.de/willkommen/: "Landesbildungsserver schule-bw.de (LBS)" was shut down on 30.09.2026, content archived, support materials now on the Lehrkräftefortbildungsserver (LFBS); old LBS links redirect here; trees: Mathematik https://lehrerfortbildung-bw.de/u_matnatech/mathematik/ (gs, gym with bp2016 and bp2004, bs incl. BEJ, 2BFS, 6BG, Berufskolleg, sueb), Chemie https://lehrerfortbildung-bw.de/u_matnatech/chemie/ (gym/bp2016, gym/bp2004, gym/weiteres, bs/6bg), Physik https://lehrerfortbildung-bw.de/u_matnatech/physik/ (gym/bp2016, gym/bp2004, gym/weiteres, bs/2bfs, bs/6bg); footer "Copyright" link https://lehrerfortbildung-bw.de/lak_lfb/impressum/copyright/ccbysa.html [verified 2026-11-07; copyright page itself returned client_error] - [LFBS Willkommen](https://lehrerfortbildung-bw.de/willkommen/)
- https://www.schule-bw.de/ returns 302 to https://lehrerfortbildung-bw.de/willkommen/ [verified 2026-11-07] - [schule-bw.de](https://www.schule-bw.de/)
- Hessischer Bildungsserver Lernarchiv: "Materialien für Lehrende und Lernende" organised by Grundschule and Sekundarbereich; self-learning platforms mauswiesel and select; entries are links (some to mundo.schule, medienzentrum-frankfurt.de); footer only Impressum (https://djaco.bildung.hessen.de/impress.html), Datenschutz, Haftungsausschluss; no licence statement [verified 2026-11-07] - [Lernarchiv Hessen](https://lernarchiv.bildung.hessen.de/)
- RLP-Online (Bildungsserver Berlin-Brandenburg): Rahmenlehrplan Jahrgangsstufen 1-10 for Berlin and Brandenburg with Teil A, Teil B and Teil C (one section per subject incl. Mathematik, Chemie, Physik, listing competences and binding/elective topics); offers "weitere Materialien, Aufgabenbeispiele und Filtermöglichkeiten"; no licence statement on the landing page [verified 2026-11-07] - [RLP-Online](https://bildungsserver.berlin-brandenburg.de/rlp-online)
- https://mebis.bycs.de/ returns 302 to https://klickpunktschule.bycs.de/mebis-magazin [verified 2026-11-07] - [mebis](https://mebis.bycs.de/)
- Sandbox proxy log recorded CONNECT rejections for www.schulportal-thueringen.de and bildung.thueringen.de (policy denial), so Thüringer Schulportal could not be inspected [2026-11-07].

### Inferences
- lehrerfortbildung-bw.de is now the single Baden-Württemberg source for curriculum-aligned MINT material trees (Bildungsplan 2016 per Klassenstufe for Gymnasium); the ccbysa.html URL strongly suggests CC BY-SA, which would allow ingest with attribution, but the exact version and exceptions must be read by a human before ingest.
- Landesbildungsserver pages are mostly server-rendered HTML with sitemaps; they are scrapable but licences differ per Land and often per page (many Länder publish only "alle Rechte vorbehalten" plus CC-marked individual materials).
- RLP-Online is primarily the curriculum itself (covered by the official-curricula research stream) plus implementation materials; treat the materials as cross-check unless a CC statement is found.

### Gaps
- NiBiS (nibis.de), Hamburger Bildungsserver (bildungsserver.hamburg.de), Bildungsserver Rheinland-Pfalz Fachportale, Thüringer Schulportal Mediothek, Sachsen OPAL Schule: not fetched; licences and structures unverified.
- Exact CC BY-SA version and exceptions on lehrerfortbildung-bw.de.
- Whether ByCS/mebis Mediathek is public without login.

## Key question 9: Commercial platforms with curriculum mapping

### Takeaway
sofatutor shows its Mathematik topic lists for Vorschule and Klassen 1-13 without login and markets "angepasst an die Lehrpläne der Bundesländer" without naming how; it is paywalled (30-day trial) and has no reuse licence, so it is at most a human-readable cross-check of topic naming. simpleclub, Studyflix, Learnattack, ANTON, bettermarks, Schlaukopf and Klassenarbeiten.de were only seen via third-party comparison pages in this session; none is ingestible.

### Cited Findings
- sofatutor Mathematik: "Wähle deine Klassenstufe" menu for Vorschule and Klassen 1-13, topic list grouped 1.-2., 3.-4., 5.-6., 7.-8., 9.-13. Klasse, visible without login; claims "Von Expert*innen erstellt und angepasst an die Lehrpläne der Bundesländer", "werden von echten Lehrern auf Didaktik und Rahmenlehrplankonformität geprüft", meta description "Lehrplangerecht & qualitätsgeprüft!"; "30 Tage kostenlos testen"; no licence or reuse statement; links to AGB, Impressum, Datenschutz [verified 2026-11-07] - [sofatutor Mathematik](https://www.sofatutor.com/mathematik)
- Third-party comparisons of ANTON, sofatutor, Learnattack, Studienkreis, GoStudent exist at trusted.de and heise.de; Studyflix and simpleclub appear in competitor listings [URLs from search 2026-11-07; content unverified] - [trusted.de anton vs sofatutor](https://trusted.de/anton-vs-sofatutor); [heise Lern-Apps](https://www.heise.de/tipps-tricks/Lern-Apps-fuer-Schueler-und-Studenten-4710975.html)

### Inferences
- Commercial platforms' public topic indices (sofatutor, simpleclub, Studyflix, Learnattack, Schlaukopf, Klassenarbeiten.de) are typically visible without login for SEO reasons and can be read manually to confirm that a topic list for a given grade is complete; their texts, videos and exercises are copyrighted and their AGB usually forbid automated extraction, so "avoid" for ingest.

### Gaps
- Public visibility of topic lists and explicit Bundesland selectors for simpleclub, Studyflix, Learnattack, ANTON, bettermarks, Schlaukopf and Klassenarbeiten.de were not verified in this session.

## Key question 10: Legal statements, robots.txt and bulk routes (cross-cutting)

### Takeaway
Three tiers emerge: (1) safe full-text ingest with attribution and share-alike: Serlo (CC BY-SA 4.0, GraphQL/Metadata API), ZUM-Unterrichten (CC BY-SA 4.0, MediaWiki API), Wikibooks/Wikipedia (CC BY-SA, dumps), WLO editorial text (CC BY 4.0), OpenEduHub vocabularies (CC0), lehrerfortbildung-bw.de (CC BY-SA per URL, to confirm); (2) non-commercial-only ingest: Göttingen Unterrichtsmaterialien Chemie (CC BY-NC-SA 3.0), GeoGebra materials (NC terms), Khan Academy (NC, unverified); (3) cross-check only or avoid: LEIFIphysik, seilnacht, Prof. Blume, chemie-schule, chids, MUNDO (JS app), commercial platforms. robots.txt could not be read directly because the sandbox proxy blocked curl to all education domains; WebFetch's own robots handling flagged chids.de and legacy.leifiphysik.de as disallowed.

### Cited Findings
- Sandbox: every curl to the 29 education domains failed with "CONNECT tunnel failed, response 403" (proxy policy), so robots.txt could not be read [2026-11-07, local proxy status endpoint].
- WebFetch "robots_disallowed": https://www.chids.de/ and https://legacy.leifiphysik.de/saarland/lehrplaene [2026-11-07].
- WebFetch "client_error" (site refused automated client): https://www.leifiphysik.de/nutzungsbedingungen, https://www.leifiphysik.de/impressum, https://www.leifiphysik.de/baden-wuerttemberg, https://lehrerfortbildung-bw.de/lak_lfb/impressum/copyright/ccbysa.html [2026-11-07].
- Bot wall: glotrec.gei.de (Anubis) [2026-11-07].
- Serlo terms contain no anti-scraping clause; WLO Impressum contains none; seilnacht forbids copying and republication of files [see sections above].

### Inferences
- Preferred bulk routes: Serlo Metadata API/GraphQL (no scraping); MediaWiki api.php for ZUM-Unterrichten; Wikimedia dumps; GitHub clone for openeduhub/oeh-metadata-vocabs; edu-sharing REST for WLO metadata; DSpace OAI-PMH for edumedia-depot; HTML with sitemaps for lehrerfortbildung-bw.de.
- Before any ingest the project should read robots.txt from a normal network for: de.serlo.org, unterrichten.zum.de, lehrerfortbildung-bw.de, wirlernenonline.de, edumedia-depot.gei.de.

### Gaps
- No robots.txt content was obtained for any site in this session.
