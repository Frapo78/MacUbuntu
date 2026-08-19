# MacUbuntu agent contract

MacUbuntu is designed for humans and AI automation. Humans receive concise localized output; agents must consume `--json` and stable machine fields rather than parsing translated prose.

## Project identity

MacUbuntu is an independent open-source project conceived and implemented by **Francesco Poltero**. Preserve this credit in public project documentation. Third-party software remains owned by its upstream maintainers; preserve `docs/CREDITS.md` and `docs/COMPONENTS.md` whenever integrations change.

## Safe autonomous flow

```bash
./macubuntu update --check --json
./macubuntu doctor --json
./macubuntu plan --json
./macubuntu macify --yes --json
./macubuntu status --json
```

A bare interactive `./macubuntu` is the human one-shot equivalent of `macify` and asks before mutation.

If `update --check --json` reports `data.status=update_available`, a normal official clean checkout may run `./macubuntu update --json`; start a new MacUbuntu process after an update.

## Non-negotiable rules

- Never edit `state.json` manually.
- Never bypass uninstall receipts with raw `apt remove`, Flatpak removal, file deletion or GSettings resets.
- Never work around an update blocker using `git reset --hard`, forced checkout or remote replacement.
- Treat `support.level=unsupported` and a blocked `doctor` result as hard stops.
- Inspect `plan` on experimental systems.
- Preserve user drift unless the user explicitly selects a documented force behavior.
- External components must have a reviewed upstream, a pinned/tested version where practical, a plan path, apply path and uninstall ownership semantics before joining the one-shot.
- Do not add arbitrary download domains. Runtime source downloads use an explicit allowlist.
- Do not enable WhiteSur libadwaita, GDM, Firefox-profile or GRUB rewrite helpers in the default flow without a dedicated reversible receipt design.
- Hardware drivers, GPU configuration, kernel, firmware, bootloader and disk changes remain outside the default macification profile.
- Never redistribute proprietary Apple fonts or operating-system assets.

## Third-party integration requirements

Before adding/updating a third-party project:

1. verify the current official upstream and target Ubuntu/GNOME compatibility;
2. prefer Ubuntu packages or upstream-maintained stable repositories over arbitrary binaries;
3. pin source commits and GNOME extension version tags used by a MacUbuntu release;
4. validate downloaded archive structure and metadata before copying to managed locations;
5. use MacUbuntu-specific filenames/directories when possible so existing user installations are not overwritten;
6. record a receipt immediately after each successful mutation;
7. define safe drift behavior and uninstall before enabling the component in `ALL_MODULES`;
8. update `docs/COMPONENTS.md` and `docs/CREDITS.md`;
9. add tests and require green CI before merge.

## Output contract

Normal mode is intentionally quiet. `--verbose` may stream technical subprocess output. `--json` must stay language-independent and contain stable action/status codes.

Fields may be added in minor versions; existing semantic fields should not be repurposed without a schema/version change.
