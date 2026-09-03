using System.Globalization;

namespace LegacyService;

// LoggingSetup.cs -- shared logging config for OrderBase.
//
// Log lines go to stdout AND logs/app-YYYY-MM-DD.log (when a logs/ dir
// exists in the working directory -- prod boxes have one, CI doesn't).
// The format is FROZEN: the metrics pusher (see DOCS/INSTRUCTIONS.md)
// greps these lines every minute. Change it and the dashboards go dark.
//
// Hand-rolled on purpose -- no ILogger<T>, no DI. `GetLogger(name)` mirrors
// the stdlib `logging.getLogger(name)` call in the Python original.

public static class LoggingSetup
{
    private const string LogDir = "logs";
    private static bool _configured;
    private static StreamWriter? _fileWriter;

    public static void Setup()
    {
        if (_configured)
        {
            return;
        }
        if (Directory.Exists(LogDir))
        {
            var fname = Path.Combine(LogDir, $"app-{DateTime.Now.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)}.log");
            _fileWriter = new StreamWriter(fname, append: true) { AutoFlush = true };
        }
        _configured = true;
    }

    public static Logger GetLogger(string name) => new(name);

    internal static void Emit(string level, string name, string line)
    {
        var ts = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss,fff", CultureInfo.InvariantCulture);
        var full = $"{ts} {level} {name} {line}";
        Console.WriteLine(full);
        _fileWriter?.WriteLine(full);
    }
}

public class Logger
{
    private readonly string _name;

    internal Logger(string name)
    {
        _name = name;
    }

    public void Info(string message, params object?[] args)
        => LoggingSetup.Emit("INFO", _name, Format(message, args));

    public void Warning(string message, params object?[] args)
        => LoggingSetup.Emit("WARNING", _name, Format(message, args));

    private static string Format(string message, object?[] args)
        => args.Length > 0 ? string.Format(CultureInfo.InvariantCulture, message, args) : message;
}
