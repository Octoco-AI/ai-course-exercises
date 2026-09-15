package ai.octoco.tinyagent.tests;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.octoco.tinyagent.reference.ReferenceTools;
import ai.octoco.tinyagent.shared.GeminiClient;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The loop's contract, tested offline against a canned model.
 *
 * <p>These cover the three mistakes the facilitator notes say account for
 * most failures in the room: forgetting to append the model's own turn,
 * sending tool results under the wrong role, and never terminating.
 *
 * <p>They run against <b>your</b> loop, via the same {@code TINY_AGENT_IMPL}
 * switch the tool tests use (see {@link Impl}), so they are red until step 1
 * is done — that's the point. To watch them green against the worked
 * solution: {@code TINY_AGENT_IMPL=reference ./mvnw test}
 *
 * <p>The tools they call are always the reference ones: these tests are about
 * the loop, and should not go red because step 2 is still unwritten.
 */
final class AgentLoopTests {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private Path sandbox;

    @BeforeEach
    void setUp() throws IOException {
        sandbox = Files.createTempDirectory("tiny-agent-loop-");
        Files.writeString(sandbox.resolve("hello.txt"), "hello world\n");
    }

    @AfterEach
    void tearDown() throws IOException {
        deleteRecursively(sandbox);
    }

    private record Run(String finalText, FakeGeminiTransport transport) {}

    private Run run(String... turns) {
        var transport = new FakeGeminiTransport(turns);
        var client = new GeminiClient("test-key", transport);
        var tools = new ReferenceTools(sandbox.toString());

        String finalText = AgentFactory.runAsync("do the thing", tools, client, "fake-model").join();
        return new Run(finalText, transport);
    }

    @Test
    void returnsTextWhenModelMakesNoToolCall() {
        var result = run(FakeGeminiTransport.textTurn("All done."));

        assertEquals("All done.", result.finalText());
        assertEquals(1, result.transport().requests().size());
    }

    @Test
    void runsToolThenReturnsFinalText() {
        var result = run(
                FakeGeminiTransport.toolCallTurn("read_file", Map.of("path", "hello.txt")),
                FakeGeminiTransport.textTurn("The file says hello world."));

        assertEquals("The file says hello world.", result.finalText());
        assertEquals(2, result.transport().requests().size());
        // The second request must carry the tool's output back to the model.
        assertTrue(result.transport().requests().get(1).contains("hello world"));
    }

    @Test
    void appendsTheModelsOwnTurnBeforeTheToolResult() throws IOException {
        // The single most-forgotten line in this exercise. If the model's turn
        // isn't appended, the model never sees that it already asked, and asks
        // again forever.
        var result = run(
                FakeGeminiTransport.toolCallTurn("read_file", Map.of("path", "hello.txt")),
                FakeGeminiTransport.textTurn("done"));

        JsonNode contents = MAPPER.readTree(result.transport().requests().get(1)).get("contents");

        assertEquals(3, contents.size()); // user prompt, model turn, tool result
        assertEquals("user", contents.get(0).get("role").asText());
        assertEquals("model", contents.get(1).get("role").asText());
        assertTrue(contents.get(1).get("parts").get(0).has("functionCall"));
    }

    @Test
    void sendsToolResultsWithUserRole() throws IOException {
        // Not "tool", not "function". About 15% of pairs try one of those.
        var result = run(
                FakeGeminiTransport.toolCallTurn("read_file", Map.of("path", "hello.txt")),
                FakeGeminiTransport.textTurn("done"));

        JsonNode toolTurn = MAPPER.readTree(result.transport().requests().get(1)).get("contents").get(2);

        assertEquals("user", toolTurn.get("role").asText());
        assertTrue(toolTurn.get("parts").get(0).has("functionResponse"));
    }

    @Test
    void toolErrorsGoBackToTheModelAsStrings() {
        // A tool failure must not kill the loop — the model gets to read it and retry.
        var result = run(
                FakeGeminiTransport.toolCallTurn("read_file", Map.of("path", "nope.txt")),
                FakeGeminiTransport.textTurn("That file doesn't exist."));

        assertEquals("That file doesn't exist.", result.finalText());
        assertTrue(result.transport().requests().get(1).contains("ERROR:"));
        assertTrue(result.transport().requests().get(1).contains("does not exist"));
    }

    @Test
    void unknownToolIsReportedRatherThanThrown() {
        var result = run(
                FakeGeminiTransport.toolCallTurn("delete_everything", Map.of("path", ".")),
                FakeGeminiTransport.textTurn("I can't do that."));

        assertEquals("I can't do that.", result.finalText());
        assertTrue(result.transport().requests().get(1).contains("unknown tool"));
    }

    @Test
    void stopsAtMaxTurns() {
        // A model that never stops calling tools must not loop forever.
        String[] turns = new String[3];
        for (int i = 0; i < 3; i++) {
            turns[i] = FakeGeminiTransport.toolCallTurn("read_file", Map.of("path", "hello.txt"));
        }

        var transport = new FakeGeminiTransport(turns);
        var client = new GeminiClient("test-key", transport);
        var tools = new ReferenceTools(sandbox.toString());

        String finalText = AgentFactory.runAsync("loop forever", tools, client, "fake-model", 3).join();

        assertTrue(finalText.startsWith("ERROR:"));
        assertTrue(finalText.contains("did not finish within 3 turns"));
        assertEquals(3, transport.requests().size());
    }

    private static void deleteRecursively(Path path) throws IOException {
        if (!Files.exists(path)) return;
        try (var walk = Files.walk(path)) {
            walk.sorted(Comparator.reverseOrder()).forEach(p -> {
                try {
                    Files.delete(p);
                } catch (IOException ignored) {
                    // best-effort cleanup
                }
            });
        }
    }
}
