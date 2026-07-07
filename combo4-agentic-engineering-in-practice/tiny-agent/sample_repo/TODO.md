# Tasks you can ask the agent to do

Pick any of these as a prompt to `python -m reference.agent`:

## Exploration

1. *"List the files in this repo and summarise what the code does."*
2. *"What functions does `math_utils.py` export? Describe each in one sentence."*

## Bug-fix

3. *"Run through `math_utils.py` and look for any bugs. If you find one, fix it with `edit_file` and explain what you changed."*
   - Expected: the agent finds `factorial(0)` returns 0, replaces the early-return with `return 1`.

## Small feature work

4. *"Add a docstring to the `greet` function in `hello.py` explaining what it does, in the same style as the docstrings in `math_utils.py`."*
5. *"Add a `lcm(a, b)` helper to `math_utils.py` that uses the existing `gcd` function."*

## Documentation

6. *"Write a README section for `math_utils.py` that lists each function with a one-line description. Add it to `sample_repo/README.md` between the 'Contents' section and the 'Running the agent against this' section."*

## Stretch (M1 stretch exercise)

7. *"Read `hello.py` and propose three ways to make it more robust. Don't edit the file — just explain each option."*
   (This should trigger no `edit_file` calls. Good test of 'no-tool-call means done'.)
