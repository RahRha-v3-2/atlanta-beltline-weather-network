# Milestones

These are the proposed milestones from the WeatherXM builder-grant draft. They are a plan, not a funded schedule and not a claim that the work is underway in the field. The draft has not been submitted by this repository.

The working assumption in the draft is about 24 weeks from approval. Week numbers below are that draft's numbers.

| # | Milestone | Draft window | Deliverable in the draft | Proposed cash | This repository |
| --- | --- | --- | --- | --- | --- |
| M1 | Eastside Trail pilot cluster | Weeks 0–6 | About 5 WeatherXM stations on consenting private host sites next to the Eastside Trail, visible on the WeatherXM explorer, with a deployment log, photos, and a QoD baseline | $4,500, and less if the program supplies stations | Not started. No site survey, no host permissions, no stations. |
| M2 | Open data pipeline, API, and MCP | Weeks 6–10 | Ingest from the WeatherXM API into Postgres, QoD filtering, air-quality fusion, a public REST API, an MCP server, Apache-2.0 repo, API docs | $1,500 | Early prototype only: client, schema, read API, MCP tool, and tests. No deployed service and no air-quality fusion. |
| M3 | Public safety dashboard and alerts | Weeks 10–16 | Heat-index and heat-island map, localized precipitation and flash-flood watch, wind advisories, plus a 30-day station-versus-airport comparison | $2,000 | Not started. `dashboard/` is a placeholder. No alert rules are evaluated. |
| M4 | Evidence package and expansion | Weeks 16–24 | 60–90 days of corridor data, a formal pilot proposal to Atlanta Beltline, Inc., a BeltLine app integration spec, a Westside expansion plan, and vendor outreach | $2,000 | Not started. There is no data report and no proposal has been sent to Atlanta Beltline, Inc. |

Proposed cash total in the draft: $10,000, plus station hardware and API access. WeatherXM does not publish a fixed grant amount. The figure is an applicant proposal and is not an award.

## Phase 1 boundary

M1 is planned on private host sites adjacent to the Eastside Trail so the cluster can proceed without Atlanta Beltline, Inc. property. Installing on BeltLine property is out of scope until the organization gives permission. No such permission exists.

M4's pilot proposal to Atlanta Beltline, Inc. is a future document. This repository is not that proposal, and it is not an integration with the BeltLine app.

## What "done" is not

A merged copy of this prototype does not close M2. M2 in the draft also includes a running public API, quality filtering on a live cluster, and air-quality fusion. Those wait on M1 stations and on an explicit decision to host the service.
