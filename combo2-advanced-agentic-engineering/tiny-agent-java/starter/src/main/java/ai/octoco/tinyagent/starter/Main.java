package ai.octoco.tinyagent.starter;

import ai.octoco.tinyagent.shared.Cli;

public final class Main {

    private Main() {}

    public static void main(String[] args) {
        int exitCode = Cli.run(
                args,
                "Usage: ../mvnw -f ../starter/pom.xml exec:java -Dexec.args=\"<your prompt>\"",
                StarterTools::new,
                (prompt, tools, client, onEvent) -> Agent.runAsync(prompt, tools, client, null, 20, onEvent));

        System.exit(exitCode);
    }
}
