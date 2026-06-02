"""A handful of math helpers. There is a bug here — on purpose."""


def factorial(n: int) -> int:
    """Compute n! — but this implementation is wrong for n == 0."""
    if n <= 0:
        return 0  # BUG: 0! should be 1, not 0
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def is_prime(n: int) -> bool:
    """Return True if n is a prime number."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def gcd(a: int, b: int) -> int:
    """Greatest common divisor via Euclid's algorithm."""
    while b:
        a, b = b, a % b
    return abs(a)
