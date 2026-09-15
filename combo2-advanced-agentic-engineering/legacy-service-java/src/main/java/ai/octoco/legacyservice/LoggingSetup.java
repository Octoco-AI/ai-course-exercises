package ai.octoco.legacyservice;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

// LoggingSetup.java -- shared logging config for OrderBase.
//
// Log lines go to stdout AND logs/app-YYYY-MM-DD.log (when a logs/ dir
// exists in the working directory -- prod boxes have one, CI doesn't).
// The format is FROZEN: the metrics pusher (see DOCS/INSTRUCTIONS.md)
// greps these lines every minute. Change it and the dashboards go dark.
//
// Hand-rolled on purpose -- no SLF4J, no Logback, no DI. getLogger(name)
// mirrors the stdlib logging.getLogger(name) call in the Python original.

public final class LoggingSetup {

    private static final String LOG_DIR = "logs";
    private static final DateTimeFormatter FILE_DATE =
            DateTimeFormatter.ofPattern("yyyy-MM-dd", Locale.ROOT);
    private static final DateTimeFormatter LINE_TIMESTAMP =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss,SSS", Locale.ROOT);

    private static boolean configured;
    private static PrintWriter fileWriter;

    private LoggingSetup() {}

    public static synchronized void setup() {
        if (configured) {
            return;
        }
        Path logDir = Path.of(LOG_DIR);
        if (Files.isDirectory(logDir)) {
            String fname = "app-" + LocalDateTime.now().format(FILE_DATE) + ".log";
            try {
                fileWriter = new PrintWriter(new FileWriter(logDir.resolve(fname).toFile(), true), true);
            } catch (IOException e) {
                // If the log file can't be opened, keep going with stdout only --
                // same as the C# port silently accepting a missing logs/ dir.
                fileWriter = null;
            }
        }
        configured = true;
    }

    public static Logger getLogger(String name) {
        return new Logger(name);
    }

    static synchronized void emit(String level, String name, String line) {
        String ts = LocalDateTime.now().format(LINE_TIMESTAMP);
        String full = ts + " " + level + " " + name + " " + line;
        System.out.println(full);
        if (fileWriter != null) {
            fileWriter.println(full);
        }
    }
}
