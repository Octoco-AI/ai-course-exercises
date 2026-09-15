package ai.octoco.legacyservice;

/** A named logger handle, as returned by {@link LoggingSetup#getLogger(String)}. */
public final class Logger {

    private final String name;

    Logger(String name) {
        this.name = name;
    }

    public void info(String message) {
        LoggingSetup.emit("INFO", name, message);
    }

    public void warning(String message) {
        LoggingSetup.emit("WARNING", name, message);
    }
}
