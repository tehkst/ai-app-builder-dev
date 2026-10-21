"""Check for the impact map (step 4d): the PHP/JS/Python scanners, the dependency graph and its
answers to "what breaks if we change this?", the Health Check report section and the founder-only
Clients lookup. Synthetic projects only; nothing is run."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.platform.auth.service import _sign_claims
from app.platform.codebase_health.report import render_markdown
from app.platform.codebase_health.service import run_health_check
from app.platform.impact_map import build_map, impact, package_reach, summary
from app.platform.impact_map.parsers import parse_js, parse_php, parse_python, strip_comments

FILES = {
    "composer.json": json.dumps({"require": {"guzzlehttp/guzzle": "^7.0", "php": ">=8.1"}}),
    "functions.php": "<?php\n// require 'fake.php';\n/* include 'also-fake.php'; */\nrequire_once __DIR__ . '/inc/cart.php';\n"
                     "require get_template_directory() . '/inc/pricing.php';\ninclude $dynamic;\n"
                     "add_action('init', 'bakery_register');\nfunction bakery_register() { register_post_type('cake', []); }\n",
    "inc/pricing.php": "<?php\nnamespace Bakery;\nuse GuzzleHttp\\Client;\nclass Pricing {\n"
                       "  public function total(array $items, bool $member): int { return member_discount(array_sum($items), $member); }\n"
                       "  public function rates() { return (new Client())->get('https://rates.test'); }\n}\n"
                       "function member_discount(int $sum, bool $member): int { return $member ? (int) round($sum * 0.9) : $sum; }\n",
    "inc/cart.php": "<?php\nuse Bakery\\Pricing;\nfunction bakery_cart_total($items) { $p = new Pricing(); "
                    "return apply_filters('bakery_cart_total', $p->total($items, is_user_logged_in())); }\n",
    "inc/promo.php": "<?php\nadd_filter('bakery_cart_total', function ($t) { return $t - 100; });\n",
    "page-checkout.php": "<?php get_header(); echo bakery_cart_total([500, 700]); get_template_part('template-parts/summary', 'order');\n",
    "template-parts/summary-order.php": "<p><?php echo esc_html(bakery_cart_total([1])); ?></p>\n",
    "tests/PricingTest.php": "<?php\nuse Bakery\\Pricing;\nclass PricingTest extends \\PHPUnit\\Framework\\TestCase {\n"
                             "  function test_total() { $this->assertSame(900, (new Pricing())->total([1000], true)); }\n}\n",
    "package.json": json.dumps({"name": "bakery-js", "dependencies": {"axios": "^1.0.0"}}),
    "tsconfig.json": '{ // comment\n "compilerOptions": { "baseUrl": ".", "paths": { "~lib/*": ["src/lib/*"] } } }',
    "src/lib/api.ts": "import axios from 'axios';\nimport fs from 'fs';\nexport const getCart = () => axios.get('/cart');\n",
    "src/components/Cart.tsx": "import { getCart } from '~lib/api';\n// import Old from './Old';\nexport function Cart() { return getCart(); }\n",
    "src/components/Badge.vue": "<template><b/></template>\n<script setup lang=\"ts\">\nimport { Cart } from './Cart'\n</script>\n",
    "src/main.ts": "import { Cart } from './components/Cart';\nexport * from './lib/api';\nconst m = await import(name);\nCart();\n",
    "src/components/Cart.test.tsx": "import { Cart } from './Cart';\ntest('cart', () => Cart());\n",
    "shop/__init__.py": "",
    "shop/models.py": "import os\nimport requests\nclass Order: ...\n",
    "shop/views.py": "from .models import Order\nfrom . import models\nimport json\n",
    "manage.py": "from shop import views\n",
}


def write_project(root: Path) -> None:
    for rel, content in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def check_parsers() -> None:
    code = strip_comments("a = '// not a comment'; // gone\n/* gone\n */ b = \"/* kept */\"; # php", hash_comments=True)
    assert "'// not a comment'" in code and "gone" not in code and '"/* kept */"' in code and "php" not in code
    assert code.count("\n") == 2, "line numbers are kept"
    php = parse_php("<?php\nnamespace App\\Http;\nuse App\\Models\\{User, Order as O};\nuse Foo\\Bar;\n"
                    "class Home extends Base implements A, B {\n  public function index() { helper(); return O::find(1); }\n"
                    "  private static function x() {}\n}\nfunction helper() { return new \\Lib\\Util(); }\n"
                    "if ($x) { require_once dirname(__FILE__) . '/../config.php'; }\nrequire $path;\n"
                    "do_action('app_boot');\nadd_filter(\"the_title\", 'f');\n")
    assert php.namespace == "App\\Http" and php.classes == ["App\\Http\\Home"], (php.namespace, php.classes)
    assert ("User", "App\\Models\\User") in php.uses and ("O", "App\\Models\\Order") in php.uses and ("Bar", "Foo\\Bar") in php.uses
    assert php.functions == ["helper"], f"methods are not global functions: {php.functions}"
    assert {"Base", "A", "B", "O", "Lib\\Util"} <= php.class_refs, php.class_refs
    assert php.includes == ["/../config.php"] and php.unresolved == 1, (php.includes, php.unresolved)
    assert php.hooks_fired == {"app_boot"} and php.hooks_added == {"the_title"}
    js = parse_js("import a from './a';\nimport {b} from \"../b\";\nimport './side.css';\nexport { c } from './c';\n"
                  "const d = require('d-pkg');\nconst e = await import('./e');\nimport type { T } from './types';\n"
                  "// import z from './z';\nrequire(variable);\n")
    assert js.imports == ["./a", "../b", "./side.css", "./c", "d-pkg", "./e", "./types"], js.imports
    assert js.unresolved == 1
    vue = parse_js("<template><div/></template><script>import X from './X.vue'</script>", "Vue")
    assert vue.imports == ["./X.vue"]
    py = parse_python("import os, sys as s\nfrom ..core import util\nfrom . import views\n# import nope\n"
                      "from .api import (\n    client as c,\n    errors,\n)\n")
    assert set(py.imports) == {"os", "sys", "..core", "..core.util", ".", ".views", ".api", ".api.client", ".api.errors"}, py.imports
    quoted = parse_python('"""Usage:\n\nimport secret_tool\nfrom fake import thing\n"""\nx = "import also_fake"\nimport real\n')
    assert quoted.imports == ["real"], f"imports inside strings must not count: {quoted.imports}"
    legacy = parse_python('print "python 2"\n"""\nimport quoted\n"""\nimport urllib2\n')  # not valid Python 3
    assert legacy.imports == ["urllib2"], legacy.imports


def check_graph(root: Path) -> None:
    m = build_map(str(root))
    expect = {
        "functions.php": {"inc/cart.php", "inc/pricing.php"},
        "inc/cart.php": {"inc/pricing.php", "inc/promo.php"},  # class + the bakery_cart_total filter's handler
        "page-checkout.php": {"inc/cart.php", "template-parts/summary-order.php"},
        "template-parts/summary-order.php": {"inc/cart.php"},
        "tests/PricingTest.php": {"inc/pricing.php"},
        "src/components/Cart.tsx": {"src/lib/api.ts"},
        "src/components/Badge.vue": {"src/components/Cart.tsx"},
        "src/main.ts": {"src/components/Cart.tsx", "src/lib/api.ts"},
        "src/components/Cart.test.tsx": {"src/components/Cart.tsx"},
        "shop/views.py": {"shop/models.py", "shop/__init__.py"},
        "manage.py": {"shop/views.py", "shop/__init__.py"},
    }
    for user, used in expect.items():
        assert m.uses.get(user, set()) >= used, (user, m.uses.get(user))
    assert "fake.php" not in str(m.uses) and "also-fake" not in str(m.uses), "commented-out includes ignored"
    assert {k: sorted(v) for k, v in m.packages.items()} == {
        "axios": ["src/lib/api.ts"], "guzzlehttp/guzzle": ["inc/pricing.php"], "requests": ["shop/models.py"]}, m.packages
    assert m.unresolved == 2, m.unresolved  # include $dynamic; import(name)
    assert m.kinds[("inc/cart.php", "inc/promo.php")] == {"hook:bakery_cart_total"}

    pricing = impact(m, "inc/pricing.php")
    assert pricing["kind"] == "file" and pricing["found"]
    assert {u["path"] for u in pricing["used_directly_by"]} == {"functions.php", "inc/cart.php", "tests/PricingTest.php"}
    assert {"page-checkout.php", "template-parts/summary-order.php"} <= {a["path"] for a in pricing["affected"]}
    assert "page-checkout.php" in pricing["entry_points"] and pricing["tests"] == ["tests/PricingTest.php"]
    assert pricing["level"] == "moderate" and not pricing["untested"]
    for target, kind in (("member_discount", "function"), ("Bakery\\Pricing", "class"), ("Pricing", "class"),
                         ("bakery_cart_total", "function"), ("axios", "package"), ("pricing.php", "file")):
        result = impact(m, target)
        assert result["kind"] == kind and result["found"], (target, result)
    promo = impact(m, "inc/promo.php")
    assert "page-checkout.php" in promo["entry_points"] and promo["untested"] and "No automated test" in promo["advice"]
    assert impact(m, "Nope\\Missing")["found"] is False
    hook = impact(m, "bakery_cart_total")
    assert hook["kind"] == "function" and hook["defined_in"] == ["inc/cart.php"]

    info = summary(m)
    assert info["hotspots"][0]["path"] == "inc/pricing.php" and info["links"] == m.link_count, info["hotspots"][:2]
    assert package_reach(m, ["GuzzleHttp/Guzzle", "left-pad"]) == [
        {"package": "GuzzleHttp/Guzzle", "files": ["inc/pricing.php"], "count": 1}]


def check_edge_cases(base: Path) -> None:
    root = base / "edge"
    files = {f"chain/l{i}.php": f"<?php require __DIR__ . '/l{i + 1}.php';\n" for i in range(9)}
    files["chain/l9.php"] = "<?php\nfunction deepest() {}\n"
    files.update({
        "composer.json": json.dumps({"require": {"symfony/console": "^6", "symfony/http-foundation": "^6", "monolog/monolog": "^3"}}),
        "src/App/User.php": "<?php\nnamespace App;\nclass User {}\n",
        "src/Domain/User.php": "<?php\nnamespace Domain;\nclass User {}\n",
        "src/web.php": "<?php\nuse Symfony\\Component\\HttpFoundation\\Request;\nuse Symfony\\Component\\Yaml\\Yaml;\n"
                       "use Monolog\\Logger;\n$r = Request::createFromGlobals(); $y = Yaml::parse('a'); $l = new Logger('x');\n",
    })
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content)
    m = build_map(str(root))
    deep = impact(m, "chain/l9.php")
    assert deep["affected_count"] == 9 and "chain/l0.php" in deep["entry_points"], "no depth cut-off: everything downstream"
    ambiguous = impact(m, "User")
    assert ambiguous["kind"] == "ambiguous" and not ambiguous["found"] and ambiguous["candidates"] == ["App\\User", "Domain\\User"]
    assert impact(m, "Domain\\User")["kind"] == "class" and impact(m, "Domain\\User")["defined_in"] == ["src/Domain/User.php"]
    assert {k: sorted(v) for k, v in m.packages.items()} == {
        "symfony/http-foundation": ["src/web.php"], "monolog/monolog": ["src/web.php"]}, \
        f"a vendor's namespace goes to the package it names, or stays unresolved: {m.packages}"


def check_report(root: Path) -> None:
    result = run_health_check(str(root), online_lookups=False)
    assert result["impact"]["hotspots"] and result["impact"]["links"] > 10, result["impact"]
    markdown = render_markdown(result)
    assert "## Impact map: where changes ripple" in markdown and "`inc/pricing.php`" in markdown
    result["impact"]["vulnerable_packages"] = [{"package": "axios", "files": ["src/lib/api.ts"], "count": 1}]
    assert "| axios | 1 file: src/lib/api.ts |" in render_markdown(result)
    from app.platform.codebase_health.report import render_pdf

    with tempfile.TemporaryDirectory() as out:
        pdf = render_pdf(result, str(Path(out) / "r.pdf"))
        assert Path(pdf).read_bytes().startswith(b"%PDF")


def check_api(root: Path, base: Path) -> None:
    from app.platform.clients import service
    from app.platform.server import app

    os.environ["ASF_CLIENT_WORKSPACES"] = str(base / "workspaces")
    service.HEALTH_CHECK_ONLINE = False
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    http = TestClient(app)

    def post(path: str, **body):
        return http.post(f"/mission-control/clients/{path}", json={"token": token, **body}).json()

    client_id = post("create", name="Bakery")["client"]["client_id"]
    codebase_id = post("add-codebase", client_id=client_id, source=str(root))["codebase"]["codebase_id"]
    assert http.post("/mission-control/clients/impact", json={"codebase_id": codebase_id, "target": "x"}).json()["status"] == "unauthorized"
    found = post("impact", codebase_id=codebase_id, target="Bakery\\Pricing")
    assert found["status"] == "ready" and found["impact"]["kind"] == "class" and found["impact"]["affected_count"] >= 4, found
    assert post("impact", codebase_id=codebase_id, target="")["status"] == "invalid-request"
    assert post("impact", codebase_id="CB-nope", target="x")["status"] == "invalid-request"
    post("run-check", codebase_id=codebase_id)
    service._RUNNING[codebase_id].join(timeout=120)
    stored = post("detail", client_id=client_id)["client"]["codebases"][0]["last_check"]["impact"]
    assert stored["hotspots"] and stored["links"] > 10, stored


def main() -> None:
    check_parsers()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        root = base / "bakery"
        write_project(root)
        check_graph(root)
        check_edge_cases(base)
        check_report(root)
        check_api(root, base)
    print("IMPACT MAP CHECK PASSED")


if __name__ == "__main__":
    main()
