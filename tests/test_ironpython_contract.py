from __future__ import absolute_import

import ast
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "RevitEstimating.extension", "lib", "revit_estimating")
EXTENSION = os.path.join(ROOT, "RevitEstimating.extension")

BANNED_IMPORT_ROOTS = set(("pathlib", "dataclasses", "typing", "enum", "statistics"))
BANNED_NAMES = set(("FileNotFoundError", "PermissionError", "TimeoutError"))
BANNED_ATTRIBUTE_CALLS = set((
    ("os", "replace"),
    ("os", "scandir"),
    ("subprocess", "run"),
    ("shutil", "which"),
    ("json", "JSONDecodeError"),
))


def runtime_python_files():
    paths = []
    for base in (LIB, EXTENSION):
        for dirpath, _, filenames in os.walk(base):
            for filename in filenames:
                if filename.endswith(".py"):
                    paths.append(os.path.join(dirpath, filename))
    return sorted(paths)


class CompatibilityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.issues = []

    def issue(self, node, message):
        self.issues.append((getattr(node, "lineno", 0), message))

    def visit_JoinedStr(self, node):
        self.issue(node, "f-string syntax is not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.issue(node, "async def is not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_Await(self, node):
        self.issue(node, "await is not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_YieldFrom(self, node):
        self.issue(node, "yield from is not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_Nonlocal(self, node):
        self.issue(node, "nonlocal is not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self.issue(node, "variable annotations are not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_NamedExpr(self, node):
        self.issue(node, "assignment expressions are not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        annotations = [arg.annotation for arg in list(getattr(node.args, "posonlyargs", [])) + list(node.args.args) + list(node.args.kwonlyargs)]
        for arg in (node.args.vararg, node.args.kwarg):
            if arg is not None:
                annotations.append(getattr(arg, "annotation", None))
        if node.returns is not None or any(item is not None for item in annotations):
            self.issue(node, "function annotations are not IronPython 2.7 compatible")
        if node.args.kwonlyargs:
            self.issue(node, "keyword-only arguments are not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_Raise(self, node):
        if getattr(node, "cause", None) is not None:
            self.issue(node, "raise-from syntax is not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_Dict(self, node):
        if any(key is None for key in node.keys):
            self.issue(node, "dictionary unpacking is not IronPython 2.7 compatible")
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.split(".")[0] in BANNED_IMPORT_ROOTS:
                self.issue(node, "Python-3-only/unbundled stdlib import: %s" % alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        root = (node.module or "").split(".")[0]
        if root in BANNED_IMPORT_ROOTS:
            self.issue(node, "Python-3-only/unbundled stdlib import: %s" % node.module)
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in BANNED_NAMES:
            self.issue(node, "Python-3-only exception name: %s" % node.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            if any(keyword.arg == "encoding" for keyword in node.keywords):
                self.issue(node, "builtin open(..., encoding=...) is not Python 2.7 compatible; use io.open")
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            pair = (node.func.value.id, node.func.attr)
            if pair in BANNED_ATTRIBUTE_CALLS:
                self.issue(node, "Python-3-only runtime call: %s.%s" % pair)
        self.generic_visit(node)


class IronPythonCompatibilityContractTests(unittest.TestCase):
    def test_runtime_sources_avoid_obvious_python3_only_constructs(self):
        files = runtime_python_files()
        self.assertTrue(files)
        failures = []
        for path in files:
            with open(path, "r") as stream:
                source = stream.read()
            tree = ast.parse(source, filename=path)
            visitor = CompatibilityVisitor()
            visitor.visit(tree)
            for line, message in visitor.issues:
                failures.append("%s:%s: %s" % (os.path.relpath(path, ROOT), line, message))
            if re.search(r"\b\d[\d_]*_\d[\d_]*\b", source):
                failures.append("%s: numeric literal separators are not IronPython 2.7 compatible" % os.path.relpath(path, ROOT))
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
