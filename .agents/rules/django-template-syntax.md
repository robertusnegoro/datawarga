

## Django Template Syntax Rules

Django's template engine has a strict syntax parser that is **not forgiving of formatting errors**. HTML auto-formatters (such as VS Code's built-in formatter or Prettier) do not understand Django template syntax and will silently break templates by reformatting them. These rules must be followed at all times.

---

### Rule 1: Django Template Tags Must Be on a Single Line

**Every `{% tag %}` must open AND close on the same line.**

The Django template parser does not support multi-line tags. An HTML formatter that word-wraps a tag across lines will cause a `TemplateSyntaxError`.

**❌ BROKEN (formatter wrapped this — will crash)**
```html
<option value="{{ r.0 }}" {% if warga.agama == r.0 %}selected{% endif %}>{{ r.1
    }}</option>
```

```html
{% if not forloop.last
%}, {% endif %}
```

**✅ CORRECT (each tag on a single line)**
```html
<option value="{{ r.0 }}" {% if warga.agama == r.0 %}selected{% endif %}>{{ r.1 }}</option>
```

```html
{% if not forloop.last %}, {% endif %}
```

---

### Rule 2: Django Template Operators Require Spaces

The Django template engine requires **spaces around all comparison operators** (`==`, `!=`, `<`, `>`, etc.). A formatter that removes spaces around `==` will cause a `TemplateSyntaxError`.

**❌ BROKEN**
```html
{% if warga.agama==r.0 %}
```

**✅ CORRECT**
```html
{% if warga.agama == r.0 %}
```

This applies to every field comparison in every `{% if %}` tag:
- `{% if warga.agama == r.0 %}`
- `{% if warga.pekerjaan == p.0 %}`
- `{% if warga.status == s.0 %}`
- `{% if warga.jenis_kelamin == jk.0 %}`
- `{% if warga.status_tinggal == st.0 %}`
- `{% if warga.status_keluarga == sk.0 %}`

---

### Rule 3: `{{ variable }}` Expressions Must Be on a Single Line

Django template variable expressions (`{{ ... }}`) must also not be split across lines by a formatter.

**❌ BROKEN**
```html
<strong>{{
    warga.no_hp|default:"-" }}</strong>
```

**✅ CORRECT**
```html
<strong>{{ warga.no_hp|default:"-" }}</strong>
```

---

### Rule 4: Disable HTML Format-on-Save for Django Templates

The project `.vscode/settings.json` **must** contain:

```json
{
  "[html]": {
    "editor.formatOnSave": false,
    "editor.defaultFormatter": null
  }
}
```

This prevents VS Code's HTML formatter from breaking Django template syntax on every save.

**When generating or editing Django templates:**
1. Never let a `{% tag %}` span more than one line.
2. Never write `variable==value` — always write `variable == value`.
3. Never let a `{{ variable }}` span more than one line.
4. After every edit, scan the file with: `grep -n "==[a-z]" <template_file>` to detect missing spaces.

---

### Rule 5: Preferred Pattern for Inline Conditional Separators

When you need to output a separator (e.g., a comma) between loop items, use a full `{% if %}...{% else %}...{% endif %}` pattern rather than a trailing `{% if %}` appended to an expression line. The latter is fragile to formatters.

**❌ Fragile (formatter can break the trailing {% if %})**
```html
{% for key, val in items.items %}
{{ key }}: {{ val }}{% if not forloop.last %}, {% endif %}
{% endfor %}
```

**✅ Robust ({% if %} is the first thing on the line)**
```html
{% for key, val in items.items %}
{% if not forloop.last %}{{ key }}: {{ val }}, {% else %}{{ key }}: {{ val }}{% endif %}
{% endfor %}
```
