# Predictions · Assignment 1, Part B

Written before any evaluation run, after one to ten dev runs per way on 4191 and
4192. Model: gpt-4.1-mini, held fixed. Each way runs 60 times (6 issues × 10).

| Way | Passes I expect, of 60 | Hardest issue I expect |
|---|---|---|
| Direct call | 32 | 4206 |
| Workflow | 36 | 4206 |
| Agent | 38 | 4204 |

## Direct call: 32 of 60, hardest 4206

It never sees code, only the repo summary, so it has to guess from filenames. I
expect it to do fine where the summary line basically names the answer (the
question, the TSV request) and badly on 4206, because the title names
`src/export/csv.ts` and with no code to read it has no reason to look past that.

## Workflow: 36 of 60, hardest 4206

Searching should fix some of the direct call's guesses (searching "localhost"
or a timezone word should land in real code), but it searches once, for terms
picked before it has seen any code, so it can't follow a lead. On 4206 I think
the terms will come straight from the title and the choose step will take the
file the reporter named.

## Agent: 38 of 60, hardest 4204

It can keep searching and follow what it finds, so it should be the only way
with a real chance on 4206. On the dev issues, though, it posted nothing in
about one run out of six because it kept searching until the turn limit, and I
expect that to cost it a few runs on every issue. 4204 (the Monday email
arriving on Tuesday in Sydney) has several plausible files: the rollup email,
the scheduler and the date helpers. I expect it to spread its answers over them
more than on any other issue.
