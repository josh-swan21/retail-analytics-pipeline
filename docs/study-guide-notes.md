# Code study guide: walkthrough notes

## Stop 0: Guardrails

### .env.example
- This is an example of the settings needed for this project. It is particularly useful for other users wishing to replicate or contribute to the project, for reviewers who want to understand the settings that went into it, and for the owner, who may be working from a different or new device. It does not contain the user’s actual credentials and settings, only placeholders for users to fill in themselves. There is no password in this file because this repo uses key-pair authentication: the credential is a private .p8 key file, which .gitignore keeps out of the repo. If a setting in .env is wrong in an obvious way (a mistyped key path, username or setting name), an error is returned and the failure is obvious. However, if a value in .env is valid but wrong, such as a folder holding an older snapshot of data or a dev schema instead of CORE, the run still succeeds, and stakeholders downstream get the wrong numbers without anyone noticing.

### requirements.txt / requirements-dbt.txt
- Why split, and what -r does:
- Why dbt is pinned tighter than pandas:
- Drift risk, and what a lock file fixes: