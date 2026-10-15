// OCR helper for figma-to-pptx.py (macOS only; uses the Vision framework).
// Usage: swift ocr.mac.swift <image.png>
// Prints one line per recognised text line: x0 \t y0 \t x1 \t y1 \t text
// Coordinates are normalised 0..1 with a top-left origin.
// Compile once for speed: swiftc -O ocr.mac.swift -o ocr  (then --ocr-cmd ./ocr)
import Foundation
import Vision

guard CommandLine.arguments.count == 2 else {
    FileHandle.standardError.write("usage: ocr.mac.swift <image>\n".data(using: .utf8)!)
    exit(2)
}
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
do {
    try VNImageRequestHandler(url: url, options: [:]).perform([request])
} catch {
    FileHandle.standardError.write("ocr failed: \(error)\n".data(using: .utf8)!)
    exit(1)
}
for obs in request.results ?? [] {
    guard let text = obs.topCandidates(1).first?.string else { continue }
    let b = obs.boundingBox  // bottom-left origin
    print(String(format: "%.5f\t%.5f\t%.5f\t%.5f\t", b.minX, 1 - b.maxY, b.maxX, 1 - b.minY) + text)
}
