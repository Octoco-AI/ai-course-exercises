# Tasks you can ask the agent to do

Pick any of these as a prompt. Run from `sample_repo/`:

```bash
dotnet run --project ../src/TinyAgent.Starter -- "<prompt>"
```

## Exploration

1. *"List the files in this repo and summarise what the code does."*
2. *"What methods does `MathUtils.cs` expose? Describe each in one sentence."*

## Bug-fix

3. *"Run through `MathUtils.cs` and look for any bugs. If you find one, fix it with `edit_file` and explain what you changed."*
   - Expected: the agent finds `Factorial(0)` returns 0, replaces the early return with `return 1`.

## Small feature work

4. *"Add an XML doc comment to the `Greet` method in `Hello.cs` explaining what it does, in the same style as the comments in `MathUtils.cs`."*
5. *"Add an `Lcm(int a, int b)` helper to `MathUtils.cs` that uses the existing `Gcd` method."*

## Documentation

6. *"Write a README section for `MathUtils.cs` that lists each method with a one-line description. Add it to `README.md` between the 'Contents' section and the 'Running the agent against this' section."*

## Stretch (M8 stretch exercise)

7. *"Read `Hello.cs` and propose three ways to make it more robust. Don't edit the file — just explain each option."*
   (This should trigger no `edit_file` calls. Good test of 'no-tool-call means done'.)
