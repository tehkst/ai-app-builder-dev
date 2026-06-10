from __future__ import annotations


TEMPLATE_PATH = 'frontend/app/dashboard/page.tsx'
TEMPLATE_CONTENT = '"use client";\n\nimport { useEffect, useState } from "react";\nimport { getCurrentUser } from "../../lib/api";\nimport { SAFE_ERROR_MESSAGES } from "../../lib/errors";\n\nexport default function DashboardPage() {\n  const [userId, setUserId] = useState("");\n  const [errorMessage, setErrorMessage] = useState("");\n\n  useEffect(() => {\n    async function loadDashboard() {\n      setErrorMessage("");\n\n      try {\n        const user = await getCurrentUser();\n        setUserId(user.user_id);\n      } catch {\n        setErrorMessage(SAFE_ERROR_MESSAGES.unauthorized);\n      }\n    }\n\n    loadDashboard();\n  }, []);\n\n  return (\n    <main>\n      <h1>Dashboard</h1>\n\n      {errorMessage ? (\n        <p>{errorMessage}</p>\n      ) : (\n        <p>Current user ID: {userId || "Loading..."}</p>\n      )}\n    </main>\n  );\n}\n'
