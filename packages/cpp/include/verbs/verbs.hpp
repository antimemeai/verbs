#pragma once

#include <functional>
#include <stdexcept>
#include <string>
#include <utility>

namespace verbs {

class violation : public std::runtime_error {
public:
    const std::string constraint;

    explicit violation(std::string name)
        : std::runtime_error("constraint violated: " + name),
          constraint(std::move(name)) {}
};

// Check an owned value once, then return it by value. Predicate errors propagate.
// Taking the value by value prevents returning a reference to a temporary.
template <typename T, typename Predicate>
T check(std::string name, T value, Predicate&& predicate) {
    if (!std::invoke(std::forward<Predicate>(predicate), std::as_const(value))) {
        throw violation(std::move(name));
    }
    return value;
}

} // namespace verbs
