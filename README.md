# automate mails
## Introduction
This is a script that helps me automate reading emails when I'm trying to find a job, cause it's easy to forget about some recrutation tasks/tests or to answer sometimes.

## Usage
You should have a virtual environment created, via `python3 -m venv venv`. Also, you should get all needed secrets and credentials and store it into the `keys.yaml` file.

```bash
source venv/bin/activate
python3 main.py
```

## TODO:
1. ~~read mails~~
2. simple gemini support for mails' categorizing
3. rewrite to async
4. if a mail is related to work, classify it by:
    - position
    - location
    - type (on-site, hybrid, remote)
    - recrutation state (cv sent, waiting, action required, rejected, approved)
5. store the data in a csv file
6. generate a google sheet with my data
7. also move read mails into special mail directory (so I wont see them)
8. do some logs
9. add a webhook/discord bot
10. host the app somewhere

## Interesting sources:
- https://ai.google.dev/gemini-api/docs/structured-output i could use it to make genai output parsing easier