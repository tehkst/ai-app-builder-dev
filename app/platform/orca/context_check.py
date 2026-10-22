"""Check for step 5d, graph-based context: outlines per language, the code connected to a task (its
files, what they use, what uses them) in every briefing without file contents, the size cap, the
architect's code map, and the content-hash cache (unchanged files are never re-parsed; the map is
rebuilt only when a file changes or appears)."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from app.platform.impact_map.check import write_project
from app.platform.orca import context
from app.platform.orca.handoffs import build_assignment, plan_assignment, review_assignment
from app.platform.orca.models import Mission, Task


def check_outlines() -> None:
    php = "<?php\nnamespace Shop;\nclass Cart {\n  public function add($x) {}\n  private static function total() {}\n}\nfunction helper() {}\n"
    assert context.outline(php) == "Cart, add, total, helper", context.outline(php)
    js = "export default function App() {}\nexport const api = 1;\nclass Store {}\nasync function load() {}\n"
    assert context.outline(js) == "App, api, Store, load", context.outline(js)
    py = "class Order:\n    def total(self):\n        pass\n\nasync def fetch():\n    pass\n"
    assert context.outline(py) == "Order, total, fetch", context.outline(py)
    many = "\n".join(f"def f{i}():\n    pass" for i in range(20))
    assert context.outline(many).endswith("(+8 more)") and context.outline("x = 1") == "(no named definitions)"


def check_task_context(root: Path) -> None:
    block = context.task_context(str(root), ["inc/pricing.php"])
    assert block.startswith("## Code connected to this task"), block
    assert "- `inc/pricing.php`: Pricing, total, rates, member_discount" in block, block
    used_by = block.split("Used by", 1)[1]
    for path in ("functions.php", "inc/cart.php", "tests/PricingTest.php"):
        assert f"`{path}`" in used_by, (path, block)
    assert "round($sum * 0.9)" not in block and "array_sum" not in block, "outlines only, never contents"
    ts = context.task_context(str(root), ["./src/components/Cart.tsx"])
    assert "`src/lib/api.ts`: getCart" in ts.split("They use", 1)[1] and "`src/main.ts`" in ts.split("Used by", 1)[1], ts
    assert context.task_context(str(root), []) == "" and context.task_context(str(root), ["missing.php"]) == ""

    plan = context.plan_context(str(root))
    assert plan.startswith("## Code map") and "Entry points:" in plan and "`inc/pricing.php`" in plan, plan

    mission = Mission("ORCA-CONTEXT00001", "Fix pricing", str(root), plan_summary="s")
    task = Task("T1", "Fix discount", "d", ["inc/pricing.php"], ["grep -q x inc/pricing.php"])
    assert "## Code connected to this task" in build_assignment(mission, task)
    assert "## Code map" in plan_assignment(mission)
    review = review_assignment(mission, task, {"summary": "s", "files_changed": ["inc/cart.php"]}, [], False)
    assert "- `inc/cart.php`" in review and "page-checkout.php" in review, "QA sees what uses the changed file"


def check_cap(base: Path) -> None:
    root = base / "wide"
    (root / "lib").mkdir(parents=True)
    (root / "lib" / "core.js").write_text("export function core() {}\n")
    for i in range(60):
        (root / f"page{i}.js").write_text(f"import {{ core }} from './lib/core.js';\nexport function page{i}LongName{'X' * 80}() {{}}\n")
    block = context.task_context(str(root), ["lib/core.js"])
    assert len(block) < context.MAX_CONTEXT_CHARS + 800, len(block)
    assert block.count("`page") <= context.MAX_NEIGHBOURS, "at most MAX_NEIGHBOURS per list"


def check_cache(base: Path) -> None:
    root = base / "cached"
    write_project(root)
    context.task_context(str(root), ["inc/pricing.php"])
    builds, misses = context.STATS["map_builds"], context.STATS["outline_misses"]
    context.task_context(str(root), ["inc/pricing.php"])
    assert context.STATS["map_builds"] == builds, "unchanged workspace: the map is reused"
    assert context.STATS["outline_misses"] == misses, "unchanged files: outlines come from the content-hash cache"

    time.sleep(0.01)
    target = root / "inc" / "pricing.php"
    target.write_text(target.read_text() + "function loyalty_points() {}\n")
    os.utime(target, None)
    block = context.task_context(str(root), ["inc/pricing.php"])
    assert context.STATS["map_builds"] == builds + 1 and "loyalty_points" in block, "a changed file rebuilds the map"
    assert context.STATS["outline_misses"] == misses + 1, "only the changed file is re-parsed"

    (root / "inc" / "extra.php").write_text("<?php\nfunction extra() { return member_discount(1, true); }\n")
    block = context.task_context(str(root), ["inc/pricing.php"])
    assert context.STATS["map_builds"] == builds + 2 and "`inc/extra.php`" in block, "a new file is picked up"


def check_review_fixes(base: Path) -> None:
    # Files build_map leaves out (generated, minified) never force a rebuild.
    root = base / "excluded"
    write_project(root)
    (root / "generated").mkdir()
    (root / "generated" / "client.ts").write_text("export const x = 1;\n")
    (root / "src" / "bundle.min.js").write_text("var a=1;\n")
    context.task_context(str(root), ["inc/pricing.php"])
    builds = context.STATS["map_builds"]
    context.task_context(str(root), ["inc/pricing.php"])
    assert context.STATS["map_builds"] == builds, "excluded files must not trigger a rebuild every briefing"

    # A deleted file keeps its former dependants in the context (they are what may break).
    (root / "inc" / "cart.php").unlink()
    block = context.task_context(str(root), ["inc/cart.php"])
    assert "`inc/cart.php` (deleted)" in block and "`page-checkout.php`" in block.split("Used by", 1)[1], block

    # Caches are bounded (LRU): old workspaces drop out.
    for i in range(context.MAX_MAPS + 3):
        small = base / f"ws{i}"
        small.mkdir()
        (small / "a.py").write_text("import b\n")
        (small / "b.py").write_text("def f():\n    pass\n")
        context.task_context(str(small), ["a.py"])
    assert len(context._MAPS) == context.MAX_MAPS and str(base / "ws0") not in context._MAPS
    assert len(context._OUTLINES) <= context.MAX_OUTLINES


def main() -> None:
    check_outlines()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        root = base / "bakery"
        write_project(root)
        check_task_context(root)
        check_cap(base)
        check_cache(base)
        check_review_fixes(base)
    print("ORCA CONTEXT CHECK PASSED")


if __name__ == "__main__":
    main()
