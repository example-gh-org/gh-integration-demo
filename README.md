# gh-integration-demo

Demo of publishing a markdown knowledge base as a website with GitHub Pages.

- `knowledge-base/` holds the markdown source. Currently one file: a Tokyo travel guide.
- `.github/workflows/publish-knowledge-base.yml` runs when a change to `knowledge-base/` lands on `main` (for example, a merged pull request). It converts each markdown file to HTML with pandoc and deploys the result to GitHub Pages.
- `scripts/build-site.sh` is the build step. Run it locally with pandoc installed to preview the output in `_site/`.

## Making a change

1. Branch off `main` and edit or add a markdown file in `knowledge-base/`.
2. Open a pull request and merge it.
3. The workflow rebuilds and redeploys the site automatically.
