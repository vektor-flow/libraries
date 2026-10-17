from pathlib import Path
import difflib
here = Path(__file__).resolve().parent
source = here.parent / 'compiler-renderer-repair-02/regression_layouts.cpp'
old = source.read_text()
addition = r'''
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
'''
new = old.replace('int main() {', addition + '\nint main() {\n    review04_negative_controls();', 1)
new = new.replace('    std::cout << "ordinary counted metadata layout regressions passed', '    review04_record_projection_cases();\n    std::cout << "ordinary counted metadata layout regressions passed', 1)
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/integration/0.7.4/compiler-renderer-repair-02/regression_layouts.cpp',tofile='b/integration/0.7.4/compiler-renderer-repair-02/regression_layouts.cpp'))
(here/'regression-supplement.patch').write_text(patch)
# Do not apply to reviewed source. Keep proposed executable source for review only.
(here/'regression_layouts_supplemented.cpp').write_text(new)
print('Prepared proposal only:', len(patch), 'bytes;', len(new.splitlines()), 'source lines')
