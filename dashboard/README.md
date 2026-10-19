# Dashboard placeholder

No dashboard is built yet. This directory is the reserved home for the public heat, flood, and wind view described in milestone M3.

The page, when it exists, will read `GET /observations/latest` from the API in this repository. It will not ship with sample weather, invented station markers, or a claim that Atlanta Beltline, Inc. or the BeltLine app is integrated.

## Planned views

- Heat index and urban-heat context for host sites tagged `eastside`.
- Precipitation, and a flash-flood watch limited to low-lying segments once those segments are surveyed.
- Wind readings for vendors and events, as an advisory computed from stored observations.
- Station data-quality scores next to each reading.
- A station-versus-nearest-airport comparison, which is an M3 report and not part of this prototype.

## Empty state

Until stations are ingested, the only honest UI is an empty state: phase 1 proposes about 5 WeatherXM stations on consenting private host sites next to the Eastside Trail, nothing is deployed, and no alert is in effect.

Air-quality tiles, if added later, stay visually separate from WeatherXM-verified observations. Those sensors are not part of this scaffold.
