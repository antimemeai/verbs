#include <verbs/verbs.hpp>
#include <memory>

void expect(bool condition) {
    if (!condition) throw std::runtime_error("contract test failed");
}

int main() {
    for (int n = -10; n <= 10; ++n) {
        try {
            auto result = verbs::check("bounded", n, [](int n) { return n >= 1 && n <= 5; });
            expect(n >= 1 && n <= 5 && result == n);
        } catch (const verbs::violation& error) {
            expect(!(n >= 1 && n <= 5));
            expect(error.constraint == "bounded");
            expect(std::string(error.what()) == "constraint violated: bounded");
        }
    }
    int calls = 0;
    auto value = std::make_unique<int>(7);
    auto pointer = value.get();
    auto result = verbs::check("positive", std::move(value), [&](const auto& v) {
        ++calls;
        return *v > 0;
    });
    expect(result.get() == pointer && calls == 1);
    struct predicate_error {};
    bool propagated = false;
    try {
        verbs::check("broken", 0, [](int) -> bool { throw predicate_error{}; });
    } catch (const predicate_error&) { propagated = true; }
    expect(propagated);
}
