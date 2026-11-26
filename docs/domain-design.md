# Domain design for Soccer Analytics

The core domain is **postgame reporting for a soccer team**. A coach records a match recap, saves it privately while working, and publishes it to their team. The league publishes fixtures and scores independently of those recaps.

## Contexts and vocabulary

| Context | Owns | Uses |
| --- | --- | --- |
| League (supporting) | Teams, fixtures, and public results | Team identities. A registered opponent links a fixture to a second team. An external opponent is a display name. |
| Match Reporting (core) | One recap per match and team, per-player stats, team notes, and individual feedback | Fixture participation from League, roster ownership and account membership from Team Access |
| Team Access (supporting) | Accounts, team memberships, coach and player roles, roster links, and invitations | Team IDs from League and roster entries that belong to that team |

A **team** is the privacy boundary. A **membership** grants a user one role in one team. A **roster entry** can exist before its player registers. A **player invitation** links one roster entry to one account when redeemed. A **fixture** has a home team, a registered away team or external opponent, and public match information. A **result** is a final score. A **recap** is the participating team's report, with lifecycle Draft → Published. A **team note** is intended for all team members. **Individual feedback** is intended for one rostered player and their coaches.

## Rules

| Information or action | Authorized audience |
| --- | --- |
| Public feed, fixture details, final score | Anyone |
| Create fixture or enter/update the public score | Coach of the home team that manages the fixture |
| Add/edit roster entries and issue player invitations | Coach of the roster's team |
| Create, edit, or publish a recap | Coach of that recap's participating team |
| Published statistics and team note | Members of the recap's team |
| Published individual feedback | Recipient and the recipient's team coaches |
| Draft recap | Coaches of the recap's team |
| Registration email | Account owner in the application. Server operators and authorized database access remain privileged. |

Two teams on the same match never share private recaps. Posting a final score does not publish a recap. Players cannot choose a team or role during registration. Invitations are time-limited, one-use, and scoped to one roster entry. Coaches are provisioned with a trusted local CLI. Coach actions derive the team from session membership. A published recap supports explicit published updates, while ordinary draft saves apply before first publication. Unpublished data stays out of the HTML response for players. A recap revision prevents stale forms from replacing newer work. Archiving a roster entry revokes its linked account’s team access and preserves historical performance.

## Code structure

Flask route modules follow these contexts. League views receive only public match columns. Team views select data by team and filter feedback on the server. A shared permission module resolves membership and enforces coach, team, fixture, and roster rules before reads or writes. SQLite transactions persist each recap and its stats/feedback together. Foreign keys and unique constraints protect the new relationships, and existing roster and match records remain available.

The migration retains legacy performance records. Their latest row per player and match is copied to a team recap when the player belongs to a participating team. Since the older app had no publication consent, these recaps start as private drafts. Duplicate, orphaned, or unmatched legacy rows are retained in the original table and excluded from the active recap as appropriate. Public fixtures stay visible. Legacy scores are marked final when both sides have valid, nonnegative integer scores. The migration does not infer a registered away team from a legacy free-text opponent.

## Privacy defaults and acceptance

Collect display name, email, and a password. Persist a password hash and keep email out of roster and recap queries. A stored invitation hash is sufficient to validate a code, so the plaintext code is shown only on issue. Notes are plain text and use HTML escaping when rendered. Bind database inputs as parameters. Protect forms with CSRF tokens and prevent shared caching of dynamic pages.

A successful demo has two coaches and two teams in one match. A visitor sees the score, each team sees only its own published recap, a player sees their own feedback, and a coach can work with their own roster but cannot edit the other team's players. A saved note containing literal angle brackets stays text. The UI supports narrow screens, keyboard navigation, and visible labels for forms and match status.
