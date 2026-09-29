# Scope and methodology

[← Model list](../README.md#models)

This is a curated research snapshot of text-to-image architectures and named model families. It covers GANs, autoregressive and masked image-token models, pixel-space and latent diffusion, diffusion transformers and flow matching, continuous-token autoregressive models, unified multimodal models, few-step and on-device releases, and selected commercial interfaces. It is not a claim to enumerate every private model, fine-tune, LoRA or community checkpoint.

## Inclusion and grouping

Each entry has a documented path from a text prompt to a generated image and at least one primary source. Unified multimodal models are included when their text-to-image generation is documented. Models that also edit images are included, with editing noted as an interaction. Add-on control and adaptation modules (ControlNet, IP-Adapter, LoRA), personalization methods (DreamBooth, textual inversion), editing-only methods, guidance and sampling techniques, safety and concept-erasure methods, standalone autoencoders and image tokenizers, and text-to-video systems are outside this catalog.

Distinct research generations have separate cards: Stable Diffusion 1.x/2.x, SDXL and Stable Diffusion 3 are separate families. Sizes, resolutions, quantizations and closely related checkpoints remain variants. A distilled model gets its own card only when its architecture or sampling regime is the subject of a separate primary source.

Groups are navigation aids, not mutually exclusive technical claims:

| Group | Organizing feature |
| --- | --- |
| Early | Pre-GAN neural text-to-image generation, such as recurrent attention and variational models |
| GAN | Adversarially trained generators, including multi-stage and large-scale GANs |
| AR token | Autoregressive prediction of discrete image tokens |
| Masked token | Parallel or iterative masked prediction of discrete image tokens |
| Pixel diffusion | Diffusion in pixel space, often cascaded through super-resolution stages |
| Latent U-Net | Diffusion in an autoencoder latent space with a U-Net denoiser |
| DiT / flow | Transformer denoisers, including MMDiT designs, rectified flow and flow matching |
| Continuous AR | Autoregressive or masked prediction of continuous tokens, often with a diffusion head, and AR–diffusion hybrids |
| Unified | One model for multimodal understanding and image generation |
| Efficient | Releases centered on few-step sampling, distillation or on-device inference |
| API | Selected commercial interfaces with limited architectural disclosure |

For example, Würstchen is a latent U-Net model with a highly compressed prior stage; Muse is a masked token model whose text conditioning comes from a frozen language model; Transfusion combines next-token prediction with diffusion in one transformer and appears under Unified. Efficient and API are deployment groups. Inclusion does not establish that weights are available or that a model runs on every local device.

## Modalities and interaction

- **T:** the text prompt, including negative prompts and structured prompt formats.
- **I input:** a reference, source or condition image, often optional and variant-dependent. It does not establish image-understanding capability. Training-only images are not an inference input.
- **I output:** a generated image through the documented complete pipeline, including decoders and documented super-resolution stages.
- **V / A:** video or audio, used only when a unified model documents them as inputs or outputs alongside text-to-image generation.
- **generation:** text-to-image synthesis is established; this label makes no quality or latency claim.
- **editing:** the source also documents text-guided editing of an input image with the same model. Requires I input.

Modality sets summarize the family. They do not promise all combinations for all variants. Spatial controls (layouts, masks, depth, pose), numeric parameters and style codes are described in notes rather than added as separate modalities.

## Sources, dates, licenses and figures

Architecture and capability statements use linked papers, developer repositories, model cards and official documentation. Review levels distinguish abstracts, READMEs and other source types; they do not imply reproducing results or running model weights. Source dates mean first paper submissions or explicitly dated announcements, not necessarily release dates. Missing dates remain blank. Claims that cannot be tied to a primary source are left out rather than guessed.

The optional `license` field records code and weight licenses exactly as the developer's repository or model card states them, as reviewed on the source's `reviewed_on` date. A missing license field means it was not established, not that the model is unlicensed. Licenses change between versions; variant-specific terms belong in the notes.

Every card has a local image. Paper or developer figures retain attribution and their original download URL in [figure credits](../assets/architectures/CREDITS.md). Multi-panel figures and PDF excerpts preserve the technical content. Where a suitable primary-source figure is unavailable, a generated SVG explicitly summarizes documented inputs and outputs without inventing internal architecture. Third-party figures are included for architectural comparison and scholarly commentary and are not covered by the repository license; see the [figure notice](../assets/architectures/FIGURE_NOTICE.md).

Figures extracted from arXiv HTML may be converted to PNG. Multiple panels from the same figure can be assembled for display, with every original image URL retained in `origin_urls`. Figures drawn inline in arXiv HTML (TikZ/SVG) are cropped from the PDF. These are source figures; they do not assert that the full generation implementation is available.

## arXiv 2025+ import

The [2025 onward collection](t2i-arxiv-daily.md) screens every paper returned by a pinned arXiv API query for **"text-to-image" in the title**, first submitted **on or after 2025-01-01**. No maintained third-party daily list covers text-to-image, so the snapshot is fetched directly with `scripts/fetch_arxiv.py`. The [screening ledger](../data/t2i-arxiv-daily.json) records the query, retrieval date, a checksum over every snapshot row, and a decision and reason for each paper.

Most papers with "text-to-image" in their titles are methods applied to existing models (guidance, control, personalization, editing, safety, acceleration, evaluation) and are excluded with a recorded reason. Named generation systems and distinct unnamed architectures are included with explanatory names. Major releases whose titles do not contain the phrase, such as technical reports, are covered by the curated catalog instead.

The query is a discovery index. Repository links are checked against the paper, author-linked project pages or a matching author repository. `author-linked` means a GitHub source was identified, which may contain an implementation, a placeholder or supporting data; the notes say which where it matters. `not-found` is a review result, not a claim that no code exists. Retitled papers and extended versions share a family when they describe the same system. Withdrawn papers retain a visible status note.

The catalog format, validation approach and figure policy are adapted from [Awesome TTS Architectures](https://github.com/kadirnar/awesome-tts-architectures) (Apache-2.0). Model-level claims cite their own primary sources.

## Maintenance

[data/models.json](../data/models.json), [data/figures.json](../data/figures.json) and [the arXiv screening ledger](../data/t2i-arxiv-daily.json) are the sources of truth. Run `python3 scripts/catalog.py --check` to verify the catalog offline. See [CONTRIBUTING.md](../CONTRIBUTING.md) for updates and corrections.
