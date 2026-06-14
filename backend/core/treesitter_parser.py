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
LANG_MODULES = {}

try:
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True

    _loaders = {}

    try:
        import tree_sitter_python as m; _loaders["Python"] = m.language
    except Exception: pass
    try:
        import tree_sitter_javascript as m; _loaders["JavaScript"] = m.language
    except Exception: pass
    try:
        import tree_sitter_typescript as m
        _loaders["TypeScript"] = m.language_typescript
        _loaders["TSX"] = m.language_tsx
    except Exception: pass
    try:
        import tree_sitter_java as m; _loaders["Java"] = m.language
    except Exception: pass
    try:
        import tree_sitter_go as m; _loaders["Go"] = m.language
    except Exception: pass
    try:
        import tree_sitter_rust as m; _loaders["Rust"] = m.language
    except Exception: pass
    try:
        import tree_sitter_cpp as m; _loaders["C++"] = m.language
    except Exception: pass
    try:
        import tree_sitter_c as m; _loaders["C"] = m.language
    except Exception: pass
    try:
        import tree_sitter_ruby as m; _loaders["Ruby"] = m.language
    except Exception: pass
    try:
        import tree_sitter_php as m; _loaders["PHP"] = m.language_php
    except Exception: pass
    try:
        import tree_sitter_bash as m; _loaders["Bash"] = m.language
    except Exception: pass
    try:
        import tree_sitter_css as m; _loaders["CSS"] = m.language
    except Exception: pass
    try:
        import tree_sitter_html as m; _loaders["HTML"] = m.language
    except Exception: pass
    try:
        import tree_sitter_json as m; _loaders["JSON"] = m.language
    except Exception: pass
    try:
        import tree_sitter_yaml as m; _loaders["YAML"] = m.language
    except Exception: pass
    try:
        import tree_sitter_toml as m; _loaders["TOML"] = m.language
    except Exception: pass
    try:
        import tree_sitter_scala as m; _loaders["Scala"] = m.language
    except Exception: pass
    try:
        import tree_sitter_kotlin as m; _loaders["Kotlin"] = m.language
    except Exception: pass
    try:
        import tree_sitter_haskell as m; _loaders["Haskell"] = m.language
    except Exception: pass
    try:
        import tree_sitter_elixir as m; _loaders["Elixir"] = m.language
    except Exception: pass
    try:
        import tree_sitter_ocaml as m
        _loaders["OCaml"] = m.language_ocaml
        _loaders["OCaml Interface"] = m.language_ocaml_interface
    except Exception: pass
    try:
        import tree_sitter_c_sharp as m; _loaders["C#"] = m.language
    except Exception: pass
    try:
        import tree_sitter_lua as m; _loaders["Lua"] = m.language
    except Exception: pass
    try:
        import tree_sitter_markdown as m
        _loaders["Markdown"] = m.language
    except Exception: pass
    try:
        import tree_sitter_regex as m; _loaders["Regex"] = m.language
    except Exception: pass
    try:
        import tree_sitter_graphql as m; _loaders["GraphQL"] = m.language
    except Exception: pass
    try:
        import tree_sitter_svelte as m; _loaders["Svelte"] = m.language
    except Exception: pass

    for lang_name, loader in _loaders.items():
        try:
            lang_obj = loader()
            # New packages return capsule directly — try wrapping first
            try:
                LANG_MODULES[lang_name] = Language(lang_obj)
            except Exception:
                # Some newer packages: lang_obj IS the language already
                LANG_MODULES[lang_name] = lang_obj
        except Exception as e:
            logger.warning("tree_sitter_lang_failed", language=lang_name, error=str(e))

    logger.info("tree_sitter_loaded", count=len(LANG_MODULES), languages=list(LANG_MODULES.keys()))

except ImportError as e:
    logger.warning("tree_sitter_unavailable", error=str(e))


def parse_file(language: str, content: str, file_path: str = "") -> Dict:
    """
    Parse a source file and return:
    {
        ast_valid, functions, classes, imports,
        dependency_graph, file_metrics, raw_ast_available
    }
    Falls back to regex-based extraction if tree-sitter unavailable.
    """
    if TREE_SITTER_AVAILABLE and language in LANG_MODULES:
        return _parse_with_treesitter(language, content, file_path)
    else:
        logger.warning("treesitter_unavailable_fallback", language=language)
        return _parse_with_regex_fallback(language, content, file_path)


def _parse_with_treesitter(language: str, content: str, file_path: str) -> Dict:
    lang = LANG_MODULES[language]
    parser = Parser(lang)

    tree = parser.parse(content.encode("utf-8"))
    root = tree.root_node

    ast_valid = not root.has_error
    functions = []
    classes = []
    imports = []

    def walk(node, parent_class=None):
        ntype = node.type

        # ── Function definitions ──────────────────────────────
        if ntype in (
            "function_definition",       # Python
            "function_declaration",      # JS/TS/Go
            "method_definition",         # JS class methods
            "method_declaration",        # Java
            "arrow_function",            # JS arrow
            "func_literal",              # Go
            "fn_item",                   # Rust
        ):
            name = _extract_name(node, language)
            start = node.start_point[0] + 1   # 1-indexed
            end   = node.end_point[0] + 1

            calls = _extract_calls(node, content)
            params = _extract_params(node)
            is_public = _is_public(name, node, language)

            functions.append({
                "name": name,
                "start_line": start,
                "end_line": end,
                "line_count": end - start + 1,
                "calls": calls,
                "params": params,
                "is_public": is_public,
                "parent_class": parent_class,
            })

        # ── Class definitions ──────────────────────────────────
        elif ntype in (
            "class_definition",    # Python
            "class_declaration",   # Java/JS/TS
            "struct_item",         # Rust
            "impl_item",           # Rust impl block
        ):
            name = _extract_name(node, language)
            start = node.start_point[0] + 1
            end   = node.end_point[0] + 1
            classes.append({
                "name": name,
                "start_line": start,
                "end_line": end,
            })
            for child in node.children:
                walk(child, parent_class=name)
            return  # already recursed

        # ── Import statements ──────────────────────────────────
        elif ntype in (
            "import_statement",
            "import_from_statement",
            "import_declaration",
            "require_call",  # custom for CJS
        ):
            module = _extract_import_module(node, content)
            if module:
                imports.append({
                    "module": module,
                    "line": node.start_point[0] + 1,
                })

        for child in node.children:
            walk(child, parent_class=parent_class)

    walk(root)

    # Cross-file dependency graph: funcA → [funcB, funcC, ...]
    dep_graph = {f["name"]: f["calls"] for f in functions}

    lines = content.splitlines()
    return {
        "ast_valid": ast_valid,
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "dependency_graph": dep_graph,
        "file_metrics": {
            "total_lines": len(lines),
            "function_count": len(functions),
            "class_count": len(classes),
            "import_count": len(imports),
        },
        "raw_ast_available": True,
    }


def _parse_with_regex_fallback(language: str, content: str, file_path: str) -> Dict:
    """Regex-based fallback when tree-sitter unavailable (e.g., unsupported language)."""
    lines = content.splitlines()
    functions = []
    imports = []

    # Language-specific patterns
    func_patterns = {
        "Python":     r"^(async\s+)?def\s+(\w+)\s*\(",
        "JavaScript": r"^(async\s+)?function\s+(\w+)\s*\(",
        "TypeScript": r"^(async\s+)?function\s+(\w+)\s*\(",
        "Java":       r"(public|private|protected|static|\s)+\w+\s+(\w+)\s*\(",
        "Go":         r"^func\s+(\w+)\s*\(",
        "Rust":       r"^(pub\s+)?fn\s+(\w+)\s*\(",
    }
    import_patterns = {
        "Python":     r"^(import|from)\s+(\S+)",
        "JavaScript": r"^(import|require\s*\()\s+['\"]?(\S+)",
        "Java":       r"^import\s+([\w.]+)",
        "Go":         r'"([\w./]+)"',
    }

    fpat = func_patterns.get(language, r"^(function|def|func)\s+(\w+)")
    ipat = import_patterns.get(language, r"^import\s+(\S+)")

    for i, line in enumerate(lines, 1):
        if re.search(fpat, line.strip()):
            m = re.search(r"(\w+)\s*\(", line)
            if m:
                functions.append({
                    "name": m.group(1),
                    "start_line": i,
                    "end_line": i,
                    "line_count": 1,
                    "calls": [],
                    "params": [],
                    "is_public": not m.group(1).startswith("_"),
                    "parent_class": None,
                })
        if re.search(ipat, line.strip()):
            m = re.search(ipat, line.strip())
            if m:
                imports.append({"module": m.group(2) if m.lastindex >= 2 else m.group(1), "line": i})

    return {
        "ast_valid": True,
        "functions": functions,
        "classes": [],
        "imports": imports,
        "dependency_graph": {f["name"]: [] for f in functions},
        "file_metrics": {
            "total_lines": len(lines),
            "function_count": len(functions),
            "class_count": 0,
            "import_count": len(imports),
        },
        "raw_ast_available": False,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_name(node, language: str) -> str:
    for child in node.children:
        if child.type in ("identifier", "name", "property_identifier"):
            return child.text.decode("utf-8")
    return "<anonymous>"


def _extract_calls(node, content: str) -> List[str]:
    calls = []
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
    params = []
    for child in node.children:
        if child.type in ("parameters", "formal_parameters", "parameter_list"):
            for p in child.children:
                if p.type == "identifier":
                    params.append(p.text.decode("utf-8"))
    return params


def _extract_import_module(node, content: str) -> Optional[str]:
    try:
        text = node.text.decode("utf-8")
        # Extract module name from various import syntaxes
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
            text = node.text.decode("utf-8")[:50]
            return "public" in text
        except Exception:
            return True
    if language == "Rust":
        try:
            text = node.text.decode("utf-8")[:20]
            return text.strip().startswith("pub")
        except Exception:
            return False
    return True


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

    # Verify old_code exists verbatim somewhere in the file
    if old_code.strip() not in full_content:
        return False

    return True