# Onboarding – start contributing in 10 minutes

Welcome! This is the quick start for new developers on the Tectonic Hackathon KBC project.

## 1. Get access
1. Create/sign in to a [GitHub](https://github.com) account.
2. Send your GitHub username to **@davidvandoveren** to be added as collaborator (you will get an email invite – accept it).

## 2. Install the basics
- [Git](https://git-scm.com/downloads)
- A code editor ([Cursor](https://cursor.com) or VS Code)
- Optional: [GitHub CLI](https://cli.github.com) (`gh auth login` makes authentication easy)
- Language runtimes: decided in `README.md` once the stack is chosen

## 3. Clone the repo
```bash
git clone https://github.com/davidvandoveren/tectonichackathon.git
cd tectonichackathon
git config user.name  "Your Name"
git config user.email "you@example.com"
```

## 4. Daily workflow (we do NOT push to `main`)
```bash
git checkout main && git pull            # start from the latest main
git checkout -b feature/short-description # one branch per task
# ...make changes, commit small and often...
git add <files>
git commit -m "Short, clear message"
git push -u origin feature/short-description
```
Then open a **Pull Request** on GitHub (or `gh pr create --fill`). Another teammate reviews, you merge. `main` is protected: direct pushes are blocked.

## 5. Ground rules
- **No secrets** in git: no API keys, passwords, tokens, real customer data. Use a local `.env` (already git-ignored) and share keys via a private channel.
- **Synthetic data only.**
- Keep PRs small (ideally < 300 lines) so reviews are fast.
- Write down what is unfinished in the README – the hackathon rules require it.
- Be kind in reviews.

## 6. Where to look first
- `README.md` – the case, judging criteria, run instructions
- `docs/ideas.md` – brainstorm and open decisions (add your ideas via PR!)
- `CONTRIBUTING.md` – branch naming, commit and review conventions

## Need help?
Ask in the team chat or open a GitHub Issue with the `question` label.
