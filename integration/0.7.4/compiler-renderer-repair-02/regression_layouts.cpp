// UNEXECUTED native regression. Link the real authenticated compiler core;
// no replacement implementations, allocator changes, or source stubs.
#include "compiler/native/vkf_value_layout.hpp"
#include <algorithm>
#include <iostream>
#include <stdexcept>

using namespace vkf::machine_ir;
using namespace vkf::machine_ir::detail;

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

static ValueLayout metadata(const ValueLayout& numbers, const ValueLayout& texts) {
    ValueLayout out{0, ValueKind::Aggregate, {}};
    assign_record_field_layout(out, "numbers", numbers);
    assign_record_field_layout(out, "texts", texts);
    assign_record_field_layout(out, "count", ValueLayout{});
    return out;
}

int main() {
    const ValueLayout numeric{};
    const ValueLayout string{2, ValueKind::String, {}};
    const auto counted_num = dynamic_list_layout(numeric);
    const auto counted_string = dynamic_list_layout(string);
    const auto declared = metadata(counted_num, counted_string);
    const std::vector<ValueLayout> actuals{
        metadata(indexed_layout({}), indexed_layout({})),
        metadata(indexed_layout(std::vector<ValueLayout>(1, numeric)),
                 indexed_layout(std::vector<ValueLayout>(1, string))),
        metadata(indexed_layout(std::vector<ValueLayout>(9, numeric)),
                 indexed_layout(std::vector<ValueLayout>(9, string))),
        declared
    };
    std::vector<int> order{0, 1, 2, 3};
    do {
        FunctionSignature signature;
        signature.parameters.push_back(declared);
        for (int index : order) {
            // This is the real ordinary-call ordering in core53/core56.
            refine_signature_parameter_full_projection_paths(
                signature, 0, actuals[index], {"numbers", "texts", "count"});
            refine_signature_parameter_from_argument(signature, 0, actuals[index]);
            require(same_inference_layout(signature.parameters[0], declared),
                    "ordinary call narrowed a counted metadata field");
        }
        auto result = declared;
        for (int index : order) {
            merge_inferred_layout(result, actuals[index]);
            require(same_inference_layout(result, declared),
                    "ordinary record result narrowed counted storage");
        }
    } while (std::next_permutation(order.begin(), order.end()));

    // Explicit fixed extents remain fixed; the new proof must not convert them.
    auto fixed_nine = indexed_layout(std::vector<ValueLayout>(9, numeric));
    const auto one = indexed_layout(std::vector<ValueLayout>(1, numeric));
    auto fixed_merged = fixed_nine;
    merge_inferred_layout(fixed_merged, one);
    require(same_inference_layout(fixed_merged, fixed_nine), "fixed merge changed");
    refine_full_projection_path(fixed_merged, one, {}, 0);
    require(same_inference_layout(fixed_merged, one), "fixed full demand changed");
    // Numeric widening remains an independent existing behavior.
    ValueLayout promoted{};
    merge_inferred_layout(promoted, ValueLayout{2, ValueKind::Complex, {}});
    require(promoted.kind == ValueKind::Complex && promoted.width == 2,
            "numeric promotion changed");
    std::cout << "ordinary counted metadata layout regressions passed\n";
}
