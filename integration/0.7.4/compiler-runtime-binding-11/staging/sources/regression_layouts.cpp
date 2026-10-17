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


// Review04 supplement: real entry points and independently specified outcomes.
// UNEXECUTED. The whole-record cases are expected to FAIL candidate 8ff80f95.
static void review04_negative_controls() {
    const ValueLayout num{};
    const ValueLayout str{2, ValueKind::String, {}};
    const auto counted = dynamic_list_layout(num);
    const auto three = indexed_layout(std::vector<ValueLayout>(3, num));
    const auto check = [](const ValueLayout& initial, const ValueLayout& actual,
                          const char* label, bool check_merge = true) {
        auto full = initial;
        refine_full_projection_path(full, actual, {}, 0);
        require(same_inference_layout(full, actual), label);
        if (check_merge) {
            auto merged = initial;
            merge_inferred_layout(merged, actual);
            require(same_inference_layout(merged, actual), label);
        }
    };
    // These malformed/noncanonical layouts must keep the previous substitution
    // outcome; this does NOT assert that the compiler accepts them as programs.
    auto bad = three;
    bad.width += 1;
    check(counted, bad, "wrong total width was certified");
    bad = three; bad.selectors["1"].offset = 0;
    check(counted, bad, "overlapping selectors were certified");
    bad = three; bad.selectors["1"].offset = 3;
    check(counted, bad, "gapped selectors were certified");
    bad = three; bad.selectors["0.ghost"] = ValueSlice{};
    check(counted, bad, "extra descendant was certified");
    bad = three; bad.selectors["99.ghost"] = ValueSlice{};
    check(counted, bad, "orphan descendant was certified");
    bad = ValueLayout{3, ValueKind::Aggregate, {}};
    bad.selectors["00"] = {0, 1, ValueKind::Numeric};
    bad.selectors["1"] = {1, 1, ValueKind::Numeric};
    bad.selectors["2"] = {2, 1, ValueKind::Numeric};
    check(counted, bad, "noncanonical numeric selector was certified");
    bad = three; bad.tuple_leaf = true;
    check(counted, bad, "tuple actual was certified");
    bad = three; bad.shared_element_count = 3;
    check(counted, bad, "shared actual was certified");
    bad = three; bad.concurrent_handle_kind = ConcurrentHandleKind::Queue;
    check(counted, bad, "channel-tagged actual was certified");
    bad = three; bad.dynamic_element = std::make_shared<ValueLayout>(num);
    check(counted, bad, "aggregate with dynamic element was certified");
    check(counted, indexed_layout({ValueLayout{2, ValueKind::Complex, {}}}),
          "complex-vector actual was swallowed");
    check(counted, indexed_layout({str}), "String actual matched Numeric ABI");
    check(dynamic_list_layout(str), three, "Numeric actual matched String ABI");
    check(counted, indexed_layout({ValueLayout{2, ValueKind::Numeric, {}}}),
          "wrong primitive width was certified");
    ValueLayout record{0, ValueKind::Aggregate, {}};
    assign_record_field_layout(record, "value", num);
    check(counted, record, "record actual was certified", false);
    check(counted, indexed_layout({record, record, record}),
          "record-element vector was certified");
    check(counted, ValueLayout{1, ValueKind::SharedNumericVector, {}},
          "shared-vector kind was certified", false);
    ValueLayout channel{1, ValueKind::ConcurrentHandle, {}};
    channel.concurrent_handle_kind = ConcurrentHandleKind::Queue;
    check(counted, channel, "channel kind was certified", false);
    auto current = counted; current.width = 2;
    check(current, three, "malformed counted width was certified");
    current = counted; current.selectors["unexpected"] = ValueSlice{};
    check(current, three, "counted selectors were certified");
    current = counted; current.tuple_leaf = true;
    check(current, three, "tuple-tagged counted storage was certified");
    current = counted; current.shared_element_count = 1;
    check(current, three, "shared counted storage was certified");
    current = counted; current.concurrent_handle_kind = ConcurrentHandleKind::Queue;
    check(current, three, "channel counted storage was certified");
    // Construct explicit elements directly: dynamic_list_layout canonicalizes Num.
    for (int defect = 0; defect != 6; ++defect) {
        current = counted;
        auto element = num;
        if (defect == 0) element.width = 2;
        if (defect == 1) element.selectors["unexpected"] = ValueSlice{};
        if (defect == 2) element.dynamic_element = std::make_shared<ValueLayout>(num);
        if (defect == 3) element.tuple_leaf = true;
        if (defect == 4) element.shared_element_count = 1;
        if (defect == 5) element.concurrent_handle_kind = ConcurrentHandleKind::Queue;
        current.dynamic_element = std::make_shared<ValueLayout>(element);
        check(current, three, "malformed counted element was certified");
    }
    current = counted;
    current.dynamic_element = std::make_shared<ValueLayout>(num);
    auto merged = current;
    merge_inferred_layout(merged, three);
    require(same_inference_layout(merged, current), "explicit Numeric element lost");
    refine_full_projection_path(merged, three, {}, 0);
    require(same_inference_layout(merged, current), "explicit Numeric full demand lost");
    require(!counted.dynamic_element, "canonical Numeric element is not null");
    // A fixed formal must still substitute exactly, including the empty actual.
    for (int extent : {0, 1}) {
        const auto actual = indexed_layout(std::vector<ValueLayout>(extent, num));
        FunctionSignature fixed;
        fixed.parameters.push_back(three);
        fixed.parameter_type_names.push_back("[num:3]");
        refine_signature_parameter_full_projection_paths(fixed, 0, actual, {""});
        refine_signature_parameter_from_argument(fixed, 0, actual);
        require(same_inference_layout(fixed.parameters[0], actual),
                "fixed formal no longer substitutes exact full demand");
    }
    // The existing counted-to-counted numeric promotion must still be visible.
    auto promoted = counted;
    const auto complex = dynamic_list_layout(ValueLayout{2, ValueKind::Complex, {}});
    merge_inferred_layout(promoted, complex);
    require(same_inference_layout(promoted, complex), "counted promotion changed");
}

static void review04_record_projection_cases() {
    const ValueLayout num{};
    const ValueLayout str{2, ValueKind::String, {}};
    const auto declared = metadata(dynamic_list_layout(num), dynamic_list_layout(str));
    int failures = 0;
    const auto wrap = [](const ValueLayout& child) {
        ValueLayout result{0, ValueKind::Aggregate, {}};
        assign_record_field_layout(result, "metadata", child);
        assign_record_field_layout(result, "tail", ValueLayout{2, ValueKind::String, {}});
        return result;
    };
    // mode0: empty path selecting whole Metadata; mode1: terminal metadata record;
    // mode2: empty path selecting an enclosing record with nested Metadata.
    const auto check = [&](const ValueLayout& initial, const ValueLayout& actual,
                           const ValueLayout& expected, int extent, int sibling) {
        for (int mode = 0; mode != 3; ++mode) {
            FunctionSignature signature;
            signature.parameters.push_back(mode ? wrap(initial) : initial);
            const auto supplied = mode ? wrap(actual) : actual;
            const auto wanted = mode ? wrap(expected) : expected;
            refine_signature_parameter_full_projection_paths(
                signature, 0, supplied, {mode == 1 ? "metadata" : ""});
            const bool full_ok = same_inference_layout(signature.parameters[0], wanted);
            refine_signature_parameter_from_argument(signature, 0, supplied);
            const bool call_ok = same_inference_layout(signature.parameters[0], wanted);
            if (!full_ok || !call_ok) {
                ++failures;
                std::cerr << "record projection failed: mode=" << mode
                          << " vector_extent=" << extent << " sibling_extent=" << sibling
                          << " full_ok=" << full_ok << " call_ok=" << call_ok << '\n';
            }
        }
    };
    for (int extent : {0, 1, 9}) {
        const auto actual = metadata(
            indexed_layout(std::vector<ValueLayout>(extent, num)),
            indexed_layout(std::vector<ValueLayout>(extent, str)));
        check(declared, actual, declared, extent, -1);
        for (int sibling : {0, 1}) {
            auto initial = declared, supplied = actual, expected = declared;
            assign_record_field_layout(initial, "fixed",
                indexed_layout(std::vector<ValueLayout>(3, num)));
            const auto narrow = indexed_layout(std::vector<ValueLayout>(sibling, num));
            assign_record_field_layout(supplied, "fixed", narrow);
            assign_record_field_layout(expected, "fixed", narrow);
            check(initial, supplied, expected, extent, sibling);
        }
    }
    require(failures == 0, "whole-record counted storage regression");
}

// Repair05 additions. Real compiler entry points; UNEXECUTED until native grant.
static void repair05_record_controls() {
    const ValueLayout num{};
    const ValueLayout str{2, ValueKind::String, {}};
    const auto declared = metadata(dynamic_list_layout(num), dynamic_list_layout(str));
    const auto actual = metadata(indexed_layout({num}), indexed_layout({str}));
    const auto exact = [](const ValueLayout& initial, const ValueLayout& supplied,
                          const char* message) {
        auto result = initial;
        refine_full_projection_path(result, supplied, {}, 0);
        require(same_inference_layout(result, supplied), message);
    };
    // Invalid record boundaries must not certify otherwise eligible children.
    for (int side = 0; side != 2; ++side) {
        for (int defect = 0; defect != 8; ++defect) {
            auto initial = declared, supplied = actual;
            auto& bad = side ? supplied : initial;
            if (defect == 0) ++bad.width;
            if (defect == 1) ++bad.selectors["texts"].offset;
            if (defect == 2) bad.selectors["orphan.child"] = ValueSlice{};
            if (defect == 3) bad.tuple_leaf = true;
            if (defect == 4) bad.shared_element_count = 1;
            if (defect == 5) bad.concurrent_handle_kind = ConcurrentHandleKind::Queue;
            if (defect == 6) bad.dynamic_element = std::make_shared<ValueLayout>(num);
            if (defect == 7) bad.selectors["count"].offset = 0;
            exact(initial, supplied, "invalid record boundary preserved counted children");
        }
    }
    auto extra = actual;
    assign_record_field_layout(extra, "extra", num);
    exact(declared, extra, "new field incorrectly accepted as matching record structure");
    extra = declared;
    assign_record_field_layout(extra, "extra", num);
    exact(extra, actual, "removed field incorrectly retained during projection");

    // Record-element vectors are not traversed by the new record overlay.
    exact(indexed_layout({declared}), indexed_layout({actual}),
          "record-element vector changed replacement behavior");
    exact(dynamic_list_layout(declared), indexed_layout({actual}),
          "counted record-element vector changed replacement behavior");

    // A late malformed nested record must discard earlier local child changes.
    // The field names force the eligible child to be visited before the failure.
    auto nested_bad = actual;
    ++nested_bad.width;
    ValueLayout initial{0, ValueKind::Aggregate, {}}, supplied{0, ValueKind::Aggregate, {}};
    assign_record_field_layout(initial, "a", dynamic_list_layout(str));
    assign_record_field_layout(initial, "z", declared);
    assign_record_field_layout(supplied, "a", indexed_layout({str}));
    assign_record_field_layout(supplied, "z", nested_bad);
    exact(initial, supplied, "failed nested validation leaked a partial overlay");

    // Unsupported child ABI still substitutes exactly while an independent
    // valid counted child is retained; no numeric conversion is introduced.
    auto cross = metadata(indexed_layout({str}), indexed_layout({str}));
    auto expected = metadata(indexed_layout({str}), dynamic_list_layout(str));
    auto result = declared;
    refine_full_projection_path(result, cross, {}, 0);
    require(same_inference_layout(result, expected), "cross-ABI child was preserved");
    cross = metadata(indexed_layout({ValueLayout{2, ValueKind::Complex, {}}}),
                     indexed_layout({str}));
    expected = metadata(indexed_layout({ValueLayout{2, ValueKind::Complex, {}}}),
                        dynamic_list_layout(str));
    result = declared;
    refine_full_projection_path(result, cross, {}, 0);
    require(same_inference_layout(result, expected), "numeric conversion acceptance changed");

    // With no eligible counted child the complete actual stays exact, including
    // a changed field order and fixed extent.
    initial = ValueLayout{0, ValueKind::Aggregate, {}};
    supplied = ValueLayout{0, ValueKind::Aggregate, {}};
    assign_record_field_layout(initial, "first", indexed_layout({num, num, num}));
    assign_record_field_layout(initial, "last", num);
    assign_record_field_layout(supplied, "last", num);
    assign_record_field_layout(supplied, "first", indexed_layout({}));
    exact(initial, supplied, "unrelated fixed record no longer substitutes exactly");

    // Existing numeric compatibility still retains a wider ABI at equal shape.
    initial = metadata(ValueLayout{2, ValueKind::Complex, {}}, dynamic_list_layout(str));
    supplied = metadata(num, dynamic_list_layout(str));
    result = initial;
    refine_full_projection_path(result, supplied, {}, 0);
    require(same_inference_layout(result, initial), "numeric compatibility branch changed");
}

static void repair05_canonical_and_alias_controls() {
    const ValueLayout num{};
    const ValueLayout str{2, ValueKind::String, {}};
    // Explicit Numeric pointer must remain explicit; snapshots share both the
    // SelectorMap and element pointers. Expected values are built independently.
    const auto make_declared = [&]() {
        auto counted_num = dynamic_list_layout(num);
        counted_num.dynamic_element = std::make_shared<ValueLayout>(num);
        auto record = metadata(counted_num, dynamic_list_layout(str));
        assign_record_field_layout(record, "fixed", indexed_layout({num, num, num}));
        return record;
    };
    auto initial = make_declared();
    const auto snapshot = initial;
    const auto numeric_element = initial.selectors.at("numbers").dynamic_element;
    const auto string_element = initial.selectors.at("texts").dynamic_element;
    auto supplied = metadata(indexed_layout({num, num, num}), indexed_layout({str, str, str}));
    assign_record_field_layout(supplied, "fixed", indexed_layout({}));
    const auto supplied_snapshot = supplied;
    auto expected = make_declared();
    assign_record_field_layout(expected, "fixed", indexed_layout({}));
    refine_full_projection_path(initial, supplied, {}, 0);
    require(same_inference_layout(initial, expected), "canonical mixed result differs");
    require(same_inference_layout(snapshot, make_declared()), "shared input snapshot mutated");
    auto original_actual = metadata(indexed_layout({num, num, num}), indexed_layout({str, str, str}));
    assign_record_field_layout(original_actual, "fixed", indexed_layout({}));
    require(same_inference_layout(supplied, original_actual) &&
            same_inference_layout(supplied_snapshot, original_actual), "candidate snapshot mutated");
    require(snapshot.selectors.at("numbers").dynamic_element == numeric_element &&
            initial.selectors.at("numbers").dynamic_element == numeric_element &&
            same_inference_layout(*numeric_element, num), "Numeric pointer aliased mutation");
    require(snapshot.selectors.at("texts").dynamic_element == string_element &&
            initial.selectors.at("texts").dynamic_element == string_element &&
            same_inference_layout(*string_element, str), "String pointer aliased mutation");
    require(initial.width == 3 && initial.selectors.at("numbers").offset == 0 &&
            initial.selectors.at("texts").offset == 1 &&
            initial.selectors.at("count").offset == 2 &&
            initial.selectors.at("fixed").offset == 3,
            "rebuilt offsets retain fixed candidate widths");
    require(!initial.selectors.shares_storage(snapshot.selectors), "result selectors not detached");
    refine_full_projection_path(initial, initial, {}, 0);
    require(same_inference_layout(initial, expected), "self-alias projection changed layout");

    // A newly empty fixed sibling can share its offset with a later counted
    // field. Canonical reconstruction must preserve both named slices.
    ValueLayout middle{0, ValueKind::Aggregate, {}};
    assign_record_field_layout(middle, "numbers", dynamic_list_layout(num));
    assign_record_field_layout(middle, "fixed", indexed_layout({num, num, num}));
    assign_record_field_layout(middle, "texts", dynamic_list_layout(str));
    auto middle_expected = middle;
    assign_record_field_layout(middle_expected, "fixed", indexed_layout({}));
    ValueLayout middle_actual{0, ValueKind::Aggregate, {}};
    assign_record_field_layout(middle_actual, "numbers", indexed_layout({num}));
    assign_record_field_layout(middle_actual, "fixed", indexed_layout({}));
    assign_record_field_layout(middle_actual, "texts", indexed_layout({str}));
    refine_full_projection_path(middle, middle_actual, {}, 0);
    require(same_inference_layout(middle, middle_expected) &&
            middle.selectors.at("fixed").offset == 1 &&
            middle.selectors.at("texts").offset == 1,
            "empty middle sibling damaged canonical offsets");

    // When preserving counted children, retain the established record field order
    // even if the supplied record arrives with a different physical order.
    ValueLayout reordered{0, ValueKind::Aggregate, {}}, reordered_expected{0, ValueKind::Aggregate, {}};
    assign_record_field_layout(reordered, "count", num);
    assign_record_field_layout(reordered, "texts", indexed_layout({str, str, str}));
    assign_record_field_layout(reordered, "numbers", indexed_layout({num}));
    assign_record_field_layout(reordered, "fixed", indexed_layout({num}));
    auto explicit_num = dynamic_list_layout(num);
    explicit_num.dynamic_element = std::make_shared<ValueLayout>(num);
    assign_record_field_layout(reordered_expected, "numbers", explicit_num);
    assign_record_field_layout(reordered_expected, "texts", dynamic_list_layout(str));
    assign_record_field_layout(reordered_expected, "count", num);
    assign_record_field_layout(reordered_expected, "fixed", indexed_layout({num}));
    initial = make_declared();
    refine_full_projection_path(initial, reordered, {}, 0);
    require(same_inference_layout(initial, reordered_expected), "established order/offsets changed");
}

int main() {
    repair05_record_controls();
    repair05_canonical_and_alias_controls();
    review04_negative_controls();
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
    review04_record_projection_cases();
    std::cout << "ordinary counted metadata layout regressions passed\n";
}
