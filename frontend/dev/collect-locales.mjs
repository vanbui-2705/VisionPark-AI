import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
const values = new Set()
const apply = process.argv.includes('--apply')
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name)
    if (entry.isDirectory()) walk(file)
    else if (file.endsWith('.tsx')) {
      const source = fs.readFileSync(file, 'utf8')
      const tree = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
      const edits = []
      let needsImport = false
      const insideFunction = node => { for (let p = node.parent; p; p = p.parent) if (ts.isFunctionLike(p)) return true; return false }
      const visit = node => {
        if ((ts.isStringLiteral(node) || ts.isJsxText(node)) && /[\u00c0-\u1ef9]/.test(node.text)) {
          const text = node.text.replace(/\s+/g, ' ').trim().replace(/&quot;/g, '"').replace(/&amp;/g, '&')
          values.add(text)
          if (apply && insideFunction(node) && !(ts.isCallExpression(node.parent) && node.parent.expression.getText(tree) === 't')) {
            const expression = `t(${JSON.stringify(text)})`
            const replacement = ts.isJsxText(node) || ts.isJsxAttribute(node.parent) ? `{${expression}}` : expression
            edits.push({ start: ts.isJsxText(node) ? node.pos : node.getStart(tree), end: node.end, replacement })
            needsImport = true
          }
        }
        if (apply && ts.isJsxExpression(node) && node.expression && !ts.isJsxAttribute(node.parent)) {
          const e = node.expression
          if ((ts.isPropertyAccessExpression(e) && ['label', 'title'].includes(e.name.text)) || (ts.isElementAccessExpression(e) && e.expression.getText(tree).endsWith('_LABEL'))) {
            edits.push({ start: e.getStart(tree), end: e.end, replacement: `t(${e.getText(tree)})` }); needsImport = true
          }
        }
        ts.forEachChild(node, visit)
      }
      visit(tree)
      if (apply && edits.length) {
        let updated = source
        for (const edit of edits.sort((a,b) => b.start - a.start)) updated = updated.slice(0, edit.start) + edit.replacement + updated.slice(edit.end)
        if (needsImport) {
          let relative = path.relative(path.dirname(file), 'src/lib/i18n').replaceAll('\\', '/')
          if (!relative.startsWith('.')) relative = './' + relative
          updated = `import { t } from ${JSON.stringify(relative)}\n` + updated
        }
        fs.writeFileSync(file, updated)
      }
    }
  }
}
walk('src')
fs.writeFileSync('../backend/var/locale-catalog.json', JSON.stringify([...values].sort(), null, 2))
console.log(values.size)
