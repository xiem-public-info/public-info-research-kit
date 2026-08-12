#!/usr/bin/env swift
import AppKit
import Foundation
import Vision

struct OCRLine: Encodable {
    let text: String
    let confidence: Float
    let bboxNormalized: [String: Double]
    let bboxPixels: [String: Double]
}

struct OCRResult: Encodable {
    let schema: String
    let status: String
    let imagePath: String
    let imageWidth: Double
    let imageHeight: Double
    let recognitionLevel: String
    let languageCorrection: Bool
    let recognitionLanguages: [String]
    let lineCount: Int
    let lines: [OCRLine]
    let error: String?
    let errorDomain: String?
    let errorCode: Int?
}

func makeResult(
    status: String,
    imagePath: String,
    imageWidth: Double,
    imageHeight: Double,
    recognitionLanguages: [String] = ["zh-Hans", "en-US"],
    lineCount: Int = 0,
    lines: [OCRLine] = [],
    error: String? = nil,
    errorDomain: String? = nil,
    errorCode: Int? = nil
) -> OCRResult {
    return OCRResult(
        schema: "macos_vision_ocr_result.v1",
        status: status,
        imagePath: imagePath,
        imageWidth: imageWidth,
        imageHeight: imageHeight,
        recognitionLevel: "accurate",
        languageCorrection: true,
        recognitionLanguages: recognitionLanguages,
        lineCount: lineCount,
        lines: lines,
        error: error,
        errorDomain: errorDomain,
        errorCode: errorCode
    )
}

func emit(_ result: OCRResult) {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    if let data = try? encoder.encode(result), let text = String(data: data, encoding: .utf8) {
        print(text)
    } else {
        print("{\"status\":\"encode_error\"}")
    }
}

if CommandLine.arguments.count < 2 {
    let result = makeResult(
        status: "usage_error",
        imagePath: "",
        imageWidth: 0,
        imageHeight: 0,
        error: "Usage: vision_ocr.swift <image_path>"
    )
    emit(result)
    exit(2)
}

let imagePath = CommandLine.arguments[1]
let imageURL = URL(fileURLWithPath: imagePath)
let imageReference = imageURL.lastPathComponent

guard let image = NSImage(contentsOf: imageURL) else {
    emit(makeResult(
        status: "image_load_error",
        imagePath: imageReference,
        imageWidth: 0,
        imageHeight: 0,
        error: "Cannot load image"
    ))
    exit(1)
}

var proposedRect = CGRect(origin: .zero, size: image.size)
guard let cgImage = image.cgImage(forProposedRect: &proposedRect, context: nil, hints: nil) else {
    emit(makeResult(
        status: "cgimage_error",
        imagePath: imageReference,
        imageWidth: Double(image.size.width),
        imageHeight: Double(image.size.height),
        error: "Cannot create CGImage"
    ))
    exit(1)
}

let width = Double(cgImage.width)
let height = Double(cgImage.height)
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "en-US"]

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {
    try handler.perform([request])
    let observations = request.results ?? []
    let lines: [OCRLine] = observations.compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else {
            return nil
        }
        let box = observation.boundingBox
        let pixelX = Double(box.origin.x) * width
        let pixelY = (1.0 - Double(box.origin.y) - Double(box.height)) * height
        let pixelW = Double(box.width) * width
        let pixelH = Double(box.height) * height
        return OCRLine(
            text: candidate.string,
            confidence: candidate.confidence,
            bboxNormalized: [
                "x": Double(box.origin.x),
                "y": Double(box.origin.y),
                "width": Double(box.width),
                "height": Double(box.height)
            ],
            bboxPixels: [
                "x": pixelX,
                "y": pixelY,
                "width": pixelW,
                "height": pixelH
            ]
        )
    }
    emit(makeResult(
        status: "ok",
        imagePath: imageReference,
        imageWidth: width,
        imageHeight: height,
        recognitionLanguages: request.recognitionLanguages,
        lineCount: lines.count,
        lines: lines,
        error: nil
    ))
} catch {
    let nsError = error as NSError
    emit(makeResult(
        status: "ocr_error",
        imagePath: imageReference,
        imageWidth: width,
        imageHeight: height,
        recognitionLanguages: request.recognitionLanguages,
        error: nsError.localizedDescription,
        errorDomain: nsError.domain,
        errorCode: nsError.code
    ))
    exit(1)
}
