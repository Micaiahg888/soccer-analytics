# Implementation changes and privacy review

## What changed and why

| Files | Change and reason |
| --- | --- |
| `app.py`, `soccer/__init__.py` | The entry point loads a Flask app factory. A single factory configures sessions, headers, CSRF, database initialization, and blueprints before serving requests. The factory also lets tests choose an isolated database. |
| `database.py` → `soccer/database.py` and `soccer/schema.sql` | Request-scoped SQLite connections and a versioned migration replace import-time setup. Added accounts, memberships, invitations, team recaps, and recap entries. The migration preserves legacy data and copies eligible stats to drafts. |
| `soccer/permissions.py` | Team membership is loaded from the database for each request. Coach-only routes enforce the role, then queries or fixture checks enforce team scope. Roles and team ownership come from the server. |
| `soccer/accounts.py`, `templates/account.html` | Added sign-in, sign-out, account-owner profile, coach provisioning, and player registration using one-use invitation codes. This gives coaches and players a clear way into the private workspace without self-assigned roles. |
| `soccer/league.py`, `templates/league.html`, `templates/_fixtures.html`, `templates/match.html` | The public homepage now separates upcoming fixtures from recent results and adds team and season filters. Match views fetch public fixtures separately from team context. |
| `soccer/team_space.py`, `templates/my_team.html`, `templates/fixture_edit.html`, `templates/player_edit.html`, `templates/player.html`, `templates/compare.html` | The team workspace brings matches, roster actions, and team stats together. Coaches enter fixtures and manage the roster here. Player profiles and comparisons are team-scoped and use published recaps. Archiving revokes player membership and preserves match history. |
| `soccer/reporting.py`, `templates/recap_edit.html` | A single roster-based form replaces individual stat-entry and stat-edit pages. Drafts, published recaps, and individual feedback share a transaction. A revision check prevents an older browser tab from silently overwriting a newer recap. Saving a public score is a separate form so it cannot publish notes. |
| `soccer/forms.py` | Server-side field and number validation applies consistent bounds before using form data. Bound query parameters keep user text separate from SQL. |
| `templates/base.html`, `templates/error.html`, `static/site.css` | Shared layout and styles add consistent navigation, responsive match cards, labeled inputs, skip navigation, focus outlines, and readable errors. |
| Legacy `index.html`, `analytics.html`, `team.html`, `edit_player.html`, `add_stat.html`, `edit_stat.html` | Superseded by the league, team, and recap screens. The placeholder leaderboard and unauthenticated write/delete routes were retired. Team creation moved to the trusted CLI. Existing public match URLs still work. |
| `requirements.txt`, `.gitignore`, `README.md` | Declared the app and form-protection dependencies, excluded local app secrets, and documented how to start the app, provision accounts, and rehearse the demo. |
| `tests/test_soccer.py` | Added regression tests for the complete authorization and publication flow, literal markup, form protection, invitation redemption, revocation, and migration of existing data. |
| `docs/domain-design.md`, this file | Document the design rules, trace implementation changes to their reasons, and record residual privacy issues for the report. |

## Privacy issues and controls

| Issue | Control |
| --- | --- |
| A public page or an alternate URL could disclose a roster, team stats, or draft content. | The league feed uses public fixture columns. Protected routes resolve server-side membership. A match shared by two teams has separate recaps, and publication only opens a recap to its own team. |
| A teammate could read someone else's individual coach feedback. | The query returns individual feedback to the linked recipient or coaches of that team. The player index and comparisons contain neither feedback nor account email. |
| A player could claim another team, coach privileges, or a teammate's roster identity. | Registration uses the invitation's team and roster entry. The server creates the player role. An invitation is short-lived, stored as a hash, and redeemed once. Reissuing replaces the pending code. |
| A logged-in coach or player could submit changes outside their scope. | Coach verbs check the role and team. The same check applies whether the request comes from the UI or another client. Cross-team player IDs in submitted recap forms are rejected. |
| Another site could cause a logged-in coach to submit a form. | State-changing routes require POST and a CSRF token. The session cookie uses HttpOnly and SameSite. |
| Stored note text could be interpreted as HTML. | User text is placed in ordinary HTML text or escaped form values with Jinja autoescaping. A Content Security Policy limits allowed content to the app. Test data with angle brackets verifies escaping in team notes and feedback. |
| User text could affect SQL statement structure. | Database calls bind input values. Any variable query clauses are fixed in code. |
| Registration exposes unnecessary personal data. | The app collects display name, email, and password. It stores a password hash, keeps email on the signed-in account's own profile, and does not request birthdates, addresses, or phone numbers. |
| Migrating from the older app could expose unpublished historical stats. | Compatible old stats enter new recaps as drafts. Historical records, including excluded rows, remain in the original table. Review and explicitly publish imported drafts as needed. |

## Limits before use with real player data

- A coach can place sensitive content in a shared note or a public fixture field. Public scores remain public and shared notes are visible to all current teammates. Use fictional players for the class demo.
- A player invite is a bearer code. Whoever receives a forwarded code can claim an unused roster entry. The classroom flow has no email verification, account recovery, or second factor.
- The app has no request rate limiting or security audit trail. A public deployment needs login throttling, monitoring, HTTPS, and a deployed session secret. The local development server is intended for localhost.
- SQLite and backups are readable by an operator with filesystem access. App access controls do not encrypt the database. Hosting needs restricted file access, backups, and a retention and deletion policy. Archiving revokes membership but retains historical stats and the account record.
- Frontend smoke checks cover desktop and narrow mobile layout, labels, and page overflow. A formal accessibility audit and assistive technology usability testing are separate work.

## Suggested screenshots for the report

1. `soccer/permissions.py`, from `team_access` through `roster_player`. Explain login, role, and team checks.
2. `soccer/reporting.py`, the query in `visible_recap`. Explain how the application filters unpublished recaps and individual feedback before rendering.
3. `templates/match.html`, the team note and individual feedback expressions. Pair these with the escaping test in `tests/test_soccer.py`.
4. A public match and the same match as a signed-in recipient. Use fictional names and exclude account data and invitation codes.
