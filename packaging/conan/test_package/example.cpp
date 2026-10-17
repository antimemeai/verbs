#include <verbs/verbs.hpp>

int main() {
    auto result = verbs::check("positive", 3, [](int n) { return n > 0; });
    if (result != 3) return 1;
    try {
        verbs::check("positive", -1, [](int n) { return n > 0; });
        return 2;
    } catch (const verbs::violation& error) {
        return error.constraint == "positive" ? 0 : 3;
    }
}
