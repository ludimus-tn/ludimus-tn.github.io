"""Preview and apply public Calendar events. All local dates use Europe/Rome."""

import argparse
import datetime as dt
import difflib
import hashlib
import html
import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlparse
from zoneinfo import ZoneInfo

import icalendar
import markdown2
import recurring_ical_events
import requests
import yaml

ROME = ZoneInfo("Europe/Rome")
ROOT = Path(__file__).resolve().parents[1]
STATE = "processors/calendar-state.json"
CONFIG = "processors/event_profiles.json"
HTTP_URL = re.compile(r"\bhttps?://(?:[^\s<>\"'()[\]{}]|\([^\s<>\"'()]*\))+(?<![.,;:!?])")
WEEKDAYS = ("Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica")
MONTHS = ("Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio",
          "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre")
DEFAULT_FEED = "https://calendar.google.com/calendar/ical/fut0ai14gqld6cpuuu8h7iu9dg%40group.calendar.google.com/public/basic.ics"
HEADER = "Informazioni:"
FIELDS = {
    "Attività": "kind", "Dove": "where", "Come arrivare": "map",
    "Come partecipare": "participation",
    "Prenotazioni": "booking_url", "Costo": "cost", "A chi è rivolto": "audience",
    "Durata": "duration", "Dimensione gruppi": "players",
    "Note": "notice", "Locandina": "image",
}
# Read older entries during migration; this text is website-only.
LEGACY_FIELDS = {"In breve": "legacy_description"}
KINDS = {"giochi da tavolo": "boardgames", "ludoteca": "boardgames", "escape room": "escape-room",
         "stracòt": "stracot", "stracot": "stracot", "altro": "custom"}
ACTIVITY_TEMPLATES = {"boardgames": "ludoteca.md", "stracot": "stracot.md",
                      "escape-room": "escape-room.md", "custom": "altro.md"}
ROUTING_FIELDS = {"uids", "summaries", "alias", "group"}
EVENT_TYPE_CODES = {"boardgames": "ludoteca", "stracot": "stracot", "escape-room": "escape-room", "custom": "altro"}
EVENT_TYPE_LABELS = {"ludoteca": "Ludoteca", "stracot": "Stracòt", "escape-room": "Escape Room", "altro": "Altro"}
DETAILS = (("participation", "Come partecipare: "),
           ("cost", "Costo: "), ("audience", "A chi è rivolto: "),
           ("duration", "Durata: "), ("players", "Dimensione gruppi: "))


class CalendarError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def render_event_markdown(text, safe_mode=None):
    protected = []

    def protect_link(match):
        def hide_url(url):
            token = f"\ue000{len(protected)}\ue001"
            protected.append(url.group(0))
            return token
        return HTTP_URL.sub(hide_url, match.group(0))

    # Existing HTML/Markdown links may have URL labels; do not linkify them again.
    text = re.sub(r"<a\b[^>]*>.*?</a\s*>", protect_link, text, flags=re.I | re.S)
    text = re.sub(r"!?\[(?:[^\[\]\n]|\[[^\]\n]*\])*\]\((?:[^()\n]|\([^()\n]*\))*\)", protect_link, text)
    rendered = markdown2.markdown(
        text, safe_mode=safe_mode,
        extras={"break-on-newline": True, "link-patterns": True},
        link_patterns=[(HTTP_URL, lambda match: match.group(0))],
    )
    for index, url in enumerate(protected):
        rendered = rendered.replace(f"\ue000{index}\ue001", html.escape(html.unescape(url), quote=True))
    return rendered


def alias_targets(paths, today, aliases, end_dates=None):
    targets = {}
    for path in sorted(paths):
        name = Path(path).name
        try:
            date = dt.date.fromisoformat(name[:10])
        except ValueError:
            continue
        slug = Path(name[11:]).stem
        last_day = dt.date.fromisoformat((end_dates or {}).get(name, date.isoformat()))
        if last_day < today:
            continue
        for alias, event_slug in aliases.items():
            if slug == event_slug and alias not in targets:
                targets[alias] = "/events/" + Path(name).with_suffix(".html").name
    return {alias: targets.get(alias, "/events") for alias in aliases}


class EventMetadataLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise CalendarError("Event metadata keys must be text")
            if key in seen:
                raise CalendarError(f"Repeated event metadata field: {key}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def read_event_source(text):
    """Read YAML front matter or the older leading event_* lines."""
    lines = text.lstrip("\ufeff").splitlines(keepends=True)
    first = next((index for index, line in enumerate(lines) if line.strip()), len(lines))
    lines = lines[first:]
    if lines and lines[0].strip() == "---":
        closing = next((index for index in range(1, len(lines)) if lines[index].rstrip("\r\n") == "---"), None)
        if closing is None:
            raise CalendarError("Unclosed event YAML metadata")
        try:
            metadata = yaml.load("".join(lines[1:closing]), Loader=EventMetadataLoader)
        except yaml.YAMLError as error:
            raise CalendarError(f"Invalid event YAML metadata: {error}") from None
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise CalendarError("Event YAML metadata must be a mapping")
        for key in ("event_title", "event_description", "event_og", "event_type", "event_town", "event_location", "event_address", "event_uid"):
            if key in metadata and not isinstance(metadata[key], str):
                raise CalendarError(f"Event metadata field must be text: {key}")
        if "event_all_day" in metadata and not isinstance(metadata["event_all_day"], bool):
            raise CalendarError("event_all_day must be a YAML boolean")
        return metadata, "".join(lines[closing + 1:]).lstrip("\r\n")
    metadata, index = {}, 0
    for line in lines:
        match = re.fullmatch(r"(event_[a-z_]+):\s*(.*?)\s*", line)
        if not match:
            break
        key, value = match.groups()
        if key in metadata:
            raise CalendarError(f"Repeated event metadata field: {key}")
        metadata[key] = html.unescape(value)
        index += 1
    return metadata, "".join(lines[index:]).lstrip("\r\n")


def source_event_info(metadata, filename):
    """Filter facts use local dates; a midnight end excludes the next day."""
    try:
        file_date = dt.date.fromisoformat(Path(filename).name[:10])
        day = dt.date.fromisoformat(str(metadata.get("event_date", file_date.isoformat())))
        if day != file_date:
            raise CalendarError(f"Event date disagrees with its filename: {filename}")
        last_day = day
        start_value, end_value = metadata.get("event_start"), metadata.get("event_end")
        if start_value:
            beginning = local(dt.datetime.fromisoformat(str(start_value).replace("Z", "+00:00")))
            if beginning.date() != day:
                raise CalendarError(f"Event start disagrees with its date: {filename}")
        if end_value:
            ending = local(dt.datetime.fromisoformat(str(end_value).replace("Z", "+00:00")))
            if start_value and ending <= beginning:
                raise CalendarError(f"Event end must be after start: {filename}")
            last_day = ending.date()
            if ending.time().replace(tzinfo=None) == dt.time():
                last_day -= dt.timedelta(days=1)
            if last_day < day:
                raise CalendarError(f"Event end precedes its date: {filename}")
    except ValueError as error:
        raise CalendarError(f"Invalid event date in {filename}: {error}") from None
    kind = metadata.get("event_type", "")
    if not isinstance(kind, str):
        raise CalendarError(f"Event type must be text: {filename}")
    kind = EVENT_TYPE_CODES.get(kind, kind)
    if kind and kind not in EVENT_TYPE_LABELS:
        raise CalendarError(f"Unknown event type in {filename}: {kind}")
    town, venue = metadata.get("event_town", ""), metadata.get("event_location", "")
    if not isinstance(town, str) or not isinstance(venue, str):
        raise CalendarError(f"Event town/location must be text: {filename}")
    location = " — ".join(value for value in (town.strip(), venue.strip()) if value)
    return {"date": day.isoformat(), "end_date": last_day.isoformat(),
            "type": kind, "type_label": EVENT_TYPE_LABELS.get(kind, "Non specificato"),
            "location": location, "location_label": location or "Non specificato"}


def event_filter_attributes(info):
    values = {"data-event": "", "data-date": info["date"], "data-end-date": info["end_date"],
              "data-type": info["type"], "data-type-label": info["type_label"],
              "data-location": info["location"], "data-location-label": info["location_label"]}
    return "".join(f' {key}="{html.escape(value, quote=True)}"' for key, value in values.items())


def render_event_link(template, title, date, event_url, attributes=""):
    values = {"title": html.escape(str(title), quote=True), "date": html.escape(date, quote=True),
              "event_url": html.escape(event_url, quote=True), "event_attributes": attributes}
    text = "".join(template) if isinstance(template, list) else template
    return re.sub(r"\{\{ (\w+) \}\}", lambda match: values[match.group(1)], text)


def render_event_page(metadata, body, root=ROOT):
    template = (root / "layouts/partials/event.html").read_text(encoding="utf-8")
    values = {"event_title": metadata.get("event_title", ""),
              "event_description": metadata.get("event_description", ""),
              "event_og": metadata.get("event_og", "https://ludimus.it/static/img/events/default.jpg")}
    values = {key: html.escape(str(value), quote=True) for key, value in values.items()}
    values.update(event_body=render_event_markdown(body),
                  footer=(root / "layouts/partials/footer.html").read_text(encoding="utf-8"),
                  hash=hashlib.md5((root / "style.css").read_bytes()).hexdigest())
    return re.sub(r"\{\{ (\w+) \}\}", lambda match: values[match.group(1)], template)


def local(value):
    if isinstance(value, dt.datetime):
        return value.replace(tzinfo=ROME) if value.tzinfo is None else value.astimezone(ROME)
    return dt.datetime.combine(value, dt.time(), ROME)


def date_label(value):
    return f"{WEEKDAYS[value.weekday()]} {value.day:02d} {MONTHS[value.month - 1]} {value.year}"


class PublicHTML(HTMLParser):
    """Convert Calendar editor HTML to safe Markdown, retaining public links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if self.hidden:
            return
        if tag in ("br", "p", "div", "li"):
            self.parts.append("\n")
        if tag in ("b", "strong"):
            self.parts.append("**")
        if tag == "a":
            href = dict(attrs).get("href", "")
            self.links.append(href if urlparse(href).scheme in ("http", "https", "mailto") else "")
            self.parts.append("[")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag in ("p", "div", "li"):
            self.parts.append("\n")
        if tag in ("b", "strong"):
            self.parts.append("**")
        if tag == "a" and self.links:
            href = self.links.pop()
            self.parts.append(f"]({href})" if href else "]")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def public_description(value):
    parser = PublicHTML()
    parser.feed(value)
    text = "".join(parser.parts).strip()
    marker = re.search(r"^\s*(?:\*\*)?" + re.escape(HEADER) + r"(?:\*\*)?\s*$", text, re.M)
    body = text[:marker.start()] if marker else text
    footer = text[marker.end():] if marker else ""
    metadata = {}
    seen = set()
    if marker:
        for line in footer.splitlines():
            if not line.strip():
                continue
            key, separator, value = line.partition(":")
            key = key.strip().strip("*")
            if not separator or (key not in FIELDS and key not in LEGACY_FIELDS):
                raise CalendarError(f"Unknown information field: {line.strip()}")
            field = FIELDS.get(key) or LEGACY_FIELDS[key]
            if field in seen:
                raise CalendarError(f"Repeated information field: {key}")
            seen.add(field)
            value = value.strip().strip("*").strip()
            if field in ("map", "image", "booking_url"):
                link = re.fullmatch(r"\[.*\]\((https?://[^\s]+)\)", value)
                if link:
                    value = link.group(1)
            if value:
                if field == "where":
                    city, separator, venue = value.partition(",")
                    if not separator or not city.strip() or not venue.strip():
                        raise CalendarError("Dove must contain Comune, nome del luogo")
                    metadata.update(city=city.strip(), venue=venue.strip())
                else:
                    metadata[field] = value
    return body.strip(), metadata


def invitation_tail(body):
    """Only split the opening words; venue/activity prose is never interpreted."""
    lines = body.strip().splitlines()
    pattern = re.compile(r"^Vi aspettiamo(?:\s+(.*))?$", re.I)
    invitations = [(index, pattern.fullmatch(line.replace("**", "").strip()))
                   for index, line in enumerate(lines)]
    invitations = [(index, match) for index, match in invitations if match]
    if not invitations:
        return None
    if len(invitations) > 1:
        raise CalendarError("Use only one Vi aspettiamo invitation")
    index, match = invitations[0]
    if index != 0:
        raise CalendarError("Put the Vi aspettiamo invitation on the first description line")
    tail = (match.group(1) or "").strip()
    if not tail:
        raise CalendarError("Complete the Vi aspettiamo invitation with the venue or activity")
    if re.search(r"\b\d{1,2}:\d{2}\b", tail):
        raise CalendarError("Keep hours in Calendar start/end, not in the Vi aspettiamo invitation")
    return tail


@dataclass
class Occurrence:
    key: str
    uid: str
    start: dt.datetime
    end: dt.datetime
    original: dt.datetime
    summary: str
    location: str
    description: str
    recurring: bool
    all_day: bool


def occurrences(calendar, start, end):
    """The recurrence library applies RRULE, RDATE, EXDATE and RECURRENCE-ID."""
    masters = {str(e.get("uid")): e for e in calendar.walk("VEVENT")
               if "RECURRENCE-ID" not in e}
    result = []
    seen = set()
    for event in recurring_ical_events.of(calendar).between(start, end):
        if str(event.get("status", "")).upper() == "CANCELLED":
            continue
        beginning = local(event.decoded("dtstart"))
        # Query returns overlapping events; publish by their local start date.
        if not start <= beginning < end:
            continue
        uid = str(event.get("uid", ""))
        if not uid:
            raise CalendarError("Calendar event has no UID")
        master = masters.get(uid, event)
        repeated = "RRULE" in master or "RDATE" in master
        original = local(event.decoded("recurrence-id")) if "RECURRENCE-ID" in event else beginning
        # The expansion library synthesizes RECURRENCE-ID even for standalone events.
        # A standalone event's identity must survive a date change.
        key = uid + ("/" + original.isoformat() if repeated else "")
        if key in seen:
            raise CalendarError(f"Duplicate Calendar identity: {key}")
        seen.add(key)
        ending = local(event.decoded("dtend")) if "DTEND" in event else beginning + event.decoded("duration", dt.timedelta(days=1))
        result.append(Occurrence(key, uid, beginning, ending, original,
                                 str(event.get("summary", "")), str(event.get("location", "")),
                                 str(event.get("description", "")), repeated,
                                 not isinstance(event.decoded("dtstart"), dt.datetime)))
    return sorted(result, key=lambda e: (e.start, e.summary, e.key))


def fetch_calendar(url=DEFAULT_FEED):
    validate_url(url)
    try:
        response = requests.get(url, timeout=60, headers={"Cache-Control": "no-cache"})
    except requests.RequestException:
        raise CalendarError("Calendar download failed; retry or use --ics with a local export") from None
    if not response.ok:
        raise CalendarError(f"Calendar feed returned HTTP {response.status_code}")
    data = response.content
    if not data.lstrip().startswith(b"BEGIN:VCALENDAR") or b"END:VCALENDAR" not in data:
        raise CalendarError("Calendar response is not a complete ICS feed")
    return icalendar.Calendar.from_ical(data)


def validate_url(value):
    if urlparse(value).scheme not in ("http", "https"):
        raise CalendarError(f"Expected an http(s) URL: {value}")
    if any(c in value for c in '\n\r<>"'):
        raise CalendarError("URL contains invalid characters")
    return value


def read_activity_template(kind, root=ROOT):
    path = "processors/event_templates/" + ACTIVITY_TEMPLATES[kind]
    lines = (root / path).read_text(encoding="utf-8").splitlines()
    images = [line.removeprefix("event_og: ").strip() for line in lines if line.startswith("event_og: ")]
    if len(images) != 1:
        raise CalendarError(f"Activity template needs one event_og: {path}")
    return path, images[0], "\n".join(line for line in lines if not line.startswith("event_og: ")).strip()


def settings(event, profiles, previous_slug=None, root=ROOT):
    body, fields = public_description(event.description)
    tail = invitation_tail(body)
    matches = [key for key, p in profiles.items() if event.uid in p.get("uids", [])]
    if len(matches) > 1:
        raise CalendarError("Calendar UID matches multiple routing profiles")
    slug = matches[0] if len(matches) == 1 else previous_slug
    if not slug:
        matches = [key for key, p in profiles.items() if event.summary.strip() in p.get("summaries", [])]
        if len(matches) > 1:
            raise CalendarError("Calendar title matches multiple routing profiles")
        if len(matches) == 1:
            slug = matches[0]
    if not slug:
        label = unicodedata.normalize("NFKD", event.summary).encode("ascii", "ignore").decode()
        slug = "evento-" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise CalendarError("Invalid local activity slug")
    profile = dict(profiles.get(slug, {}))
    unsupported = set(profile) - ROUTING_FIELDS
    if unsupported:
        raise CalendarError(f"Routing profile contains event content; move these fields to Calendar: {', '.join(sorted(unsupported))}")
    profile.update(fields)
    if tail:
        profile["invitation_tail"] = tail
    profile["slug"] = slug
    if not event.location:
        raise CalendarError("Missing Calendar Location")
    if not profile.get("city") or not profile.get("venue"):
        raise CalendarError("Missing Dove under Informazioni: (Comune, nome del luogo)")
    if not event.summary:
        raise CalendarError("Missing Calendar title")
    if event.end <= event.start:
        raise CalendarError("End must be after start")
    if not event.all_day and event.end - event.start > dt.timedelta(days=1):
        raise CalendarError("Split multi-day timed events into public sessions")
    if not fields.get("kind"):
        raise CalendarError("Missing Attività under Informazioni:")
    if fields["kind"].casefold() not in KINDS:
        raise CalendarError("Attività must be Ludoteca/Giochi da tavolo, Escape room, Stracòt or Altro")
    profile["kind"] = KINDS[fields["kind"].casefold()]
    if profile["kind"] in ("custom", "escape-room") and not body and not profile.get("legacy_description"):
        raise CalendarError("Custom events need a public description")
    profile["title"] = event.summary
    template_path, image, _ = read_activity_template(profile["kind"], root)
    profile["template"] = template_path
    profile.setdefault("image", image)
    profile.setdefault("map", "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": event.location}))
    for key in ("map", "image", "booking_url"):
        if profile.get(key):
            validate_url(profile[key])
    for key, value in profile.items():
        if isinstance(value, str) and ("\n" in value or "\r" in value):
            raise CalendarError(f"Multiline field: {key}")
    return profile, body


def time_label(event):
    if event.all_day:
        last = event.end.date() - dt.timedelta(days=1)
        return "tutto il giorno" if last == event.start.date() else "fino a " + date_label(last)
    beginning = event.start.strftime("%H:%M")
    return f"dalle {beginning} alle {event.end:%H:%M}"


def invitation_text(event, profile, times=None, *, sentence_start=True):
    tail = profile.get("invitation_tail")
    if not tail:
        activity = {"stracot": " con Stracòt", "escape-room": " per un’escape room"}.get(profile.get("kind"), "")
        tail = f"presso {profile['venue']}{activity}!"
    opening = "Vi" if sentence_start else "vi"
    return f"{opening} aspettiamo {times or time_label(event)} {tail}"


def detail_lines(profile):
    return [f"**{label.strip()}** {profile[key]}" if label else profile[key]
            for key, label in DETAILS if profile.get(key)]


def render_source(event, profile, body, root):
    date = date_label(event.start)
    time = time_label(event)
    title = profile["title"]
    invitation = invitation_text(event, profile, sentence_start=False)
    _, _, template = read_activity_template(profile["kind"], root)
    escape_text = lambda text: text.replace("<", "&lt;").replace(">", "&gt;")
    introduction = []
    if body:
        introduction.append(body.strip())
    if profile.get("legacy_description"):
        introduction.append(profile["legacy_description"])
    information = detail_lines(profile)
    if profile.get("notice"):
        information.append("❗ **Note:** " + profile["notice"])
    if profile.get("booking_url"):
        information.append(f"🎟️ [**Prenotazioni**]({profile['booking_url']})")
    values = {"title": title, "date": date, "time": time,
              "location": f"[{profile['venue']}]({profile['map']})",
              "description": "\n".join(introduction), "details": "\n".join(information)}
    if not introduction:
        template = template.replace("\n{{ description }}", "")
    # Separate descriptive prose from fields without spacing every field as a paragraph.
    if information and (introduction or profile["kind"] in ("stracot", "escape-room")):
        template = template.replace("\n\n{{ details }}", "<br />\n{{ details }}")
    elif not information:
        template = template.replace("\n\n{{ details }}", "")
    content = re.sub(r"\{\{ (\w+) \}\}", lambda match: escape_text(values[match.group(1)]), template).strip()
    metadata = {"event_title": title, "event_description": date + " " + invitation,
                "event_og": profile["image"], "event_type": EVENT_TYPE_CODES[profile["kind"]],
                "event_town": profile["city"], "event_location": profile["venue"],
                "event_address": event.location, "event_date": event.start.date().isoformat(),
                "event_start": event.start.isoformat(), "event_end": event.end.isoformat(),
                "event_all_day": event.all_day, "event_uid": event.uid}
    front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False, width=1000)
    return "---\n" + front_matter + "---\n\n" + content.strip() + "\n"


def event_link(event, profile):
    target = profile.get("alias") or f"{event.start.date().isoformat()}-{profile['slug']}.html"
    return "https://ludimus.it/events/" + target


def telegram_message(events):
    chunks = ["**[Eventi della Settimana]**\n\nEcco gli [appuntamenti della settimana](https://ludimus.it/events):"]
    groups = {}
    for event, profile in events:
        key = profile.get("group") or event.key
        groups.setdefault(key, []).append((event, profile))
    for group in groups.values():
        event, profile = group[0]
        days = " / ".join(dict.fromkeys(WEEKDAYS[e.start.weekday()].upper() for e, _ in group))
        times = time_label(event) if len(group) == 1 else ", ".join(f"il {e.start:%d/%m} {time_label(e)}" for e, _ in group)
        text = invitation_text(event, profile, times, sentence_start=False)
        lines = [f"• **{days}** [{profile['city']}] - {text}"]
        lines.extend("👉 " + link for link in dict.fromkeys(event_link(e, p) for e, p in group))
        if profile.get("booking_url"):
            lines.append(f"🎟️ **Prenotazioni:** {profile['booking_url']}")
        chunks.append("\n".join(lines))
    if not events:
        chunks.append("Al momento non ci sono eventi in programma 🎲")
    # Leave headroom for Telegram's 4096-character limit, including manual additions.
    messages, current = [], ""
    for chunk in chunks:
        if len(chunk) > 3500:
            raise CalendarError("Telegram entry exceeds 3500 characters; shorten Telegram text or split its group")
        if len(current) + len(chunk) + 2 > 3500:
            messages.append(current)
            current = ""
        current += ("\n\n" if current else "") + chunk
    messages.append(current)
    return "\n\n<!-- NEXT TELEGRAM MESSAGE -->\n\n".join(messages) + "\n"


def load_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def source_text(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def known_occurrence(calendar, record):
    """Resolve moved exceptions outside the requested range before assuming deletion."""
    original = dt.datetime.fromisoformat(record["original"])
    windows = [original]
    for component in calendar.walk("VEVENT"):
        if str(component.get("uid")) == record["uid"] and "RECURRENCE-ID" in component:
            if local(component.decoded("recurrence-id")) == original:
                windows.append(local(component.decoded("dtstart")))
        elif str(component.get("uid")) == record["uid"] and "RRULE" not in component and "RDATE" not in component:
            if "DTSTART" in component:
                windows.append(local(component.decoded("dtstart")))
    for beginning in windows:
        for event in occurrences(calendar, beginning - dt.timedelta(seconds=1), beginning + dt.timedelta(days=1)):
            if event.key == record["key"]:
                return event
    return None


def plan(calendar, start, end, root=ROOT, adopt=False):
    config = load_json(root / CONFIG)
    cutoff = dt.date.fromisoformat(config["migration_start"])
    if start.date() < cutoff:
        raise CalendarError(f"Import starts on {cutoff}; earlier event sources are outside this migration")
    state = load_json(root / STATE, {"version": 1, "events": {}})
    if state.get("version") != 1:
        raise CalendarError("Unsupported calendar state version")
    old = state["events"]
    new = dict(old)
    routes = dict(state.get("routes", {}))
    for record in old.values():
        uid = record["uid"]
        if uid not in routes:
            slugs = {item["slug"] for item in old.values() if item["uid"] == uid}
            if len(slugs) != 1:
                raise CalendarError("A Calendar UID owns multiple slugs; reconcile its routing before importing")
            route = {"slug": record["slug"]}
            alias = config["profiles"].get(record["slug"], {}).get("alias")
            if alias:
                route["alias"] = alias
            routes[uid] = route
    aliases = {route["alias"]: route["slug"] for route in routes.values() if route.get("alias")}
    aliases.update({p["alias"]: slug for slug, p in config["profiles"].items() if p.get("alias")})
    selected = {event.key: event for event in occurrences(calendar, start, end)}
    candidates = dict(selected)
    remove = {}
    errors, entries = [], []
    for key, record in old.items():
        if not record["path"].startswith("layouts/events/") or Path(record["path"]).name != f"{record['date']}-{record['slug']}.md":
            raise CalendarError("Invalid path in calendar state")
        day = dt.date.fromisoformat(record["date"])
        if start.date() <= day < end.date():
            event = candidates.get(key) or known_occurrence(calendar, dict(record, key=key))
            if event:
                candidates[key] = event
            else:
                remove[record["path"]] = "deleted/cancelled in Calendar"
                new.pop(key, None)

    writes, claimed, templates = {}, {}, {}
    for key, event in sorted(candidates.items(), key=lambda pair: (pair[1].start, pair[1].summary)):
        label = f"{event.start:%Y-%m-%d %H:%M} | {event.summary}"
        try:
            if event.start.date() < cutoff:
                raise CalendarError(f"Moved before migration cutoff {cutoff}; resolve manually")
            previous = old.get(key)
            previous_slug = previous["slug"] if previous else routes.get(event.uid, {}).get("slug")
            profile, body = settings(event, config["profiles"], previous_slug, root=root)
            if event.recurring and event.uid not in routes and profile["slug"] not in config["profiles"]:
                if any(route["slug"] == profile["slug"] for route in routes.values()):
                    profile["slug"] += "-" + digest(event.uid)[:8]
            alias = profile.get("alias") or routes.get(event.uid, {}).get("alias")
            if not alias and event.recurring:
                alias = profile["slug"]
            if alias:
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", alias):
                    raise CalendarError("Invalid local URL alias")
                if alias in aliases and aliases[alias] != profile["slug"]:
                    raise CalendarError(f"URL alias already belongs to another activity: {alias}")
                aliases[alias] = profile["slug"]
                profile["alias"] = alias
            filename = f"{event.start.date().isoformat()}-{profile['slug']}.md"
            path = "layouts/events/" + filename
            if path in claimed:
                raise CalendarError(f"Two events map to {path}; distinguish their titles or local activity mappings")
            claimed[path] = key
            target = root / path
            managed_target = False
            if target.exists() and (not previous or previous["path"] != path):
                owners = [owner for owner, record in old.items() if record["path"] == path]
                if owners and key not in owners:
                    replacement = all(old[owner]["path"] in remove and (
                        old[owner]["uid"] == event.uid or (
                            profile["slug"] in config["profiles"] and old[owner]["slug"] == profile["slug"]
                        )) for owner in owners)
                    if not replacement:
                        raise CalendarError(f"Target already owned by another Calendar event: {path}")
                managed_target = bool(owners)
                if not managed_target and not adopt:
                    raise CalendarError(f"Existing unmanaged source: {path}; review with --adopt")
            if previous:
                old_text = source_text(root / previous["path"])
                if digest(old_text) != previous["hash"]:
                    raise CalendarError(f"Managed source changed manually: {previous['path']}; put edits in Calendar or restore the source")
                if previous["path"] != path:
                    remove[previous["path"]] = f"moved to {path}"
            if profile.get("template"):
                templates[profile["template"]] = digest(source_text(root / profile["template"]))
            text = render_source(event, profile, body, root)
            before = source_text(target)
            action = "create" if not target.exists() else "update" if before != text else "unchanged"
            if target.exists() and not previous and not managed_target:
                action += "/adopt"
            writes[path] = {"before": before, "after": text, "action": action}
            routes[event.uid] = {"slug": profile["slug"], **({"alias": alias} if alias else {})}
            new[key] = {"uid": event.uid, "original": event.original.isoformat(),
                        "date": event.start.date().isoformat(), "slug": profile["slug"],
                        "path": path, "hash": digest(text)}
            entries.append({"event": event, "profile": profile, "action": action, "path": path,
                            "link": event_link(event, profile), "selected": key in selected})
        except (CalendarError, OSError) as error:
            errors.append(label + " | " + str(error))

    for path in sorted((root / "layouts/events").glob("*.md")):
        try:
            day = dt.date.fromisoformat(path.name[:10])
        except ValueError:
            continue
        relative = path.relative_to(root).as_posix()
        if start.date() <= day < end.date() and relative not in writes and relative not in remove:
            if not any(record["path"] == relative for record in old.values()):
                errors.append(f"Website-only/unreconciled source: {relative}; resolve before applying")
    for path, reason in remove.items():
        if path not in writes:
            writes[path] = {"before": source_text(root / path), "after": None, "action": "remove: " + reason}
    for record in old.values():
        if record["path"] in remove and digest(source_text(root / record["path"])) != record["hash"]:
            errors.append(f"Managed source changed manually: {record['path']}")

    weeks = {}
    monday = start.date() - dt.timedelta(days=start.weekday())
    while monday < end.date():
        weeks[monday.isoformat()] = []
        monday += dt.timedelta(days=7)
    for entry in entries:
        if entry["selected"]:
            day = entry["event"].start.date()
            monday = day - dt.timedelta(days=day.weekday())
            weeks.setdefault(monday.isoformat(), []).append((entry["event"], entry["profile"]))
    messages = {week: telegram_message(events) for week, events in weeks.items()}
    final_state = {"version": 1, "events": dict(sorted(new.items())), "routes": dict(sorted(routes.items()))}
    payload = {"start": start.isoformat(), "end": end.isoformat(), "writes": writes,
               "state_before": source_text(root / STATE), "state_after": final_state,
               "config": source_text(root / CONFIG), "templates": templates,
               "messages": messages, "errors": errors}
    source_names = {path.name for path in (root / "layouts/events").glob("*.md")}
    for path, change in writes.items():
        if change["after"] is None:
            source_names.discard(Path(path).name)
        else:
            source_names.add(Path(path).name)
    end_dates = {}
    for name in source_names:
        path = "layouts/events/" + name
        text = writes[path]["after"] if path in writes else source_text(root / path)
        metadata, _ = read_event_source(text)
        end_dates[name] = source_event_info(metadata, name)["end_date"]
    redirects = alias_targets(source_names, dt.datetime.now(ROME).date(), aliases, end_dates)
    payload["redirects"] = redirects
    payload["build_date"] = dt.datetime.now(ROME).date().isoformat()
    payload["build_inputs"] = {path: digest(source_text(root / path)) for path in (
        "processors/generate.py", "processors/calendar_events.py", "layouts/partials/event.html",
        "layouts/partials/event-link.html", "layouts/partials/footer.html", "layouts/events.html",
        "static/js/event-filters.js", "style.css")}
    fingerprint = digest(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    inputs = {CONFIG: digest(payload["config"]), STATE: digest(payload["state_before"]),
              **templates, **payload["build_inputs"]}
    return {"_fingerprint": fingerprint, "_inputs": inputs, "writes": writes, "state": final_state, "entries": entries,
            "errors": errors, "messages": messages, "start": start, "end": end,
            "total": len(selected), "redirects": redirects}


def report(proposal):
    lines = ["# Calendar preview", "",
             f"Range: {proposal['start'].date()} through {(proposal['end'] - dt.timedelta(days=1)).date()} (Europe/Rome)", "",
             "Status: BLOCKED" if proposal["errors"] else "Status: READY — preview only", "",
             f"Calendar occurrences: {proposal['total']}; mapped: {len(proposal['entries'])}; blockers: {len(proposal['errors'])}.", "",
             "## Events", "", "| Date/time | Calendar title | Action | Source | Telegram link |",
             "|---|---|---|---|---|"]
    for item in proposal["entries"]:
        event = item["event"]
        title = event.summary.replace("|", "\\|")
        end = event.end.strftime("%H:%M") + (" (+1 day)" if event.end.date() != event.start.date() else "")
        lines.append(f"| {event.start:%Y-%m-%d %H:%M}–{end} | {title} | {item['action']} | `{item['path']}` | {item['link']} |")
    if proposal["errors"]:
        lines += ["", "## Blockers", ""] + ["- " + error for error in proposal["errors"]]
    lines += ["", "## Venue redirects after rebuilding today", ""]
    lines += [f"- `/events/{alias}` → `{target}`" for alias, target in sorted(proposal["redirects"].items())]
    lines += ["", "Daily rebuilds advance these links to the next upcoming occurrence.", "",
              "## URL routing", "", "| Calendar UID | Stable slug | Alias |", "|---|---|---|"]
    for uid, route in proposal["state"].get("routes", {}).items():
        lines.append(f"| `{uid}` | `{route['slug']}` | `{route.get('alias', 'dated links')}` |")
    lines += ["",
              "## Calendar ownership to record", "", "Applying writes `processors/calendar-state.json` with these identities.", ""]
    for entry in proposal["entries"]:
        lines.append(f"- `{entry['event'].key}` → `{entry['path']}`")
    lines += ["", "## Source diffs", ""]
    for path, change in sorted(proposal["writes"].items()):
        lines += [f"### {change['action']}: {path}", ""]
        diff = "".join(difflib.unified_diff((change["before"].rstrip() + "\n").splitlines(keepends=True) if change["before"] else [],
                                          ((change["after"] or "").rstrip() + "\n").splitlines(keepends=True) if change["after"] else [],
                                          fromfile=path, tofile=path))
        lines += ["```diff", diff.rstrip(), "```", ""] if diff else ["Content unchanged; ownership recorded on apply.", ""]
    lines += ["## Telegram drafts", ""]
    if proposal["errors"]:
        lines += ["Drafts are partial until all blockers are resolved.", ""]
    for week, message in proposal["messages"].items():
        lines += ["### Week of " + week, "", "```markdown", message.rstrip(), "```", ""]
    return "\n".join(lines) + "\n"


def output_artifacts(proposal, directory):
    if not directory.is_dir():
        raise CalendarError("Output directory must already exist")
    resolved = directory.resolve()
    if resolved == ROOT or any(resolved == ROOT / p or ROOT / p in resolved.parents for p in ("layouts", "events", "processors")):
        raise CalendarError("Use an external directory for preview artifacts")
    (directory / "calendar-preview.md").write_text(report(proposal), encoding="utf-8")
    for week, message in proposal["messages"].items():
        (directory / f"telegram-{week}.md").write_text(message, encoding="utf-8")
        rendered = render_event_markdown(message.replace("<!-- NEXT TELEGRAM MESSAGE -->", "\n---\n"), safe_mode="escape")
        (directory / f"telegram-{week}.html").write_text(
            '<!doctype html><html lang="it"><meta charset="utf-8"><title>Telegram draft</title><body>' + rendered + '</body></html>', encoding="utf-8")
    preview = directory / "event-pages"
    preview.mkdir(exist_ok=True)
    index = ["<!doctype html><html><meta charset='utf-8'><title>Calendar preview</title><body>",
             "<h1>Proposed event pages</h1>", "<p>Partial preview: resolve blockers first.</p>" if proposal["errors"] else "", "<ul>"]
    for path, change in sorted(proposal["writes"].items()):
        if change["after"] is None:
            continue
        metadata, body = read_event_source(change["after"])
        rendered = render_event_page(metadata, body)
        rendered = rendered.replace('href="../', 'href="https://ludimus.it/').replace('src="../', 'src="https://ludimus.it/')
        name = Path(path).with_suffix(".html").name
        (preview / name).write_text(rendered, encoding="utf-8")
        index.append(f'<li><a href="{name}">{html.escape(name)}</a></li>')
    index.append("</ul></body></html>")
    (preview / "index.html").write_text("\n".join(index), encoding="utf-8")


def apply_plan(proposal, root=ROOT, build=True, recheck=None):
    if proposal["errors"]:
        raise CalendarError("Resolve every blocker before applying")
    if recheck is not None and recheck()["_fingerprint"] != proposal["_fingerprint"]:
        raise CalendarError("Calendar or input files changed during this run; regenerate the preview before applying")
    for path, expected in proposal["_inputs"].items():
        if digest(source_text(root / path)) != expected:
            raise CalendarError(f"Input file changed during this run: {path}")
    for path, change in proposal["writes"].items():
        if source_text(root / path) != change["before"]:
            raise CalendarError(f"File changed since preview: {path}")
    for path, change in proposal["writes"].items():
        target = root / path
        if change["after"] is None:
            target.unlink(missing_ok=True)
            (root / "events" / (target.stem + ".html")).unlink(missing_ok=True)
        elif change["before"] != change["after"]:
            target.write_text(change["after"], encoding="utf-8")
    (root / STATE).write_text(json.dumps(proposal["state"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if build:
        subprocess.run([sys.executable, str(root / "processors/generate.py")], cwd=root, check=True)


def date_arg(value):
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--ics", type=Path, help="Offline Calendar export")
    sources.add_argument("--url", default=DEFAULT_FEED, help="Public ICS feed; default is the Ludimus Calendar")
    parser.add_argument("--week", type=date_arg, help="Any date in the selected Monday–Sunday week")
    parser.add_argument("--from", dest="first", type=date_arg, help="First included date")
    parser.add_argument("--to", dest="last", type=date_arg, help="Last included date")
    parser.add_argument("--adopt", action="store_true", help="Preview/adopt existing unmanaged event sources")
    parser.add_argument("--apply", action="store_true", help="Apply a reviewed plan, then rebuild the website")
    parser.add_argument("--output-dir", type=Path, help="Existing external directory for report and Markdown/HTML drafts")
    parser.add_argument("--brief", action="store_true", help="Print a summary; use --output-dir for the full report")
    args = parser.parse_args(argv)
    if args.week and (args.first or args.last):
        parser.error("Use --week or --from/--to")
    if bool(args.first) != bool(args.last):
        parser.error("Use --from and --to together")
    if args.brief and not args.output_dir:
        parser.error("--brief requires --output-dir so the full preview remains available")
    if args.first:
        first, last = args.first, args.last
    else:
        day = args.week or (dt.datetime.now(ROME).date() + dt.timedelta(days=7))
        first = day - dt.timedelta(days=day.weekday())
        last = first + dt.timedelta(days=6)
    if last < first:
        parser.error("--to must be on or after --from")
    start = dt.datetime.combine(first, dt.time(), ROME)
    end = dt.datetime.combine(last + dt.timedelta(days=1), dt.time(), ROME)
    try:
        def read_calendar():
            return icalendar.Calendar.from_ical(args.ics.expanduser().read_bytes()) if args.ics else fetch_calendar(args.url)

        calendar = read_calendar()
        proposal = plan(calendar, start, end, adopt=args.adopt)
        if args.brief:
            print(f"Range: {first}–{last} (Europe/Rome)")
            print(f"Calendar occurrences: {proposal['total']}; mapped: {len(proposal['entries'])}; blockers: {len(proposal['errors'])}")
            for error in proposal["errors"]:
                print("BLOCKER: " + error)
        else:
            print(report(proposal))
        if args.output_dir:
            output_artifacts(proposal, args.output_dir)
        if args.apply:
            apply_plan(proposal, recheck=lambda: plan(read_calendar(), start, end, adopt=args.adopt))
            print("Applied and rebuilt. Review git diff, then publish the site and paste the draft.")
        return 2 if proposal["errors"] else 0
    except (CalendarError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
