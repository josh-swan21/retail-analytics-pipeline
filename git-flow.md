========================================
RETAIL ANALYTICS — GIT WORKFLOW
========================================


1. START SESSION
----------------------------------------

git status
git branch
git switch main
git pull origin main

Ask:
- What state is the repository in?
- Did I leave anything uncommitted?
- Is main current?


2. DEFINE TODAY'S CHANGE
----------------------------------------

Examples:

feature/order-mart
feature/customer-model
feature/shopify-ingestion
fix/order-duplicates
refactor/python-cleaning

Create branch:

git switch -c feature/name-of-feature


3. WORK
----------------------------------------

Write/change:
- Python
- SQL
- dbt
- YAML
- tests
- documentation
- configuration


4. CHECK CHANGES
----------------------------------------

git status

git diff

Ask:
- What files changed?
- Why did they change?
- Are any changes accidental?


5. TEST
----------------------------------------

Examples:

dbt run --select model_name

dbt test --select model_name

dbt build --select model_name

python script_name.py

Validate Snowflake output if necessary.


6. STAGE
----------------------------------------

Preferred:

git add path/to/file

or multiple files:

git add file1
git add file2

Use cautiously:

git add .


7. REVIEW STAGED CHANGES
----------------------------------------

git status

git diff --staged

Ask:

"Is everything in this staged change part of
the same logical unit of work?"


8. COMMIT
----------------------------------------

git commit -m "Add Shopify order staging model"

Good verbs:

Add
Create
Fix
Update
Refactor
Remove
Document
Implement
Validate


9. CONTINUE WORKING
----------------------------------------

Repeat:

work
↓
test
↓
git status
↓
git diff
↓
git add
↓
git diff --staged
↓
git commit


10. PUSH
----------------------------------------

First branch push:

git push -u origin branch-name

Later:

git push


11. FINISH FEATURE
----------------------------------------

git status

Make sure working tree is clean.

Then:

git switch main

git pull origin main

git merge branch-name

git push origin main


12. CLEAN UP
----------------------------------------

git branch -d branch-name

git status

git log --oneline