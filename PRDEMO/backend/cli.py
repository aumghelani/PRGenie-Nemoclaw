"""
PRClaw CLI — demo against any real GitHub PR.

Usage:
    python -m backend.cli triage-pr <owner/repo> <pr_number>
    python -m backend.cli triage-pr aumghelani/Redhat-Hackathon-JABST 1 --dry-run

Requires GITHUB_PAT in .env (no GitHub App registration needed).
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime

import click

from backend.agents.persona_extractor import extract_persona
from backend.agents.reviewer_suggester import suggest_reviewer
from backend.agents.risk_agent import compute_risk
from backend.agents.triage_agent import (
    analyze_pr,
    format_check_run_summary,
    format_triage_comment,
)
from backend.agents.trust_scorer import compute_trust
from backend.config import settings
from backend.db.session import get_session, init_engine
from backend.db.store import save_pr_analysis
from backend.github_client import GitHubClient
from backend.llm.client import LLMClient
from backend.nemo_claw.policy_enforcer import PolicyEnforcer

# Pretty terminal output (Rich is in requirements via pytest)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    console = Console()
    HAS_RICH = True
except ImportError:
    console = None
    HAS_RICH = False


@click.group()
def cli():
    """PRClaw — GitHub-native PR triage agent."""


@cli.command("triage-pr")
@click.argument("repo")  # "owner/repo"
@click.argument("pr_number", type=int)
@click.option("--dry-run", is_flag=True, help="Print the analysis but don't post to GitHub.")
def triage_pr(repo: str, pr_number: int, dry_run: bool):
    """
    Run the full triage pipeline on a real GitHub PR.

    REPO is "owner/repo". Requires GITHUB_PAT in .env.
    """
    if "/" not in repo:
        click.echo("error: REPO must be in the form 'owner/repo'", err=True)
        sys.exit(1)

    if not settings.GITHUB_PAT:
        click.echo(
            "error: GITHUB_PAT not set. Add it to .env "
            "(github.com/settings/tokens, scope=repo).",
            err=True,
        )
        sys.exit(1)

    asyncio.run(_run(repo, pr_number, dry_run))


async def _run(repo_full_name: str, pr_number: int, dry_run: bool) -> None:
    init_engine()

    # Force GitHub live (we're using PAT), keep LLM mode whatever .env says.
    github = GitHubClient(mock_mode=False)
    llm = LLMClient()

    if HAS_RICH:
        console.print(Panel(
            f"[bold magenta]🤖 PRClaw[/bold magenta]  triaging "
            f"[cyan]{repo_full_name}#{pr_number}[/cyan]\n"
            f"LLM: [yellow]{llm.model}[/yellow]   Dry-run: [yellow]{dry_run}[/yellow]",
            border_style="magenta",
        ))

    # 1. Fetch the PR via GitHub REST API.
    _step("Fetching PR from GitHub…")
    pr_resp = await github._request("GET", f"/repos/{repo_full_name}/pulls/{pr_number}", installation_id=0)
    pr = pr_resp.json()
    author = pr["user"]["login"]
    files = await github.get_pr_files(repo_full_name, pr_number, installation_id=0)
    file_names = [f["filename"] for f in files]
    diff = await github.get_pr_diff(repo_full_name, pr_number, installation_id=0)
    _ok(f"PR #{pr_number} '{pr['title']}' by @{author}, {len(files)} files, +{pr['additions']} -{pr['deletions']}")

    # 2. NemoClaw policy.
    _step("Loading NemoClaw policy from .github/prclaw.yml…")
    policy = await PolicyEnforcer.from_repo(repo_full_name, github, installation_id=0)
    _ok(f"Policy loaded — strictness={policy.doc.persona.strictness}, forbidden={list(policy._forbidden)}")

    # 3. Trust + Risk + Reviewer.
    _step("Trust Scorer (rule-based, no LLM)…")
    trust = await compute_trust(author, repo_full_name, github, installation_id=0,
                                cache_hours=policy.doc.trust.cache_hours)
    _ok(f"trust_level={trust['trust_level']}  trust_score={trust['trust_score']:.2f}")

    _step("Risk Agent (pattern matching, no LLM)…")
    risk = compute_risk(file_names, pr["additions"], pr["deletions"],
                        trust["trust_level"], extra_sensitive=policy.extra_sensitive_paths())
    _ok(f"risk_level={risk['risk_level']}  sensitive_files={risk['sensitive_files']}")

    _step("Reviewer Suggester (git blame ownership, no LLM)…")
    reviewer = await suggest_reviewer(repo_full_name, file_names, author, github, installation_id=0)
    _ok(f"suggested_reviewer={reviewer or '(no clear owner)'}")

    # 4. Persona + Triage (LLM).
    _step(f"Persona Extractor (1 LLM call to {llm.model})…")
    persona = await extract_persona(repo_full_name, repo_full_name.split("/")[0],
                                    github, llm, installation_id=0)
    _ok(f"focus={persona.get('focus')}  tone={persona.get('tone')}")

    _step(f"Triage Agent (1 LLM call to {llm.model})…")
    analysis = await analyze_pr(
        pr_data={
            "pr_number": pr_number, "pr_title": pr["title"], "author": author,
            "files": files, "additions": pr["additions"], "deletions": pr["deletions"],
            "diff": diff,
        },
        persona=persona, trust=trust, risk=risk,
        suggested_reviewer=reviewer, llm=llm,
    )
    _ok(f"priority={analysis['priority']}  action={analysis['suggested_action']}  "
        f"concerns={len(analysis.get('concerns', []))}")

    # 5. NemoClaw gate.
    triage_comment = format_triage_comment(analysis, trust, risk, reviewer)
    policy.assert_disclosure(triage_comment)  # raises if disclosure missing

    # 6. Show the formatted comment.
    if HAS_RICH:
        console.print()
        console.print(Panel(Markdown(triage_comment), title="📋 Bot comment that will be posted",
                           border_style="green" if not dry_run else "yellow"))
    else:
        click.echo("\n--- Bot comment ---")
        click.echo(triage_comment)

    # 7. Post (or skip in dry-run).
    if dry_run:
        _warn("Dry-run — NOT posting to GitHub.")
        return

    _step("Posting triage comment to GitHub…")
    comment_id = await github.post_pr_comment(repo_full_name, pr_number, triage_comment, installation_id=0)
    _ok(f"Posted comment id={comment_id}")

    _step("Applying labels…")
    labels = []
    if policy.can_apply_label(f"trust:{trust['trust_level']}"):
        labels.append(f"trust:{trust['trust_level']}")
    if policy.can_apply_label(f"risk:{risk['risk_level']}"):
        labels.append(f"risk:{risk['risk_level']}")
    if labels:
        try:
            await github.add_labels(repo_full_name, pr_number, labels, installation_id=0)
            _ok(f"Applied labels: {labels}")
        except Exception as e:
            _warn(f"Label add failed (often: labels don't exist on repo yet): {e}")

    # 8. Cache.
    with get_session() as s:
        save_pr_analysis(s, pr_number, repo_full_name, {
            **analysis,
            "trust_level": trust["trust_level"],
            "risk_level": risk["risk_level"],
            "suggested_reviewer": reviewer,
            "bot_comment_id": comment_id,
        })

    if HAS_RICH:
        console.print()
        console.print(Panel(
            f"✅  Done. Open https://github.com/{repo_full_name}/pull/{pr_number} to see the comment.",
            border_style="green",
        ))


# -- pretty helpers ---------------------------------------------------------


def _step(msg: str) -> None:
    if HAS_RICH:
        console.print(f"[bold blue]→[/bold blue] {msg}")
    else:
        click.echo(f"-> {msg}")


def _ok(msg: str) -> None:
    if HAS_RICH:
        console.print(f"  [green]✓[/green] {msg}")
    else:
        click.echo(f"   OK  {msg}")


def _warn(msg: str) -> None:
    if HAS_RICH:
        console.print(f"  [yellow]⚠[/yellow] {msg}")
    else:
        click.echo(f"   !!  {msg}")


if __name__ == "__main__":
    cli()
