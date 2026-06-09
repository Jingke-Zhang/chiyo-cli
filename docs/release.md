# Release

This project currently uses git tags and GitHub Releases. Homebrew is the
preferred future distribution path; until then, releases document the
development-install state of the repository.

## Checklist

1. Review the commit range since the previous tag:

   ```sh
   git log --oneline --reverse vX.Y.Z..HEAD
   git diff --stat vX.Y.Z..HEAD
   ```

2. Move completed entries from `Unreleased` in `CHANGELOG.md` into a new version
   section.

3. Update `pyproject.toml` to the release version.

4. Run tests:

   ```sh
   make test
   ```

5. Commit the release metadata:

   ```sh
   git add CHANGELOG.md pyproject.toml
   git commit -m "docs: release vX.Y.Z"
   ```

6. Create an annotated tag:

   ```sh
   git tag -a vX.Y.Z -m "vX.Y.Z"
   ```

7. Push the commit and tag:

   ```sh
   git push
   git push origin vX.Y.Z
   ```

8. Create a GitHub Release from the tag. Use the matching `CHANGELOG.md` section
   as the release notes, and mark only the newest stable release as latest.

## Backfilled Releases

If a tag already exists but the GitHub Release is missing, create the GitHub
Release from the existing tag instead of retagging. Keep the release notes
limited to the commit range that produced that tag.
