"""A small two-app codebase (Next.js shop + Flask API + Express server + WordPress plugin) for the
Codebase Map checks: every kind of endpoint, request and mount the scanner should understand."""
from __future__ import annotations

import subprocess
from pathlib import Path

FILES = {
    "web/src/lib/api.ts": """/** Typed client for every backend call. */
const BASE = process.env.NEXT_PUBLIC_API;
export async function listOrders() { return fetch(`${BASE}/api/orders`) }
export async function createOrder(o) { return fetch('/api/orders', { method: 'POST', body: JSON.stringify(o) }) }
export async function getOrder(id) { return axios.get(`/api/orders/${id}`) }
export async function pay() { return fetch('https://api.stripe.com/v1/charges', {method: 'POST'}) }
export async function profile(id) { return fetch(`/v2/users/${id}`) }
""",
    "web/src/app/orders/page.tsx": """import { listOrders } from '../../lib/api'
export default function OrdersPage() { return null }
""",
    "web/src/app/[shop]/page.tsx": """import { getOrder } from '../../lib/api'
export default function ShopPage() { return null }
""",
    "web/src/app/api/items/route.ts": """export async function GET() {}
export async function POST() {}
""",
    "web/src/components/Unused.tsx": "export function Unused() { return null }\n",
    "api/app/__init__.py": '''"""Flask app factory."""
from flask import Flask
from app.routes.orders import bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp, url_prefix="/api")
    return app
''',
    "api/app/routes/orders.py": '''"""Order endpoints."""
from flask import Blueprint
import stripe

bp = Blueprint("orders", __name__)


@bp.route("/orders", methods=["GET", "POST"])
def orders():
    """List or create orders."""


@bp.get("/orders/<int:order_id>")
def one(order_id):
    return stripe.Charge.retrieve(order_id)
''',
    "api/app/settings.py": 'STRIPE_KEY = "sk_live_' + "4" * 24 + '"\n',
    "server/index.js": """const express = require('express')
const users = require('./routes/users')
const app = express()
app.use('/v2/users', auth, users)
app.listen(3000)
""",
    "server/routes/users.js": """const router = require('express').Router()
router.get('/:id', show)
router.post('/', create)
module.exports = router
""",
    "plugin/bakery.php": """<?php
/**
 * Plugin Name: Bakery Orders
 */
add_action('rest_api_init', function () {
    register_rest_route('bakery/v1', '/cakes/(?P<id>\\d+)', ['methods' => WP_REST_Server::READABLE, 'callback' => 'bakery_cake']);
});
add_action('wp_ajax_bakery_save', 'bakery_save');
function bakery_cake($req) { return wp_remote_get('https://api.sendgrid.com/v3/mail'); }
""",
    "plugin/js/admin.js": """jQuery.post(ajaxurl, { action: 'bakery_save', id: 1 });
""",
    "web/package.json": '{"name": "shop", "dependencies": {"next": "14.2.0"}}\n',
    "README.md": "# Bakery\n",
}


def write_sample(root: Path) -> Path:
    for rel, text in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root
