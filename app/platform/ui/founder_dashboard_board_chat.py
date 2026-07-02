from __future__ import annotations

from app.platform.ui.founder_dashboard_stable import render_stable_founder_dashboard


def render_board_chat_dashboard() -> str:
    html = render_stable_founder_dashboard()
    html = html.replace("<h2>Board Room Discussion</h2>", "<h2>Board Room Executive Chat</h2>")
    html = html.replace("<textarea id='message' placeholder='Tell the Board Room what you want to discuss.'></textarea>", "<div class='board-chat-note'>Chat-style Board Room workspace. Minutes panel will capture decisions, actions, and knowledge notes.</div><textarea id='message' placeholder='Message the Board Room...' rows='3'></textarea>")
    html = html.replace("Start Board Room Discussion", "Send")
    html = html.replace("<h3>Board Room Response</h3><pre id='result'>Type a message and start the discussion.</pre>", "<div class='board-chat-grid'><section><h3>Chat</h3><pre id='result'>Start a new Board Room chat.</pre></section><aside class='board-minutes'><h3>Minutes</h3><p><strong>Decisions</strong></p><ul><li>No decisions captured yet.</li></ul><p><strong>Actions</strong></p><ul><li>No actions captured yet.</li></ul><p><strong>Knowledge</strong></p><ul><li>Important context will appear here.</li></ul></aside></div>")
    html = html.replace("</style>", ".board-chat-note{border:1px solid var(--line);background:#07101e;border-radius:12px;padding:12px;margin-bottom:12px;color:var(--muted)}.board-chat-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:14px}.board-minutes{border:1px solid var(--line);border-radius:12px;padding:14px;background:#07101e}.board-minutes ul{padding-left:18px;color:#dbeafe}@media(max-width:900px){.board-chat-grid{grid-template-columns:1fr}}\n</style>")
    return html
