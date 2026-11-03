"""What a Codebase Cartographer might return for sample.py's codebase (used by the checks)."""
ARCHITECTURE = {
    "project": {"name": "Bakery", "summary": "An online bakery: customers order cakes on the website, staff manage "
                                               "orders, and a WordPress plugin shows cakes on the shop's blog."},
    "nodes": [
        {"id": "web", "label": "Online shop", "kind": "ui", "summary": "The website customers use to order cakes.",
         "paths": ["web"]},
        {"id": "web.pages", "parent": "web", "label": "Pages", "kind": "feature", "summary": "The shop's pages.",
         "paths": ["web/src/app/**/page.tsx"]},
        {"id": "web.client", "parent": "web", "label": "Talks to the server", "kind": "library",
         "summary": "Every request the shop sends to the servers.", "paths": ["web/src/lib"]},
        {"id": "api", "label": "Main server", "kind": "service", "summary": "Takes orders and payments.", "paths": ["api"]},
        {"id": "accounts", "label": "Accounts server", "kind": "service", "summary": "Customer profiles.", "paths": ["server/**"]},
        {"id": "plugin", "label": "Blog plugin", "kind": "feature", "summary": "Shows cakes on the shop's WordPress blog.",
         "paths": ["plugin"]},
        {"id": "stripe", "label": "Stripe", "kind": "external", "summary": "Takes card payments.",
         "packages": ["pypi:stripe"], "hosts": ["api.stripe.com"]},
        {"id": "sendgrid", "label": "SendGrid", "kind": "external", "summary": "Sends emails.", "hosts": ["*.sendgrid.com"]},
    ],
    "edges": [{"from": "stripe", "to": "api/app/routes/orders.py", "kind": "http", "label": "webhooks",
               "description": "Stripe tells the server when a payment went through."}],
    "flows": [{"id": "order", "title": "Ordering a cake", "steps": [
        {"node": "web/src/app/orders/page.tsx", "note": "The customer opens their orders."},
        {"node": "web/src/lib/api.ts", "note": "The shop asks the server for them."},
        {"node": "api/app/routes/orders.py", "note": "The server looks them up."},
        {"node": "stripe", "note": "Payments go through Stripe."}]}],
    "tour": [{"node": "web", "title": "The shop", "note": "Where customers order."},
             {"node": "api", "title": "The main server", "note": "Where orders are kept."}],
}
