package tree_sitter_munya_test

import (
	"testing"

	tree_sitter "github.com/tree-sitter/go-tree-sitter"
	tree_sitter_munya "github.com/tree-sitter/tree-sitter-munya/bindings/go"
)

func TestCanLoadGrammar(t *testing.T) {
	language := tree_sitter.NewLanguage(tree_sitter_munya.Language())
	if language == nil {
		t.Errorf("Error loading Munya grammar")
	}
}
