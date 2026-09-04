# Assets

Reader: Documentation maintainers. Question: Which assets are used and where did they come from?

Three files, and two of them are referenced by nothing in the tree on purpose.

| File | Used by |
|---|---|
| `banner.svg` | the top of [`../../README.md`](../../README.md) |
| `social-preview.svg` | the source the PNG is rendered from |
| `social-preview.png` | **uploaded to GitHub by hand**, under Settings → Social preview. Nothing links to it here, and that is expected: GitHub stores its own copy. |

The social preview **is** configured on the repository — the page serves an
`og:image` from `repository-images.githubusercontent.com` rather than the
generated default. Checked 2026-08-31. If that ever stops being true, these two
files are dead weight and should go: they exist only to feed that setting.
