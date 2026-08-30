/** A handful of math helpers. There is a bug here — on purpose. */

/** Compute n! — but this implementation is wrong for n === 0. */
export function factorial(n: number): number {
  if (n <= 0) {
    return 0; // BUG: 0! should be 1, not 0
  }

  let result = 1;
  for (let i = 1; i <= n; i += 1) {
    result *= i;
  }
  return result;
}

/** Return true if n is a prime number. */
export function isPrime(n: number): boolean {
  if (n < 2) return false;
  if (n === 2) return true;
  if (n % 2 === 0) return false;

  let i = 3;
  while (i * i <= n) {
    if (n % i === 0) return false;
    i += 2;
  }
  return true;
}

/** Greatest common divisor via Euclid's algorithm. */
export function gcd(a: number, b: number): number {
  while (b !== 0) {
    [a, b] = [b, a % b];
  }
  return Math.abs(a);
}
