/** A handful of math helpers. There is a bug here — on purpose. */
public final class MathUtils {

    private MathUtils() {}

    /** Compute n! — but this implementation is wrong for n == 0. */
    public static long factorial(int n) {
        if (n <= 0) {
            return 0; // BUG: 0! should be 1, not 0
        }

        long result = 1;
        for (int i = 1; i <= n; i++) {
            result *= i;
        }
        return result;
    }

    /** Return true if n is a prime number. */
    public static boolean isPrime(int n) {
        if (n < 2) return false;
        if (n == 2) return true;
        if (n % 2 == 0) return false;

        int i = 3;
        while ((long) i * i <= n) {
            if (n % i == 0) return false;
            i += 2;
        }
        return true;
    }

    /** Greatest common divisor via Euclid's algorithm. */
    public static int gcd(int a, int b) {
        while (b != 0) {
            int t = b;
            b = a % b;
            a = t;
        }
        return Math.abs(a);
    }
}
