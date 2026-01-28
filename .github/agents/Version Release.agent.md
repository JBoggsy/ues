# Version Release Agent

This agent guides the process of creating a new version release for the UES project. It handles changelog updates, version bumping, TODO cleanup, and GitHub release creation.

## Prerequisites

Before invoking this agent, ensure:
- All feature work for the release is complete and merged to `main`
- Working directory is clean (`git status` shows no uncommitted changes)
- You are on the `main` branch
- `gh` CLI is installed and authenticated

## Required User Input

| Input | Description | Example |
|-------|-------------|---------|
| **New version** | The version to release (or "auto" for suggestion) | `0.3.0` or `auto` |

## Workflow Steps

### Phase 1: Pre-Release Validation

1. **Verify clean working directory**
   ```bash
   git status --porcelain
   ```
   - If not clean, STOP and ask user to commit or stash changes

2. **Verify on main branch**
   ```bash
   git branch --show-current
   ```
   - If not on `main`, STOP and ask user to switch branches

3. **Run test suite**
   ```bash
   uv run pytest
   ```
   - If tests fail, STOP and report failures
   - Capture total test count for README badge update

4. **Get current version**
   - Extract from `pyproject.toml` line 3: `version = "X.Y.Z"`

5. **Get last release tag**
   ```bash
   git tag -l --sort=-v:refname | head -1
   ```

### Phase 2: Analyze Changes (for Semver Suggestion)

1. **Get commits since last release**
   ```bash
   git log <last_tag>..HEAD --oneline
   ```

2. **Analyze commit messages for semver suggestion**
   - **MAJOR** (breaking changes): Look for "BREAKING", "!:", removes/renames public API
   - **MINOR** (new features): Look for "feat:", "Add", new endpoints, new modalities
   - **PATCH** (fixes only): Look for "fix:", "Fix", bug fixes, documentation

3. **Present suggestion to user**
   ```
   Current version: 0.2.0
   Commits since v0.2.0: 23
   
   Detected changes:
   - 3 new features (feat:)
   - 5 bug fixes (fix:)
   - 0 breaking changes
   
   Suggested version: 0.3.0 (MINOR - new features added)
   
   Enter version to release [0.3.0]: 
   ```

4. **User confirms or overrides version**

### Phase 3: Update CHANGELOG.md

1. **Review commits in detail**
   ```bash
   git log <last_tag>..HEAD --oneline
   git show <hash> --stat --oneline  # For significant commits
   ```

2. **Update CHANGELOG.md following Keep a Changelog format**
   
   Required sections (only include if there are items):
   - `### Added` - New features
   - `### Changed` - Changes to existing functionality
   - `### Deprecated` - Features to be removed in future
   - `### Removed` - Removed features
   - `### Fixed` - Bug fixes
   - `### Security` - Security fixes

3. **Convert `[Unreleased]` section**
   - Change `## [Unreleased]` to `## [Unreleased]\n\n## [X.Y.Z] - YYYY-MM-DD`
   - Add new empty Unreleased section above

4. **Update footer links**
   ```markdown
   [Unreleased]: https://github.com/JBoggsy/ues/compare/vX.Y.Z...HEAD
   [X.Y.Z]: https://github.com/JBoggsy/ues/compare/vPREVIOUS...vX.Y.Z
   [PREVIOUS]: https://github.com/JBoggsy/ues/releases/tag/vPREVIOUS
   ```

### Phase 4: Clean Up TODO.md

1. **Remove completed sections**
   - Any section marked with `✅ Completed:` should be removed entirely
   - The CHANGELOG now tracks completed work

2. **Remove completed items from incomplete sections**
   - Items marked `[x]` or with `~~strikethrough~~`
   - Items marked as done inline

3. **Verify remaining TODOs against codebase**
   - For each unchecked item, search codebase to confirm it's not done
   - If implemented, remove from TODO

4. **Update test counts in TODO.md**
   - Update "Total Tests" count
   - Update per-category counts:
     ```bash
     uv run pytest --co -q tests/models/ 2>/dev/null | tail -1
     uv run pytest --co -q tests/api/ 2>/dev/null | tail -1
     uv run pytest --co -q tests/client/ 2>/dev/null | tail -1
     uv run pytest --co -q tests/agent_testing/ 2>/dev/null | tail -1
     ```

### Phase 5: Update Version Numbers

Update version in these files:

| File | Location | Update |
|------|----------|--------|
| `pyproject.toml` | Line 3 | `version = "X.Y.Z"` |
| `src/ues/main.py` | Root endpoint | `"version": "X.Y.Z"` |
| `README.md` | Test badge | `tests-NNNN%20passing` |
| `README.md` | Endpoint count (if changed) | `NN endpoints` |

Then regenerate lock file:
```bash
uv sync
```

### Phase 6: Commit and Tag

1. **Stage all changes**
   ```bash
   git add -A
   ```

2. **Create commit**
   ```bash
   git commit -m "Release vX.Y.Z

   - Bump version from A.B.C to X.Y.Z
   - Update CHANGELOG.md with all changes since vA.B.C
   - Update README.md test count badge (NNNN tests)
   - Clean up TODO.md, remove completed items

   AI generated commit message"
   ```

3. **Create annotated tag**
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z

   Key features:
   - Feature 1
   - Feature 2
   - Feature 3"
   ```
   
   Tag message should summarize the 3-5 most important changes.

### Phase 7: Push and Create Draft Release

1. **Push commit and tag**
   ```bash
   git push origin main
   git push origin vX.Y.Z
   ```

2. **Create draft GitHub release**
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --draft --notes "RELEASE_NOTES"
   ```
   
   Release notes should include:
   - Summary of key features (from CHANGELOG Added section)
   - Summary of changes (from CHANGELOG Changed section)  
   - Summary of fixes (from CHANGELOG Fixed section)
   - Link to full CHANGELOG

3. **Report to user**
   ```
   ✅ Draft release created: https://github.com/JBoggsy/ues/releases/tag/vX.Y.Z
   
   Please review the release notes and click "Publish" when ready.
   ```

## Rollback Procedure

If something goes wrong after committing but before publishing:

```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag (if pushed)
git push origin --delete vX.Y.Z

# Reset commit
git reset --hard HEAD~1

# Force push (if already pushed)
git push origin main --force
```

## Endpoint Count

To get the current endpoint count:
```bash
grep -r "@router\." src/ues/api/routes/ --include="*.py" | wc -l
```

## Version Locations Reference

Files that contain version numbers (for verification):

**Must update:**
- `pyproject.toml` - Source of truth
- `src/ues/main.py` - API response
- `CHANGELOG.md` - Release notes
- `README.md` - Badges

**Auto-updated:**
- `uv.lock` - Via `uv sync`
- `src/ues/models/version.py` - Reads from package metadata

**Examples only (do NOT update):**
- `docs/**/*.md` - Example JSON snippets showing `"ues_version": "X.Y.Z"`
- `tests/**/*.py` - Test fixtures with version strings

## Keep a Changelog Format Reference

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Features to be removed

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes

## [Previous Version] - Date
...

[Unreleased]: https://github.com/USER/REPO/compare/vX.Y.Z...HEAD
[X.Y.Z]: https://github.com/USER/REPO/compare/vPREV...vX.Y.Z
```
