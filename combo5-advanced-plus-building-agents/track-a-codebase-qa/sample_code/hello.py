"""Entry point for the TodoMagic reminder scheduler demo."""

from math_utils import factorial, is_prime


def greet(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greet("TodoMagic"))
    print(f"5! = {factorial(5)}")
    print(f"Is 17 prime? {is_prime(17)}")
