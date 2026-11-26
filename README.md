# Soccer Analytics Platform

A public soccer league feed and a private team workspace. Coaches enter match stats, team notes, and individual feedback. Players see their team’s published recaps.

- [Domain design and access rules](docs/domain-design.md)
- [Implementation changes and privacy review](docs/changes-and-privacy.md)

## Run locally on Windows

1. Open the downloaded project folder that contains `app.py` in PowerShell.
2. Run these commands one at a time:

   ```powershell
   py -m venv venv
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   .\venv\Scripts\python.exe -m flask --app app run --port 5001
   ```

3. Open the [league feed](http://127.0.0.1:5001/) and leave PowerShell open.

A new local app creates `soccer.db` at the project root. To use data from the previous version, stop the old app, back up its `soccer.db`, and copy it into this folder before starting the new app. Compatible old player stats are migrated into private drafts. Existing teams, players, fixtures, and scores are kept. Legacy opponent names stay as external text because old fixtures have no opposing team ID.

## Set up a demo league

In a second PowerShell window in the same folder, create two fictional teams:

```powershell
.\venv\Scripts\python.exe -m flask --app app accounts add-team "Harbor FC"
.\venv\Scripts\python.exe -m flask --app app accounts add-team "Summit FC"
.\venv\Scripts\python.exe -m flask --app app accounts teams
```

Use the actual IDs printed above. When prompted, enter a display name, a unique demo email, and a password of at least 12 characters for each coach.

```powershell
.\venv\Scripts\python.exe -m flask --app app accounts add-coach 1
.\venv\Scripts\python.exe -m flask --app app accounts add-coach 2
```

Sign in as Harbor FC’s coach. In **My Team**, add a player, then use **Invite** to issue a one-use code. In a separate browser profile, open **Sign in → Join with a coach invitation** and register the player. Repeat for the other team if you want to demo the opposing player's view.

As Harbor FC’s coach, add a match against Summit FC, save a public final score, and save the team recap as a draft. Confirm the public score appears while the draft stays private. Publish the recap, then check the match as the Harbor player, the opposing player, and a signed-out visitor.

## Run the tests

```powershell
.\venv\Scripts\python.exe -m pip install pytest
.\venv\Scripts\python.exe -m pytest -q
```

The tests create separate temporary databases. For local development, the app generates a session key under `instance/`. For an HTTPS deployment, supply a shared random `SOCCER_SECRET_KEY`, set `SOCCER_HTTPS=1`, and use `SOCCER_DATABASE` to point to private persistent storage. Read the [privacy review](docs/changes-and-privacy.md#limits-before-use-with-real-player-data) before using real information.
