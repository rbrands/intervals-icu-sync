# Training Architect Test Chat

Use this page to test the Foundry agent locally via Chainlit.

## Before You Start

- Ensure `.env` contains `FOUNDRY_PROJECT_ENDPOINT`, `ATHLETE_ID`, and `INTERVALS_API_KEY`.
- Use the Python 3.12 Chainlit environment for local UI tests.
- Recommended launcher on Windows: `./Start-Chainlit.ps1 -Port 8013 -Watch`.

## In-Chat Commands

- `/settings` shows current runtime settings.
- `/discipline <climber|criterium|roadrace|marathon>` sets the discipline for the session.
- `/language <de|en|...>` sets the response language for the session.

## Notes

- This UI uses the same structured inputs as `foundry-agent/invoke_agent.py`.
- Credentials are sent per request and should never be logged.
