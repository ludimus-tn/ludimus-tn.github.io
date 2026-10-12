# Calendar events

## Setup

Default source URL:

```text
https://calendar.google.com/calendar/ical/fut0ai14gqld6cpuuu8h7iu9dg%40group.calendar.google.com/public/basic.ics
```

Use Python 3.10+ and `pip install -r requirements.txt`. The script downloads the public calendar; no login or keys are needed.
Other sources:

- `--ics PATH` reads a local export instead
- `--url URL` selects another feed

Google can take a few minutes to show edits in the feed. Retry later or use a fresh export.

## Publish an event

1. Add the public title, hours and full Location in Calendar. Set Repeat for a series. Use `Europe/Rome`, even when editing abroad.
2. Fill the description using the example below.
3. Preview and apply its week, then publish the website.
4. Copy the rendered Telegram draft and post it manually after the website is published.

## Generate next week

```bash
mkdir -p /tmp/ludimus-events
python processors/calendar_events.py --output-dir /tmp/ludimus-events --brief
```

This selects the following Monday–Sunday. Check `calendar-preview.md` and `event-pages/index.html` in the output folder.
Apply by repeating the same command with `--apply`:

```bash
python processors/calendar_events.py --output-dir /tmp/ludimus-events --brief --apply
```

Commit the changed files, including `processors/calendar-state.json`, and push yourself.
Copy the message from `telegram-YYYY-MM-DD.html`. Its `.md` file is available for editing.

## Other options

```bash
python processors/calendar_events.py --week 2026-10-19 --output-dir /tmp/ludimus-events --brief
python processors/calendar_events.py --from 2026-10-19 --to 2026-12-31 --output-dir /tmp/ludimus-events --brief
python processors/calendar_events.py --ics ~/Downloads/calendar.ics --week 2026-10-19 --output-dir /tmp/ludimus-events --brief
```

`--week` accepts any date in that week. A range includes both dates and gives one message per week. Keep the same options when applying.

## Correct or cancel an event

Edit Calendar, then run the affected week again. For a series-wide change, run the full affected date range.
Edit/delete just one occurrence for an exception. Keep generated event files untouched.
If the script stops, read the report, fix the issue and retry.
The daily website build uses committed files; it does not fetch Calendar. You need to run the script again BEFORE rebuilding the website.

## Website filters

The event page filters by short venue (shown with its town), date range and activity. Filters work together; **Azzera filtri** restores the full list.
The script writes YAML metadata at the top of generated event Markdown: type, town, short venue, address, date, local start/end, all-day status and Calendar UID.
The website reads it automatically, no need to touch the YAML.
Older pages without these details remain visible and use **Non specificato** for missing location/type. With JavaScript disabled, the full list stays visible.

Keep dates/hours in their Calendar fields. Split lunch breaks and different daily hours into separate sessions, each at most 24 hours.

## Description

The optional first sentence starts with `Vi aspettiamo`. The script adds the hours, so leave them out.
Other prose stays on the website. Finish with `Informazioni:` and one field per line.
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
| `Locandina`         | Image link; otherwise the template supplies a generic image.   | `https://ludimus.it/static/img/stracot.png`<br>`https://example.org/locandina.jpg`                                                                                   |

Omit unused fields. Replace sample URLs with real links. Unknown or repeated fields stop the script.
Escape Room and Altro need a description. Without an invitation, the script writes one from the venue and activity.
Telegram gets only the invitation, event link and booking link. `In breve` is retired; old values appear only on the website.

## Event URLs

A **slug** is the URL name, such as `serata-gattogordo`. Dated pages use `YYYY-MM-DD-SLUG.html`.
A short link such as `/events/gattogordo` points to the next upcoming event.

The script chooses a name automatically and remembers it in `processors/calendar-state.json`. Do not edit that file.
For a new recurring series, add it in Calendar, preview and apply. No JSON edit is needed unless you want a custom URL.
Editing the same series keeps its URL. Deleting and recreating it gives it a new Calendar ID (which you should then add to the existing JSON profile).

### Custom names and matching

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

## Templates and event details

`processors/event_templates/` contains templates: `ludoteca.md`, `stracot.md`, `escape-room.md`, `altro.md`.
They supply page layout, shared wording and a default image. Calendar supplies event details, including membership rules, fees and booking.

Imports start on 19 October 2026. Earlier events are handled manually.
