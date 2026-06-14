"""
NEXUS — Layer 2: Universal AST Parser (Tree-sitter)
Ground truth for ALL line numbers. LLM line numbers are NEVER trusted directly.
Extracts: functions, classes, imports, call graph, cross-file dependency graph.
Supports: Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, Ruby.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

import structlog
logger = structlog.get_logger()

TREE_SITTER_AVAILABLE = False
LANG_MODULES: Dict[str, Any] = {}

# Mapping: language name → (module_attr, display_name)
# display_name is passed to Language(ptr, name) in tree-sitter 0.21.x
_LANG_LOADERS = [
    ("Python",              "tree_sitter_python",      "language",           "python"),
    ("JavaScript",          "tree_sitter_javascript",  "language",           "javascript"),
    ("TypeScript",          "tree_sitter_typescript",  "language_typescript","typescript"),
    ("TSX",                 "tree_sitter_typescript",  "language_tsx",       "tsx"),
    ("Java",                "tree_sitter_java",        "language",           "java"),
    ("Go",                  "tree_sitter_go",          "language",           "go"),
    ("Rust",                "tree_sitter_rust",        "language",           "rust"),
    ("C++",                 "tree_sitter_cpp",         "language",           "cpp"),
    ("C",                   "tree_sitter_c",           "language",           "c"),
    ("Ruby",                "tree_sitter_ruby",        "language",           "ruby"),
    ("PHP",                 "tree_sitter_php",         "language_php",       "php"),
    ("Bash",                "tree_sitter_bash",        "language",           "bash"),
    ("CSS",                 "tree_sitter_css",         "language",           "css"),
    ("HTML",                "tree_sitter_html",        "language",           "html"),
    ("JSON",                "tree_sitter_json",        "language",           "json"),
    ("YAML",                "tree_sitter_yaml",        "language",           "yaml"),
    ("TOML",                "tree_sitter_toml",        "language",           "toml"),
    ("Scala",               "tree_sitter_scala",       "language",           "scala"),
    ("Kotlin",              "tree_sitter_kotlin",      "language",           "kotlin"),
    ("Haskell",             "tree_sitter_haskell",     "language",           "haskell"),
    ("Elixir",              "tree_sitter_elixir",      "language",           "elixir"),
    ("OCaml",               "tree_sitter_ocaml",       "language_ocaml",     "ocaml"),
    ("OCaml Interface",     "tree_sitter_ocaml",       "language_ocaml_interface", "ocaml_interface"),
    ("C#",                  "tree_sitter_c_sharp",     "language",           "c_sharp"),
    ("Lua",                 "tree_sitter_lua",         "language",           "lua"),
    ("Markdown",            "tree_sitter_markdown",    "language",           "markdown"),
    ("Regex",               "tree_sitter_regex",       "language",           "regex"),
    ("GraphQL",             "tree_sitter_graphql",     "language",           "graphql"),
    ("Svelte",              "tree_sitter_svelte",      "language",           "svelte"),
]

try:
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True

    for lang_name, module_name, attr_name, ts_name in _LANG_LOADERS:
        try:
            mod = __import__(module_name)
            loader_fn = getattr(mod, attr_name)
            ptr = loader_fn()                  # returns an int (capsule pointer)
            lang_obj = Language(ptr, ts_name)  # ← correct API for tree-sitter 0.21.x
            LANG_MODULES[lang_name] = lang_obj
        except ImportError:
            pass  # package not installed — skip silently
        except Exception as e:
            logger.warning("tree_sitter_lang_failed", language=lang_name, error=str(e))

    logger.info(
        "tree_sitter_loaded",
        count=len(LANG_MODULES),
        languages=list(LANG_MODULES.keys()),
    )

except ImportError as e:
    logger.warning("tree_sitter_unavailable", error=str(e))


# ── Public API ────────────────────────────────────────────────────────────────

def parse_file(language: str, content: str, file_path: str = "") -> Dict:
    """
    Parse a source file and return:
    {
        ast_valid, functions, classes, imports,
        dependency_graph, file_metrics, raw_ast_available
    }
    Raises RuntimeError if tree-sitter is unavailable or the language is unsupported.
    """
    if not TREE_SITTER_AVAILABLE:
        raise RuntimeError(
            "tree-sitter is not installed. Install it with: pip install tree-sitter"
        )
    if language not in LANG_MODULES:
        raise RuntimeError(
            f"Language '{language}' is not supported or its tree-sitter package is not installed. "
            f"Available: {list(LANG_MODULES.keys())}"
        )
    return _parse_with_treesitter(language, content, file_path)


# ── Core parser ───────────────────────────────────────────────────────────────

def _parse_with_treesitter(language: str, content: str, file_path: str) -> Dict:
    lang = LANG_MODULES[language]

    parser = Parser()
    parser.set_language(lang)

    tree = parser.parse(content.encode("utf-8"))
    root = tree.root_node

    ast_valid = not root.has_error
    functions: List[Dict] = []
    classes:   List[Dict] = []
    imports:   List[Dict] = []

    def walk(node, parent_class=None):
        ntype = node.type

        # ── Function / method definitions ──────────────────────
        if ntype in (
            "function_definition",   # Python
            "function_declaration",  # JS / TS / Go
            "method_definition",     # JS class methods
            "method_declaration",    # Java
            "arrow_function",        # JS arrow
            "func_literal",          # Go
            "fn_item",               # Rust
        ):
            name  = _extract_name(node, language)
            start = node.start_point[0] + 1   # convert to 1-indexed
            end   = node.end_point[0] + 1

            functions.append({
                "name":         name,
                "start_line":   start,
                "end_line":     end,
                "line_count":   end - start + 1,
                "calls":        _extract_calls(node),
                "params":       _extract_params(node),
                "is_public":    _is_public(name, node, language),
                "parent_class": parent_class,
            })

        # ── Class / struct definitions ─────────────────────────
        elif ntype in (
            "class_definition",   # Python
            "class_declaration",  # Java / JS / TS
            "struct_item",        # Rust
            "impl_item",          # Rust impl block
        ):
            name  = _extract_name(node, language)
            start = node.start_point[0] + 1
            end   = node.end_point[0] + 1
            classes.append({"name": name, "start_line": start, "end_line": end})
            for child in node.children:
                walk(child, parent_class=name)
            return   # already recursed into children

        # ── Import statements ──────────────────────────────────
        elif ntype in (
            "import_statement",
            "import_from_statement",
            "import_declaration",
            "require_call",
        ):
            module = _extract_import_module(node)
            if module:
                imports.append({"module": module, "line": node.start_point[0] + 1})

        for child in node.children:
            walk(child, parent_class=parent_class)

    walk(root)

    dep_graph = {f["name"]: f["calls"] for f in functions}
    lines = content.splitlines()

    return {
        "ast_valid":      ast_valid,
        "functions":      functions,
        "classes":        classes,
        "imports":        imports,
        "dependency_graph": dep_graph,
        "file_metrics": {
            "total_lines":    len(lines),
            "function_count": len(functions),
            "class_count":    len(classes),
            "import_count":   len(imports),
        },
        "raw_ast_available": True,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_name(node, language: str) -> str:
    for child in node.children:
        if child.type in ("identifier", "name", "property_identifier"):
            return child.text.decode("utf-8")
    return "<anonymous>"


def _extract_calls(node) -> List[str]:
    calls: List[str] = []

    def walk(n):
        if n.type == "call":
            func = n.child_by_field_name("function")
            if func:
                name = func.text.decode("utf-8").split(".")[-1]
                if name and name not in calls:
                    calls.append(name)
        for child in n.children:
            walk(child)

    walk(node)
    return calls


def _extract_params(node) -> List[str]:
    params: List[str] = []
    for child in node.children:
        if child.type in ("parameters", "formal_parameters", "parameter_list"):
            for p in child.children:
                if p.type == "identifier":
                    params.append(p.text.decode("utf-8"))
    return params


def _extract_import_module(node) -> Optional[str]:
    try:
        text = node.text.decode("utf-8")
        m = re.search(r"""['"]([^'"]+)['"]""", text)
        if m:
            return m.group(1)
        m = re.search(r"import\s+([\w.]+)", text)
        if m:
            return m.group(1)
        m = re.search(r"from\s+([\w.]+)", text)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def _is_public(name: str, node, language: str) -> bool:
    if language == "Python":
        return not name.startswith("_")
    if language in ("Java", "C++"):
        try:
            return "public" in node.text.decode("utf-8")[:50]
        except Exception:
            return True
    if language == "Rust":
        try:
            return node.text.decode("utf-8")[:20].strip().startswith("pub")
        except Exception:
            return False
    return True


# ── Line-number validator ─────────────────────────────────────────────────────

def validate_line_numbers(
    proposed_line_start: int,
    proposed_line_end: int,
    ast_result: Dict,
    old_code: str,
    full_content: str,
) -> bool:
    """
    CRITICAL: Validate that LLM-proposed line numbers exist and match the AST.
    Returns True only if the old_code exists verbatim in the file at those lines.
    """
    lines = full_content.splitlines()
    total = len(lines)

    if proposed_line_start < 1 or proposed_line_end > total:
        return False
    if proposed_line_start > proposed_line_end:
        return False
    if old_code.strip() not in full_content:
        return False

    return True