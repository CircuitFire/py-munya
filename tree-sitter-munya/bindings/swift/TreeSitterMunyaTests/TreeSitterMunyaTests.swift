import XCTest
import SwiftTreeSitter
import TreeSitterMunya

final class TreeSitterMunyaTests: XCTestCase {
    func testCanLoadGrammar() throws {
        let parser = Parser()
        let language = Language(language: tree_sitter_munya())
        XCTAssertNoThrow(try parser.setLanguage(language),
                         "Error loading Munya grammar")
    }
}
