# AI Context — Bootstrap cho Agent

Agent mới đọc theo thứ tự:
1. `OVERVIEW.md`
2. `AI_CONTEXT.md` (file này)
3. `ARCHITECTURE.md`
4. `DECISIONS.md`

Quy tắc:
- Không quét toàn repo trước khi đọc 4 file trên.
- `can(user, perm)` là nguồn duy nhất cho phân quyền.
- Không hard-code role/token/URL.
- Không fake số liệu production.
- Docs update sau thay đổi đáng kể (routes, permissions, API contract).
