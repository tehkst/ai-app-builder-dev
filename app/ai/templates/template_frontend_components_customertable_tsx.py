from __future__ import annotations


TEMPLATE_PATH = 'frontend/components/CustomerTable.tsx'
TEMPLATE_CONTENT = 'type Customer = {\n  id: number;\n  name: string;\n  email?: string | null;\n  phone?: string | null;\n  company?: string | null;\n};\n\ntype CustomerTableProps = {\n  customers: Customer[];\n};\n\nexport default function CustomerTable({ customers }: CustomerTableProps) {\n  return (\n    <table>\n      <thead>\n        <tr>\n          <th>Name</th>\n          <th>Email</th>\n          <th>Phone</th>\n          <th>Company</th>\n        </tr>\n      </thead>\n\n      <tbody>\n        {customers.map((customer) => (\n          <tr key={customer.id}>\n            <td>{customer.name}</td>\n            <td>{customer.email || "-"}</td>\n            <td>{customer.phone || "-"}</td>\n            <td>{customer.company || "-"}</td>\n          </tr>\n        ))}\n      </tbody>\n    </table>\n  );\n}\n'
