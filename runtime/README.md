# How the AML runtime handles a cell

We send the full smear image to the runtime with the two ends of the scale bar and the corners of the cell box. That keeps the bar and the cell in the same image. The runtime reads the printed length, measures the bar in pixels, and uses that scale to calculate the width and height of your box.

If you choose **Classify cell**, the runtime also gives you a **blast** or **non-blast** call. You choose what goes in the box, so focus, stain, and how closely you frame the cell all matter. The measurement also depends on whether the microscope put the correct scale on the image in the first place.

## How we checked this build

We compared the compiled runtime with a separate calculation using the original checkpoint. Both saw the same cell pixels. The calls matched on **34 of 34 inputs**, including 30 private microscopy images and four synthetic inputs.

That check tells us the conversion preserved the call on those inputs. We haven’t measured clinical sensitivity, specificity, or patient-level performance for this manual cell-selection workflow.

## Files in this folder

- `community.wasm.part1` and `community.wasm.part2` make up the compiled runtime and its trained weights. Keep both files in this folder. The app joins them when it runs.
- `run.cjs` passes the full image and its coordinates to the runtime.
- `SHA256SUMS.txt` gives the SHA-256 checksum for each part. Together, in order, the two files have the same checksum as the tested build, `3e6869994305363c7d186b5578a93f746d78ab0ca0f5431fb4dd28f551b2dc3b`.

The compiled runtime and weights have their own license. The JavaScript runner uses the project’s BSD 3-Clause license. [Runtime terms](LICENSE.txt) · [Code license](../LICENSE)
