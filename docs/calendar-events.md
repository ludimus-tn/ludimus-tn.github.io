# Calendar events

## Creating events in the public calendar

### Checklist

1. Add:
   1. A comprehensive title, e.g. `Serata giochi da tavolo @ Locanda del Gatto Gordo`, or `Escape Room @ CRV Ala`. Something that makes sense to a visitor.
   2. The START and END date and time, and make sure they are correct. Use `Europe/Rome` even when editing abroad.
   3. Set repeat for a series, if applicable.
2. Fill the [description](#description) using the example below. Include a public image link for `Locandina` if you have one.

If an event spans multiple days, repeat it, rather than having a full-day event. The script generates one page per day, and the website shows each day separately.

### Description

You MAY start an event with a sentence that MUST start with `Vi aspettiamo`.
Essentially, a public invitation which will be used in Telegram and on the website. It should be short, clear and friendly.

The rest of the description is a list of fields, one per line, in the format `X: y...`.
Everything is public: keep internal notes and private contact information elsewhere.

```text
Vi aspettiamo alla Locanda del Gatto Gordo per una serata di giochi in compagnia!

Informazioni:
Attività: Giochi da tavolo
Dove: Trento, Locanda del Gatto Gordo
Come arrivare: https://maps.app.goo.gl/SkH39dic7ntw4NcG7
Come partecipare: Accesso libero, non serve prenotare
Costo: Gratuito
A chi è rivolto: Tutti
```

| Field               | What to write                                                  | Examples of values                                                                                                                                                   |
| ------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Attività`          | **Required.** Pick a template.                                 | `Ludoteca` / `Giochi da tavolo`; `Stracòt`; `Escape room`; `Altro`                                                                                                   |
| `Dove`              | **Required.** Town, then short venue name.                     | `Trento, Locanda del Gatto Gordo`<br>`Rovereto, Smart Lab`<br>`Cognola, Istituto Comenius`                                                                           |
| `Come arrivare`     | Maps link; otherwise the script searches the Calendar address. | `https://maps.app.goo.gl/SkH39dic7ntw4NcG7`<br>`http://bit.ly/SmartLabMaps`                                                                                          |
| `Come partecipare`  | What someone must do to attend.                                | `Accesso libero, non serve prenotare.`<br>`Prenotazione obbligatoria; presenta la conferma all'arrivo.`<br>`È richiesta la tessera Glow; puoi associarti sul posto.` |
| `Prenotazioni`      | Booking link.                                                  | `https://example.org/iscrizioni`<br>`https://example.org/prenota-un-turno`                                                                                           |
| `Costo`             | Price, if known.                                               | `Gratuito`<br>`5€ per la tessera associativa di Glow`<br>`30€ a gruppo`                                                                                                      |
| `A chi è rivolto`   | Audience and age rules.                                        | `Tutti, anche senza esperienza.`<br>`Famiglie; bambini accompagnati da un adulto.`<br>`Ragazzi e adulti dai 16 anni.`                                                |
| `Durata`            | Length of one game/turn (not opening hours!)                   | `8 minuti per partita`<br>`45 minuti per turno`<br>`Circa 2 ore`                                                                                                     |
| `Dimensione gruppi` | People per team or turn.                                       | `4 persone per squadra`<br>`5–6 persone a turno`<br>`Da 3 a 5 persone`                                                                                               |
| `Note`              | Extra public information.                                      | `Presentati 10 minuti prima del turno prenotato.`<br>`Ultimo appuntamento prima della pausa estiva.`<br>`Sito ufficiale: https://example.org/evento`                 |
| `Locandina`         | Direct image link, downloaded automatically; otherwise the template supplies a generic image. | `https://ludimus.it/static/img/stracot.png`<br>`https://example.org/locandina.jpg`                                                                                   |

Some notes:

- Omit unused fields. Only the first two are really required. If unneeded, just leave them out.
- Replace sample URLs with real links!
- Unknown/wrong/repeated fields stop the script. Check the Calendar description for typos.
- Escape Room and Altro need an explicit initial. Without an invitation, the script manufactures one from the venue and activity.
- On Telegram messages, we print the invitation, event link and booking link. Other fields are omitted.
- `Locandina` must link directly to a valid JPEG, PNG, GIF or WebP image. A web page, non-image response or corrupt image blocks the import; it is not saved to the repo.

## Generazione eventi sito

### Checklist

1. Complete the [setup](#setup), then run the [preview command](#generate-next-week) for the affected week or [date range](#other-options).
2. Check `calendar-preview.md` and `event-pages/index.html`, including the [slug and short link](#event-urls). Set custom names before the first apply if needed.
3. Check the downloaded `Locandina` in the preview and its filename under **Event images** in `calendar-preview.md`. No manual image upload is needed.
4. Repeat the same command with `--apply` ([details](#generate-next-week)). NOTE: `python3 processors/generate.py` is automatically run, no need to run it twice.
5. Commit the changed files, including downloaded images, and push.
6. Copy the rendered Telegram draft and post it manually after the website is published ([details](#generate-next-week)).

### Setup

Default source URL:

```text
https://calendar.google.com/calendar/ical/fut0ai14gqld6cpuuu8h7iu9dg%40group.calendar.google.com/public/basic.ics
```

Use Python 3.10+ and `pip install -r requirements.txt`. The script downloads the public calendar; no login or keys are needed.
Other sources:

- `--ics PATH` reads a local export instead
- `--url URL` selects another feed

Google can take a few minutes to show edits in the feed. Retry later or use a fresh export.

### Generate next week

```bash
mkdir -p /tmp/ludimus-events
python processors/calendar_events.py
```

Alternatively, to avoid printing all the junk on the terminal, provide `--brief` and an output folder:

```bash
python processors/calendar_events.py --output-dir /tmp/ludimus-events --brief
```

This selects the following Monday–Sunday. Check the terminal, or `calendar-preview.md` and `event-pages/index.html` in the output folder.
Images from `Locandina` are fetched and validated during preview, then saved by `--apply` as `static/img/events/YYYY-MM-DD-SLUG.ext`. The extension follows the actual image format, and the generated event page uses the local image's public URL.

Apply by repeating the same command with `--apply`:

```bash
python processors/calendar_events.py --apply
```

Commit the changed files and push. Consider that the usual `python3 processors/generate.py` is automatically run, so you do not need to run it twice.
Double-check the Telegram message (if output folder: `telegram-YYYY-MM-DD.md`, and if necessary its HTML generated version), then send it too.

### Other options

```bash
python processors/calendar_events.py --week 2026-10-19 --output-dir /tmp/ludimus-events --brief
python processors/calendar_events.py --from 2026-10-19 --to 2026-12-31 --output-dir /tmp/ludimus-events --brief
python processors/calendar_events.py --ics ~/Downloads/calendar.ics --week 2026-10-19 --output-dir /tmp/ludimus-events --brief
```

`--week` accepts any date in that week. A range includes both dates and gives one message per week. 

### Correct or cancel an event

Edit Calendar, then run the affected week again. For a series-wide change, run the full affected date range.
Edit/delete just one occurrence for an exception. Keep generated event files untouched.
If the script stops, read the report, fix the issue and retry.

### Event URLs

A **slug** is the URL name, such as `serata-gattogordo`. Dated pages use `YYYY-MM-DD-SLUG.html`.
A short link such as `/events/gattogordo` points to the next upcoming event.

The script chooses a name automatically and remembers it in `processors/calendar-state.json`. Do not edit that file.
For a new recurring series, add it in Calendar, preview and apply. No JSON edit is needed unless you want a custom URL.
Editing the same series keeps its URL. Deleting and recreating it gives it a new Calendar ID (which you should then add to the existing JSON profile).

#### Custom names and matching

Edit `processors/event_profiles.json` before the first apply if you want a shorter URL:

```json
"serata-caffe-nuovo": {
  "uids": ["REAL_UID_FROM_THE_PREVIEW"],
  "alias": "caffe-nuovo"
}
```

The key names the dated files; `alias` gives `/events/caffe-nuovo`. Find the UID (Calendar's event ID) in the preview's **URL routing** table.

| JSON field  | Purpose                                                                                                                            |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `uids`      | Match a particular Calendar event/series.                                                                                          |
| `summaries` | Match an exact Calendar title when a new entry has no saved UID route yet. Useful for individually agreed dates.                   |
| `alias`     | Give the activity a shared short link. Without it, individual dates use dated links. Recurring series get an automatic short link. |
| `group`     | Optionally combine related sessions in a Telegram bullet.                                                                          |

Example: Doppio Malto dates have different UIDs but the same title. Its `summaries` match sends them to the shared `/events/doppiomalto` link.
One-off events need no profile; their dated URL names are assigned automatically.
UID matches take priority over title matches. For separately created dates, update `summaries` if you change their usual title.
To recreate a series without changing its URL, add its new UID to the existing profile. Keep the profile key and alias.

### Website filters

The event page filters by town, date range and activity. Filters work together; **Azzera filtri** restores the full list.
The script writes YAML metadata at the top of generated event Markdown: type, town, short venue, address, date, local start/end, all-day status and Calendar UID.
The website reads it automatically, no need to touch the YAML.
Older pages without these details remain visible and use **Non specificato** for missing location/type. With JavaScript disabled, the full list stays visible.

### Templates and event details

`processors/event_templates/` contains templates: `ludoteca.md`, `stracot.md`, `escape-room.md`, `altro.md`.
They supply page layout, shared wording and a default image. Calendar supplies event details, including membership rules, fees and booking.

Imports start on 19 October 2026. Earlier events are handled manually.
