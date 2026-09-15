package ai.octoco.tinyagent.tests;

import ai.octoco.tinyagent.shared.AgentEvent;
import ai.octoco.tinyagent.shared.GeminiClient;
import ai.octoco.tinyagent.shared.Tools;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * The agent loop under test — the same switch as {@link ToolsFactory}, so
 * step 1 gets a test suite too.
 */
final class AgentFactory {

    private AgentFactory() {}

    static CompletableFuture<String> runAsync(String prompt, Tools tools, GeminiClient client, String model) {
        return runAsync(prompt, tools, client, model, 20, evt -> { });
    }

    static CompletableFuture<String> runAsync(
            String prompt, Tools tools, GeminiClient client, String model, int maxTurns) {
        return runAsync(prompt, tools, client, model, maxTurns, evt -> { });
    }

    static CompletableFuture<String> runAsync(
            String prompt,
            Tools tools,
            GeminiClient client,
            String model,
            int maxTurns,
            Consumer<AgentEvent> onEvent) {
        return "reference".equals(Impl.selected())
                ? ai.octoco.tinyagent.reference.Agent.runAsync(prompt, tools, client, model, maxTurns, onEvent)
                : ai.octoco.tinyagent.starter.Agent.runAsync(prompt, tools, client, model, maxTurns, onEvent);
    }
}
