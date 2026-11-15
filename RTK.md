<!-- rtk-owned: written by `rtk init --codex`, removed by `rtk init --codex --uninstall` -->

# Command output

Command output here is condensed to save tokens, keeping every signal and
dropping costly noise. Treat it as the complete result: run commands
normally, and batch related commands into one call to avoid extra turns.
Truncated results state their recovery path in their own output. Re-run a
command as `rtk bypass <cmd>` only when its result is unusable: empty when
output was clearly expected, contradicting its exit code, or garbled.
## Additional RTK Policy

Always prefer RTK-prefixed commands when an equivalent exists.

Examples:
- git status → rtk git status
- git diff → rtk git diff
- git log → rtk git log
- rg → rtk rg
- ls → rtk ls

Use normal commands when RTK has no equivalent or full output is required.

Never sacrifice accuracy, omit errors, or hide important diagnostic information to save tokens.