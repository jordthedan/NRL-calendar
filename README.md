# NRL Live Calendar

A live, read-only Apple Calendar feed for NRL fixtures.

## What it does

- Pulls fixture data from the official NRL draw.
- Includes regular-season and finals rounds as they are published.
- Checks automatically every hour using GitHub Actions.
- Uses stable event IDs so opponent, kickoff-time and venue changes update existing calendar events instead of creating duplicates.
- Includes a 30-minute event alert.
- Stores event times as absolute UTC instants so Apple Calendar displays them correctly in Australia/Sydney, including daylight-saving changes.
- Checks the previous, current and next calendar year. This means the same subscription is designed to roll into future NRL seasons (2027, 2028 and onward) once the NRL publishes those fixtures; no new calendar subscription should be needed.

## Apple Calendar subscription

Subscribe to:

https://jordthedan.github.io/NRL-calendar/nrl-calendar.ics

The repository must have GitHub Pages enabled from the `main` branch / repository root for that URL to work.

## Update schedule

The workflow runs hourly at minute 17 and can also be run manually from the Actions tab.

If the NRL endpoint is temporarily unavailable, the generator refuses to replace the feed with an empty calendar.
