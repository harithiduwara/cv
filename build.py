#!/usr/bin/env python3
"""
Generate index.html from cv.tex.

cv.tex is the single source of truth for CV *content* (name, contact links,
experience, skills, education, projects, achievements). Presentational chrome
(the hero headline, the Role/Company/Location card, theme toggle, etc.) lives
in index.template.html. Edit cv.tex, then this script regenerates index.html.
Run in CI before compiling the PDF and deploying.
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).parent
TEX = (ROOT / "cv.tex").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "index.template.html").read_text(encoding="utf-8")

SVG = {
    "linkedin": '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 1.12 1 2.5 1s2.48 1.12 2.48 2.5zM.5 8h4V24h-4V8zm7.5 0h3.8v2.2h.05c.53-1 1.83-2.2 3.77-2.2 4.03 0 4.78 2.65 4.78 6.1V24h-4v-7.1c0-1.7-.03-3.9-2.38-3.9-2.38 0-2.75 1.86-2.75 3.78V24h-4V8z"/></svg>',
    "github": '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.2 11.4.6.1.82-.26.82-.58v-2c-3.34.72-4.04-1.6-4.04-1.6-.55-1.38-1.34-1.75-1.34-1.75-1.1-.75.08-.73.08-.73 1.2.08 1.84 1.24 1.84 1.24 1.07 1.83 2.8 1.3 3.5 1 .1-.78.42-1.3.76-1.6-2.66-.3-5.47-1.33-5.47-5.93 0-1.3.47-2.38 1.24-3.22-.13-.3-.54-1.52.12-3.17 0 0 1-.32 3.3 1.23a11.5 11.5 0 0 1 6 0C17.3 4.3 18.3 4.62 18.3 4.62c.66 1.65.25 2.87.12 3.17.77.84 1.24 1.92 1.24 3.22 0 4.6-2.82 5.62-5.5 5.92.43.37.82 1.1.82 2.22v3.29c0 .32.22.69.82.57C20.57 22.3 24 17.8 24 12.5 24 5.87 18.63.5 12 .5z"/></svg>',
    "telegram": '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>',
    "email": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/></svg>',
}


# ---------------------------------------------------------------- helpers
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def strip_comments(t):
    out = []
    for line in t.split("\n"):
        res = ""
        for i, ch in enumerate(line):
            if ch == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            res += ch
        out.append(res)
    return "\n".join(out)


def inline(s):
    """Convert a snippet of inline LaTeX to HTML."""
    s = re.sub(r"\s+", " ", s).strip()
    out, i, n = "", 0, len(s)

    def read_group(j):
        depth, k = 0, j
        while k < len(s):
            if s[k] == "{":
                depth += 1
            elif s[k] == "}":
                depth -= 1
                if depth == 0:
                    return s[j + 1:k], k + 1
            k += 1
        return s[j + 1:], len(s)

    tagmap = {"textbf": "strong", "textit": "em", "emph": "em",
              "uline": "u", "underline": "u", "textsc": "span"}
    while i < n:
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+)", s[i:])
            if m:
                cmd = m.group(1)
                j = i + 1 + len(cmd)
                while j < n and s[j] == " ":
                    j += 1
                if cmd == "href":
                    url, j = read_group(j)
                    while j < n and s[j] == " ":
                        j += 1
                    txt, j = read_group(j)
                    out += f'<a href="{esc(url.strip())}" target="_blank" rel="noopener">{inline(txt)}</a>'
                    i = j
                    continue
                if cmd in tagmap:
                    if j < n and s[j] == "{":
                        inner, j = read_group(j)
                        tag = tagmap[cmd]
                        out += f"<{tag}>{inline(inner)}</{tag}>"
                        i = j
                        continue
                if cmd == "small":
                    if j < n and s[j] == "{":
                        inner, j = read_group(j)
                        out += inline(inner)
                        i = j
                        continue
                # unknown command: drop it (and an optional {..} arg)
                if j < n and s[j] == "{":
                    _, j = read_group(j)
                i = j
                continue
            else:  # escaped char
                nxt = s[i + 1] if i + 1 < n else ""
                if nxt == "&":
                    out += "&amp;"
                elif nxt in "%_#$":
                    out += nxt
                elif nxt == "\\":
                    out += " "
                else:
                    out += nxt
                i += 2
                continue
        if s[i:i + 3] == "---":
            out += "—"; i += 3; continue
        if s[i:i + 2] == "--":
            out += "—"; i += 2; continue
        if c == "~":
            out += " "; i += 1; continue
        if c == "$":
            i += 1; continue
        out += esc(c)
        i += 1
    return out.strip()


def extract_env(s, env, start=0):
    """Return (start, end, content) of the first balanced \\begin{env}..\\end{env}."""
    b, e = f"\\begin{{{env}}}", f"\\end{{{env}}}"
    i = s.find(b, start)
    if i < 0:
        return None
    depth, k = 0, i
    while k < len(s):
        if s.startswith(b, k):
            depth += 1
            k += len(b)
        elif s.startswith(e, k):
            depth -= 1
            k += len(e)
            if depth == 0:
                return (i + len(b), k - len(e), s[i + len(b):k - len(e)])
        else:
            k += 1
    return None


def read_groups(s, start, count):
    groups, i = [], start
    for _ in range(count):
        while i < len(s) and s[i] in " \n\t":
            i += 1
        if i >= len(s) or s[i] != "{":
            break
        depth, j = 0, i
        while j < len(s):
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        groups.append(s[i + 1:j])
        i = j + 1
    return groups


def strip_opt(s):
    return re.sub(r"^\s*\[[^\]]*\]", "", s)


def split_commas(s):
    """Split on top-level commas, keeping commas inside parentheses intact."""
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
            cur += ch
        elif ch == ")":
            depth = max(0, depth - 1)
            cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------- parse
TEX = strip_comments(TEX)
BODY = TEX.split(r"\begin{document}", 1)[1]
HEADER = BODY.split(r"\section{", 1)[0]

SECTIONS = {}
for m in re.finditer(r"\\section\{([^}]+)\}(.*?)(?=\\section\{|\\end\{document\})", BODY, re.S):
    SECTIONS[m.group(1).strip()] = m.group(2)

# name + contact
mn = re.search(r"\\textbf\{\\Large\s*([^}]+)\}", HEADER)
NAME = inline(mn.group(1)) if mn else "CV"
INITIALS = "".join(w[0] for w in re.sub(r"<[^>]+>", "", NAME).split()[:2]).upper()

links = {}
for m in re.finditer(r"\\href\{([^}]*)\}\{([^}]*)\}", HEADER):
    url = m.group(1).strip()
    if "linkedin.com/in" in url:
        links["linkedin"] = url
    elif "github.com" in url:
        links["github"] = url
    elif "t.me" in url:
        links["telegram"] = url
    elif url.startswith("mailto:"):
        links["email"] = url[len("mailto:"):]
mw = re.search(r"WhatsApp[^@\n]*@([A-Za-z0-9_.]+)", HEADER)
WHATSAPP = "@" + mw.group(1) if mw else ""


def socials_html(indent="            "):
    order = ["linkedin", "github", "telegram", "email"]
    labels = {"linkedin": "LinkedIn", "github": "GitHub", "telegram": "Telegram"}
    parts = []
    for k in order:
        if k == "email" and links.get("email"):
            parts.append(f'<a href="mailto:{links["email"]}" aria-label="Email">{SVG["email"]}</a>')
        elif links.get(k):
            parts.append(f'<a href="{links[k]}" target="_blank" rel="noopener" aria-label="{labels[k]}">{SVG[k]}</a>')
    return ("\n" + indent).join(parts)


# experience
def parse_experience():
    exp = SECTIONS.get("Experience", "")
    job_re = re.compile(
        r"\\item\s*(?:\\vspace\{[^}]*\}\s*)?\\textbf\{([^}]*)\}\s*\\hfill\s*"
        r"([^\\\n]+?)\s*\\\\\s*\\textit\{([^}]*)\}([^\n]*)", re.S)
    matches = list(job_re.finditer(exp))
    jobs = []
    for idx, m in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(exp)
        seg = exp[m.end():end]
        title, dates = inline(m.group(1)), inline(m.group(2))
        org = inline(m.group(3))
        loc = inline(m.group(4).strip().lstrip(",").strip())
        subroles = []
        outer = extract_env(seg, "itemize")
        if outer:
            oc = strip_opt(outer[2])
            for sm in re.finditer(r"\\item\s*\\textbf\{([^}]*)\}\s*\\hfill\s*([^\n]+)", oc):
                inner = extract_env(oc, "itemize", sm.end())
                bullets = []
                if inner:
                    for b in re.split(r"\\item", strip_opt(inner[2])):
                        b = b.strip()
                        if b:
                            bullets.append(inline(b))
                subroles.append((inline(sm.group(1)), inline(sm.group(2)), bullets))
        techm = re.search(r"\\small\{\\textbf\{Technologies:\}\s*([^}]*)\}", seg)
        techs = split_commas(techm.group(1)) if techm else []
        jobs.append((title, dates, org, loc, subroles, techs))
    return jobs


def render_experience():
    out = []
    for title, dates, org, loc, subroles, techs in parse_experience():
        org_line = f"{org} · {loc}" if loc else org
        roles = []
        for sr_title, sr_dates, bullets in subroles:
            lis = "\n".join(f"                <li>{b}</li>" for b in bullets)
            roles.append(
                f'            <div class="role">\n'
                f'              <div class="role__head">\n'
                f"                <h4>{sr_title}</h4>\n"
                f"                <span>{sr_dates}</span>\n"
                f"              </div>\n"
                f"              <ul>\n{lis}\n              </ul>\n"
                f"            </div>")
        chips = "".join(f"<span>{esc(t)}</span>" for t in techs)
        tech_block = (
            f'            <div class="tech">\n'
            f'              <span class="tech__label">Technologies</span>\n'
            f'              <div class="chips">{chips}</div>\n'
            f"            </div>") if techs else ""
        out.append(
            f'          <article class="job reveal">\n'
            f'            <div class="job__head">\n'
            f"              <div>\n"
            f"                <h3>{title}</h3>\n"
            f'                <p class="job__org">{org_line}</p>\n'
            f"              </div>\n"
            f'              <span class="job__date">{dates}</span>\n'
            f"            </div>\n\n"
            + "\n\n".join(roles)
            + (("\n\n" + tech_block) if tech_block else "")
            + "\n          </article>")
    return "\n\n".join(out)


def render_skills():
    sec = SECTIONS.get("Technical Skills", "")
    cards = []
    for m in re.finditer(r"\\item\s*\\textbf\{([^:}]*):\}\s*([^\n\\]+)", sec):
        cat = inline(m.group(1))
        chips = "".join(f"<span>{esc(x.strip())}</span>" for x in split_commas(m.group(2)))
        cards.append(
            f'          <div class="skill-card reveal">\n'
            f"            <h3>{cat}</h3>\n"
            f'            <div class="chips">{chips}</div>\n'
            f"          </div>")
    return "\n".join(cards)


def render_education():
    sec = SECTIONS.get("Education", "")
    items = []
    for m in re.finditer(r"\\resumeSubheading", sec):
        g = read_groups(sec, m.end(), 4)
        if len(g) < 4:
            continue
        school = inline(g[0])
        loc = inline(g[1])
        degree = inline(g[2]).replace(" | ", " · ")
        dates = inline(g[3])
        items.append(
            f'          <article class="edu__item reveal">\n'
            f'            <div class="edu__main">\n'
            f"              <h3>{school}</h3>\n"
            f"              <p>{degree}</p>\n"
            f"            </div>\n"
            f'            <div class="edu__meta">\n'
            f"              <span>{loc}</span>\n"
            f"              <span>{dates}</span>\n"
            f"            </div>\n"
            f"          </article>")
    return "\n".join(items)


def render_projects():
    sec = SECTIONS.get("Projects", "")
    items = []
    for m in re.finditer(r"\\resumeSubItem", sec):
        g = read_groups(sec, m.end(), 2)
        if len(g) < 2:
            continue
        items.append(
            f'          <article class="project reveal">\n'
            f"            <h3>{inline(g[0])}</h3>\n"
            f"            <p>{inline(g[1])}</p>\n"
            f"          </article>")
    return "\n".join(items)


def render_achievements():
    sec = SECTIONS.get("Achievements", "")
    env = extract_env(sec, "itemize")
    if not env:
        return ""
    items = []
    for raw in re.split(r"\\item", strip_opt(env[2])):
        raw = raw.strip()
        if not raw:
            continue
        date = ""
        if "|" in raw:
            raw, date = raw.rsplit("|", 1)
        text = inline(raw.strip())
        date = inline(date.strip())
        li = f'          <li class="reveal"><span class="dot"></span>{text}'
        if date:
            li += f" <em>· {date}</em>"
        li += "</li>"
        items.append(li)
    return "\n".join(items)


# ---------------------------------------------------------------- render
html_out = TEMPLATE
repl = {
    "{{NAME}}": NAME,
    "{{INITIALS}}": INITIALS,
    "{{EMAIL}}": links.get("email", ""),
    "{{LINKEDIN}}": links.get("linkedin", "#"),
    "{{WHATSAPP}}": WHATSAPP,
    "{{SOCIALS}}": socials_html(),
    "{{EXPERIENCE}}": render_experience(),
    "{{SKILLS}}": render_skills(),
    "{{EDUCATION}}": render_education(),
    "{{PROJECTS}}": render_projects(),
    "{{ACHIEVEMENTS}}": render_achievements(),
}
for k, v in repl.items():
    html_out = html_out.replace(k, v)

(ROOT / "index.html").write_text(html_out, encoding="utf-8")
print("index.html generated from cv.tex "
      f"(name={NAME!r}, jobs, skills, education, projects, achievements).")
