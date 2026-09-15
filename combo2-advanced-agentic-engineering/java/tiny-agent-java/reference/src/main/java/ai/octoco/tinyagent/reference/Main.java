package ai.octoco.tinyagent.reference;

import ai.octoco.tinyagent.shared.Cli;

public final class Main {

    private Main() {}

    public static void main(String[] args) {
        int exitCode = Cli.run(
                args,
                "Usage: ../mvnw -f ../reference/pom.xml exec:java -Dexec.args=\"<your prompt>\"",
                ReferenceTools::new,
                (prompt, tools, client, onEvent) -> Agent.runAsync(prompt, tools, client, null, 20, onEvent));

        System.exit(exitCode);
    }
}
