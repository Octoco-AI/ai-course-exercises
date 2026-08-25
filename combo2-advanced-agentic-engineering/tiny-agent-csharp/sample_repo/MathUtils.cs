namespace SampleRepo;

/// <summary>A handful of math helpers. There is a bug here — on purpose.</summary>
public static class MathUtils
{
    /// <summary>Compute n! — but this implementation is wrong for n == 0.</summary>
    public static long Factorial(int n)
    {
        if (n <= 0)
        {
            return 0; // BUG: 0! should be 1, not 0
        }

        long result = 1;
        for (var i = 1; i <= n; i++)
        {
            result *= i;
        }
        return result;
    }

    /// <summary>Return true if n is a prime number.</summary>
    public static bool IsPrime(int n)
    {
        if (n < 2) return false;
        if (n == 2) return true;
        if (n % 2 == 0) return false;

        var i = 3;
        while (i * i <= n)
        {
            if (n % i == 0) return false;
            i += 2;
        }
        return true;
    }

    /// <summary>Greatest common divisor via Euclid's algorithm.</summary>
    public static int Gcd(int a, int b)
    {
        while (b != 0)
        {
            (a, b) = (b, a % b);
        }
        return Math.Abs(a);
    }
}
