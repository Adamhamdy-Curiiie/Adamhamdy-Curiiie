"""Generate the profile language card using the authenticated GitHub CLI."""

import json
import os
import shutil
import subprocess
from collections import Counter
from html import escape
from pathlib import Path


CARD = Path(__file__).resolve().parents[2] / "assets" / "most-used-languages.svg"
COLORS = ("#00f0ff", "#ff2a85", "#ff6a00", "#f5d565", "#b69bff", "#82e8b0")


def find_gh():
    if executable := shutil.which("gh"):
        return executable
    if os.name == "nt":
        executable = Path(os.environ["ProgramFiles"]) / "GitHub CLI" / "gh.exe"
        if executable.is_file():
            return str(executable)
    raise SystemExit("The GitHub CLI (gh) is required to collect language statistics.")


def gh_api(gh, endpoint, *options):
    return subprocess.run(
        [gh, "api", "--hostname", "github.com", endpoint, *options],
        check=True, stdout=subprocess.PIPE, encoding="utf-8",
    ).stdout


def repository_names(gh):
    # The default Actions token belongs to an installation and cannot list /user/repos.
    workflow_token = os.environ.get("GITHUB_ACTIONS") == "true" and not os.environ.get("GH_TOKEN")
    if workflow_token:
        owner = os.environ["GITHUB_REPOSITORY_OWNER"]
        endpoint = f"users/{owner}/repos?type=owner"
    else:
        endpoint = "user/repos?visibility=all&affiliation=owner,collaborator,organization_member"

    listing = gh_api(gh, endpoint + "&sort=created&direction=asc&per_page=100",
                     "--paginate", "--jq", ".[].full_name")
    names = {name.lower() for name in listing.splitlines()}
    if workflow_token:
        # A private workflow repository can be absent from the owner's public listing.
        names.add(os.environ["GITHUB_REPOSITORY"].lower())
    return sorted(names)


def collect_languages(gh, repositories):
    totals = Counter()
    repo_count = 0
    for name in repositories:
        languages = json.loads(gh_api(gh, f"repos/{name}/languages"))
        if sum(languages.values()) > 0:
            totals.update(languages)
            repo_count += 1
    return totals, repo_count


def render_card(totals, repo_count, checked):
    counted = ((name, size) for name, size in totals.items() if size > 0)
    rows = sorted(counted, key=lambda item: (-item[1], item[0]))
    total_bytes = sum(size for _, size in rows)
    if len(rows) > len(COLORS):
        first_other = len(COLORS) - 1
        rows = rows[:first_other] + [("Other", sum(size for _, size in rows[first_other:]))]

    height = 137 + 30 * max(1, len(rows))
    repos_label = "repository" if checked == 1 else "repositories"
    scope = f"{repo_count:,} of {checked:,} {repos_label} with language bytes · {total_bytes:,} bytes"
    segments = []
    legend = []
    description = [f"GitHub reported language bytes in {repo_count:,} of {checked:,} {repos_label} checked."]
    offset = 0
    for index, ((language, size), color) in enumerate(zip(rows, COLORS)):
        share = size / total_bytes
        percent = "&lt;0.01%" if share < 0.0001 else f"{share:.2%}"
        name = escape(language)
        description.append(f"{name} {percent}.")
        x = 30 + 460 * offset / total_bytes
        segments.append(
            f'    <rect x="{x:.4f}" y="92" width="{460 * share:.4f}" height="14" fill="{color}"/>'
        )
        offset += size
        y = 140 + 30 * index
        if index:
            legend.append(f'    <path d="M30 {y - 21}h460" stroke="#202c39"/>')
        legend.append(f'''    <g>
      <title>{name} · {size:,} bytes</title>
      <path d="M30 {y - 7}l4 -4h8v8l-4 4h-8z" fill="{color}"/>
      <text x="53" y="{y}">{name}</text>
      <text x="490" y="{y}" class="share" fill="{color}">{percent}</text>
    </g>''')

    if not rows:
        empty_message = "No language bytes reported yet."
        legend.append(f'    <text x="30" y="140">{empty_message}</text>')
        description.append(empty_message)
    bar_svg = "\n".join(segments)
    legend_svg = "\n".join(legend)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="{height}" viewBox="0 0 520 {height}" role="img" aria-labelledby="title desc">
  <title id="title">Most Used Languages</title>
  <desc id="desc">{" ".join(description)}</desc>
  <defs>
    <linearGradient id="panel" x2="1" y2="1" gradientUnits="objectBoundingBox">
      <stop stop-color="#0d1017"/><stop offset="1" stop-color="#090b10"/>
    </linearGradient>
    <linearGradient id="edge">
      <stop stop-color="#00f0ff"/><stop offset=".38" stop-color="#315165"/>
      <stop offset=".75" stop-color="#46344d"/><stop offset="1" stop-color="#ff2a85"/>
    </linearGradient>
    <clipPath id="bar"><path d="M30 97l5 -5h455v9l-5 5H30z"/></clipPath>
    <pattern id="ticks" x="30" y="92" width="10" height="14" patternUnits="userSpaceOnUse">
      <path d="M5 0L1 14" stroke="#090b10" stroke-opacity=".42" stroke-width="1.5"/>
    </pattern>
    <style>
      text {{ font-family: Inter, 'Segoe UI', Arial, sans-serif }}
      .share {{ font-family: 'IBM Plex Mono', Consolas, 'Liberation Mono', monospace; text-anchor: end }}
    </style>
  </defs>
  <path d="M19 2h146l6 5h186l6 -5h133l22 22v{height - 44}l-18 18H22L2 {height - 22}V19z"
        fill="url(#panel)" stroke="url(#edge)" stroke-width="2"/>
  <g fill="none">
    <path d="M9 49V23l14 -14h46" stroke="#00f0ff" stroke-width="2"/>
    <path d="M511 {height - 43}v20l-14 14h-40" stroke="#ff2a85" stroke-width="2"/>
    <path d="M24 {height - 8}h62l4 -4h24" stroke="#294452"/>
  </g>
  <g transform="translate(447 33)">
    <path d="M0 13L8 0h8L8 13z" fill="#00f0ff"/>
    <path d="M14 13l8 -13h8l-8 13z" fill="#ff2a85"/>
    <path d="M28 13l8 -13h8l-8 13z" fill="#ff6a00"/>
  </g>
  <text x="29" y="49" fill="#f2f6fb" font-size="29" font-weight="700" letter-spacing="-.8">Most Used Languages</text>
  <text x="30" y="72" fill="#a4b4c5" font-size="14">{scope}</text>
  <g clip-path="url(#bar)">
    <rect x="30" y="92" width="460" height="14" fill="#22313f"/>
{bar_svg}
    <rect x="30" y="92" width="460" height="14" fill="url(#ticks)"/>
  </g>
  <g fill="#e0e9f1" font-size="16">
{legend_svg}
  </g>
</svg>
'''


if __name__ == "__main__":
    gh = find_gh()
    repositories = repository_names(gh)
    totals, repo_count = collect_languages(gh, repositories)
    svg = render_card(totals, repo_count, len(repositories))
    CARD.parent.mkdir(parents=True, exist_ok=True)
    CARD.write_text(svg, encoding="utf-8", newline="\n")
    print(f"Repositories checked: {len(repositories):,}")
    print(f"Repositories with language bytes: {repo_count:,}")
    print(f"Total bytes counted: {sum(totals.values()):,}")
