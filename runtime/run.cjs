"use strict";
const fs = require("node:fs");
const path = require("node:path");

// Python sends 11 little-endian 32-bit integers, then the RGB pixels for the whole image.
// Keep the scale bar in the frame. We need to read it before we can check the cell.
function run() {
  const frame = fs.readFileSync(0);
  const headerBytes = 44;
  if (frame.length < headerBytes) throw Error("The image header is shorter than 44 bytes.");
  const args = Array.from({length: 11}, (_, index) => frame.readInt32LE(index * 4));
  const [width, height] = args;
  if (width < 48 || height < 48 || width * height > 12000000 ||
      frame.length !== headerBytes + width * height * 3) throw Error("Check the image dimensions and the number of RGB bytes sent.");
  // We split the runtime so both files fit in a GitHub browser upload.
  const parts = ["community.wasm.part1", "community.wasm.part2"];
  const bytes = Buffer.concat(parts.map(name => fs.readFileSync(path.join(__dirname, name))));
  const module = new WebAssembly.Module(bytes);
  const instance = new WebAssembly.Instance(module, {
    frame: {
      pixel(index) {
        const offset = headerBytes + index * 3;
        return frame[offset] | (frame[offset + 1] << 8) | (frame[offset + 2] << 16);
      }
    }
  });
  process.stdout.write(String(instance.exports.analyze(...args)));
}
try {
  run();
} catch (error) {
  process.stderr.write(String(error.message));
  process.exitCode = 1;
}

