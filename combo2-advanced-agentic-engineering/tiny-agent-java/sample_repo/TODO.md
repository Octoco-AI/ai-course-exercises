# Tasks you can ask the agent to do

Pick any of these as a prompt. Run from `sample_repo/` (after `./mvnw install -DskipTests` once from the project root):

```bash
../mvnw -f ../starter/pom.xml exec:java -Dexec.args="<prompt>"
```

## Exploration

1. *"List the files in this repo and summarise what the code does."*
2. *"What methods does `MathUtils.java` expose? Describe each in one sentence."*

## Bug-fix

3. *"Run through `MathUtils.java` and look for any bugs. If you find one, fix it with `edit_file` and explain what you changed."*
   - Expected: the agent finds `factorial(0)` returns 0, replaces the early return with `return 1`.

## Small feature work

4. *"Add a Javadoc comment to the `greet` method in `Hello.java` explaining what it does, in the same style as the comments in `MathUtils.java`."*
5. *"Add an `lcm(int a, int b)` helper to `MathUtils.java` that uses the existing `gcd` method."*

## Documentation

6. *"Write a README section for `MathUtils.java` that lists each method with a one-line description. Add it to `README.md` between the 'Contents' section and the 'Running the agent against this' section."*

## Stretch (M8 stretch exercise)

7. *"Read `Hello.java` and propose three ways to make it more robust. Don't edit the file — just explain each option."*
   (This should trigger no `edit_file` calls. Good test of 'no-tool-call means done'.)
