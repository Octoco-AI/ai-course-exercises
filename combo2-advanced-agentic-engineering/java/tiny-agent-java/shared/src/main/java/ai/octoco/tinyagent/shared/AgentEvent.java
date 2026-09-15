package ai.octoco.tinyagent.shared;

/**
 * What the agent loop reports as it runs. GIVEN — you don't write this.
 *
 * <p>The observer hook exists so later modules have somewhere to attach: M12
 * (CI/CD/CE) traces from here, and M16 (context engineering) counts tokens
 * from here. Keep calling {@code onEvent} from your loop even when nothing is
 * listening.
 */
public sealed interface AgentEvent {

    record TurnStart(int turn) implements AgentEvent {}

    record ToolCall(String name, String argsPreview) implements AgentEvent {}

    record ToolResult(String name, String result) implements AgentEvent {}

    record Final(String text, int turns) implements AgentEvent {}
}
