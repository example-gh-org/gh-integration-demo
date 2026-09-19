# gh-integration-demo

Demo of publishing a markdown knowledge base as a website with GitHub Pages, fed by a knowledge base on the Edra platform.

- `knowledge-base/` holds the markdown source, one file per article, in the same folder layout as the Edra knowledge base it mirrors.
- `.github/workflows/publish-knowledge-base.yml` runs when a change to `knowledge-base/` lands on `main` (a merged pull request, or a sync commit from Edra). It converts each markdown file to HTML with pandoc and deploys the result to GitHub Pages.
- `scripts/build-site.sh` is the build step. Run it locally with pandoc and python3 installed to preview the output in `_site/`.

## How content gets here

The `kb-github-sync-v1` platform workflow in `edra-org/internal-fdbe` listens for commits landing on the Edra knowledge base's `main` branch. Each time one lands it renders every published article to markdown and replaces `knowledge-base/` with the result as a single commit on `main`, which triggers the Pages deploy above. Articles removed on the platform are removed here too.

Because the platform is the source of truth, edit content there: open a change request on the Edra knowledge base and publish it. A pull request that edits `knowledge-base/` directly will be overwritten by the next sync.

## Changing the site itself

Layout, styling, and the build live outside `knowledge-base/`, so they are never overwritten by a sync. Branch off `main`, edit `scripts/` or the workflow, and open a pull request.
