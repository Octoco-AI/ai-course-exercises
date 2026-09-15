package ai.octoco.tinyagent.tests;

import ai.octoco.tinyagent.reference.ReferenceTools;
import ai.octoco.tinyagent.shared.Tools;
import ai.octoco.tinyagent.starter.StarterTools;

/** The tool implementation under test. See {@link Impl} for the switch. */
final class ToolsFactory {

    private ToolsFactory() {}

    static Tools create(String sandboxRoot) {
        return "reference".equals(Impl.selected())
                ? new ReferenceTools(sandboxRoot)
                : new StarterTools(sandboxRoot);
    }

    static String describe() {
        return "reference".equals(Impl.selected()) ? "reference (worked solution)" : "starter (your code)";
    }
}
