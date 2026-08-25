# Tasks you can ask the agent to do

Pick any of these as a prompt. Run from `sample_repo/`:

```bash
npx tsx ../src/cli.ts "<prompt>"
```

## Exploration

1. *"List the files in this repo and summarise what the code does."*
2. *"What functions does `mathUtils.ts` export? Describe each in one sentence."*

## Bug-fix

3. *"Run through `mathUtils.ts` and look for any bugs. If you find one, fix it with `edit_file` and explain what you changed."*
   - Expected: the agent finds `factorial(0)` returns 0, replaces the early return with `return 1`.

## Small feature work

4. *"Add a doc comment to the `greet` function in `hello.ts` explaining what it does, in the same style as the comments in `mathUtils.ts`."*
5. *"Add an `lcm(a, b)` helper to `mathUtils.ts` that uses the existing `gcd` function."*

## Documentation

6. *"Write a README section for `mathUtils.ts` that lists each function with a one-line description. Add it to `README.md` between the 'Contents' section and the 'Running the agent against this' section."*

## Stretch (M8 stretch exercise)

7. *"Read `hello.ts` and propose three ways to make it more robust. Don't edit the file — just explain each option."*
   (This should trigger no `edit_file` calls. Good test of 'no-tool-call means done'.)
