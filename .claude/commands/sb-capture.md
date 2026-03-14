---
description: Capture a note into the second brain
allowed-tools: Bash
---

Capture the following into the second brain:

$ARGUMENTS

Steps:
1. Determine the content type (note, meeting, idea, people, coding, strategy)
2. Classify sensitivity: pii/private/public
3. Run: sb-capture --type note --title "$ARGUMENTS" --sensitivity public
4. Confirm the file path and ask if any follow-up is needed.
