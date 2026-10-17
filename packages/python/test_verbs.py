import unittest

from verbs_agent import Violation, check


class CheckTests(unittest.TestCase):
    def test_allowed_range(self):
        for n in range(-10, 11):
            if 1 <= n <= 5:
                self.assertEqual(check("bounded", n, lambda n: 1 <= n <= 5), n)
            else:
                with self.assertRaises(Violation) as caught:
                    check("bounded", n, lambda n: 1 <= n <= 5)
                self.assertEqual(caught.exception.constraint, "bounded")
                self.assertEqual(str(caught.exception), "constraint violated: bounded")

    def test_original_value_and_one_evaluation(self):
        value = []
        calls = []

        def predicate(v):
            calls.append(v)
            return True

        self.assertIs(check("same", value, predicate), value)
        self.assertEqual(len(calls), 1)

    def test_errors_propagate_and_truthy_nonbooleans_fail(self):
        error = RuntimeError("predicate failed")

        def broken(_):
            raise error

        with self.assertRaises(RuntimeError) as caught:
            check("broken", 0, broken)
        self.assertIs(caught.exception, error)
        for invalid in [1, "true", [], {}, None]:
            with self.assertRaises(Violation):
                check("boolean", 0, lambda _: invalid)


if __name__ == "__main__":
    unittest.main()
