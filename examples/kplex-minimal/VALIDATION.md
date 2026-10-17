# Native navigation observation

Observed 2026-10-15 America/Bogota (2026-10-16 UTC), using the official K-Plex
0.1.3 release in an isolated Obsidian profile and synthetic vault under `/tmp`.
Obsidian ran from the installed app package; its exact app version was not
recorded. Plugin source inspected during design and released binary tested are
distinct evidence. No personal library or plugin settings were changed.

## Passed

- Explanation centered: map is `parent`, original source is `left`, challenge
  is `right` in K-Plex's rendered node elements.
- Click source, then explanation: inverse evidence navigation works.
- Click challenge, then explanation: inverse tension navigation works.
- Click map: both notes are children, derived from their single `up` fields.
  Clicking the explanation returns to its original neighborhood.
- Obsidian opens both source heading links at their exact headings: Resultados
  at zero-based line 9 and Limitaciones at line 14. This used Obsidian's link
  opening API, not K-Plex's connection-details interaction.
- All four Raw/Wiki files matched repository bytes after the journey.
- The disposable window was closed and the launch process exited with code 0.

The agent inspected native screenshots and rendered DOM roles. Navigation used
click events on the actual K-Plex nodes, not a replacement graph implementation.
The sandbox remained enabled; the explicitly approved native run occurred
outside the command sandbox with a bounded lifetime and local inspection port.

## Finding and correction

Copying the README into the vault made its ordinary documentation links appear
as additional inferred parent relationships. Removing only that disposable copy
left exactly the intended map/source/challenge neighborhood. Preparation guidance
now copies Raw/Wiki only. This does not disable all inferred relationships or
establish how documentation should be filtered in an existing personal vault.
