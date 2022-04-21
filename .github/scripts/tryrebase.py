#!/usr/bin/env python3

import os
from typing import Any
from gitutils import get_git_remote_name, get_git_repo_dir, GitRepo
from trymerge import gh_post_comment, GitHubPR


def parse_args() -> Any:
    from argparse import ArgumentParser
    parser = ArgumentParser("Rebase PR into branch")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rebase", action="store_true")
    parser.add_argument("--comment-id", type=int)
    parser.add_argument("--branch", type=str)
    parser.add_argument("pr_num", type=int)
    return parser.parse_args()


def rebase_onto(pr: GitHubPR, repo: GitRepo, branch: str, dry_run: bool = False) -> None:
    pr_branch_name = f"rebase-pr-{pr.pr_num}"
    repo.fetch(f"pull/{pr.pr_num}/head", pr_branch_name)
    if branch is None:
        branch = pr.default_branch()
    print(repo._run_git("rebase", branch, pr_branch_name))
    remote = f"https://github.com/{pr.info['headRepository']['nameWithOwner']}.git"
    refspec = f"{pr_branch_name}:{pr.head_ref()}"
    if dry_run:
        repo._run_git("push", "--dry-run", "-f", remote, refspec)
    else:
        push_result = repo._run_git("push", "-f", remote, refspec)
        print(push_result)
        if "Everything up-to-date" in push_result:
            gh_post_comment(pr.org, pr.project, pr.pr_num, "tried to rebase and push, but was already up to date", dry_run=dry_run)



def main() -> None:
    args = parse_args()
    repo = GitRepo(get_git_repo_dir(), get_git_remote_name(), debug=True)
    org, project = repo.gh_owner_and_name()

    pr = GitHubPR(org, project, args.pr_num)

    if pr.is_closed():
        gh_post_comment(org, project, args.pr_num, f"PR #{args.pr_num} is closed, won't rebase", dry_run=args.dry_run)
        return

    if pr.is_ghstack_pr():
        gh_post_comment(org, project, args.pr_num,
                        f"PR #{args.pr_num} is a ghstack, which is currently not supported", dry_run=args.dry_run)
        return

    try:
        rebase_onto(pr, repo, args.branch, dry_run=args.dry_run)
    except Exception as e:
        msg = f"Rebase failed due to {e}"
        run_url = os.getenv("GH_RUN_URL")
        if run_url is not None:
            msg += f"\nRaised by {run_url}"
        gh_post_comment(org, project, args.pr_num, msg, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
