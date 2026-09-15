# Sample Repo

A deliberately small codebase the tiny agent can operate on. Contains a couple of files with intentional problems for the agent to discover and fix.

## Contents

- `Hello.java` — simple greeting helper.
- `MathUtils.java` — small library with a few helpers. Has a bug.
- `TODO.md` — a list of tasks you can ask the agent to do.

## Running the agent against this

From the `tiny-agent-java/` root, install the modules once so `exec:java` can resolve them:

```bash
./mvnw install -DskipTests
```

Then, from `sample_repo/`, with `GOOGLE_API_KEY` set:

```bash
cd sample_repo
../mvnw -f ../reference/pom.xml exec:java -Dexec.args="List the files here and give me a summary of what this codebase does"
```

Swap `../reference/pom.xml` for `../starter/pom.xml` to drive your own implementation.

Or pick any task from `TODO.md` and paste it as the prompt.
