# Push this project to another GitHub account

Follow these steps to push the entire codebase to a **new GitHub account** (no code changes).

---

## 1. Create a new repo on the other GitHub account

1. Log in to the **other** GitHub account.
2. Click **New repository**.
3. Set repository name (e.g. `nityadharma`).
4. Choose **Public** or **Private**.
5. **Do not** add a README, .gitignore, or license (you already have them).
6. Click **Create repository**.
7. Copy the new repo URL, e.g. `https://github.com/OTHER_USER/nityadharma.git`.

---

## 2. Add the new remote and push

Open a terminal in the project root (`Nitya Dharma` folder) and run:

```bash
# Add the new GitHub repo as a remote (use your actual URL)
git remote add neworigin https://github.com/OTHER_USER/REPO_NAME.git

# Push all branches to the new remote
git push -u neworigin --all

# Optional: push tags if you have any
git push neworigin --tags
```

Replace `OTHER_USER` and `REPO_NAME` with the other account’s username and repo name.

---

## 3. Use the new account for future pushes

To push to the **new** account from this machine:

```bash
git push neworigin main
```

(Use `master` instead of `main` if your default branch is `master`.)

To make `neworigin` the default remote:

```bash
git remote rename origin oldorigin
git remote rename neworigin origin
git push -u origin main
```

---

## What is not pushed

- The folder **`_md_archive/`** is in `.gitignore`, so it is **not** pushed. It contains the moved .md files (audits, reports, guides, etc.).
- Only **`README.md`** stays in the project root and is pushed.
- Your **code, templates, and config** are pushed as usual.

---

## If this repo doesn’t have git yet

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/OTHER_USER/REPO_NAME.git
git push -u origin main
```

Then continue from step 2 if you need to add another remote.
