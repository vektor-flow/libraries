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
