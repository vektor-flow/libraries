#include "compiler/native/vkf_value_layout.hpp"

namespace vkf::machine_ir::detail {
ValueLayout dynamic_list_layout(ValueLayout element ) {
    ValueLayout layout{1, ValueKind::DynamicF64List, {}};
    if (element.width == 1 && element.kind == ValueKind::Numeric &&
        element.selectors.empty()) return layout;
    layout.dynamic_element = std::make_shared<ValueLayout>(std::move(element));
    return layout;
}
}

namespace vkf::machine_ir::detail {
DisplayShape shallow_display_shape(const vf::JsonValue::Object& expression) {
    const auto kind = expression.find("kind");
    if (kind != expression.end() && kind->second.is_string()) {
        if (kind->second.as_string() == "complex_const") {
            return {DisplayKind::Complex, {}};
        }
        if (kind->second.as_string() == "call") {
            const auto callee = expression.find("callee");
            const auto args = expression.find("args");
            if (callee != expression.end() && callee->second.is_object() &&
                args != expression.end() && args->second.is_array() &&
                args->second.as_array().size() == 2) {
                const auto& callee_object = callee->second.as_object();
                const auto callee_kind = callee_object.find("kind");
                const auto callee_name = callee_object.find("name");
                if (callee_kind != callee_object.end() && callee_kind->second.is_string() &&
                    callee_kind->second.as_string() == "load" &&
                    callee_name != callee_object.end() && callee_name->second.is_string() &&
                    callee_name->second.as_string() == "num") {
                    return {DisplayKind::Complex, {}};
                }
            }
        }
        if (kind->second.as_string() == "const") {
            const auto value = expression.find("value");
            if (value != expression.end()) {
                if (value->second.is_string()) return {DisplayKind::String, {}};
                if (value->second.is_boolean()) return {DisplayKind::Bit, {}};
                if (value->second.is_null()) return {DisplayKind::Null, {}};
            }
        }
    }
    const auto type = expression.find("type");
    if (type != expression.end() && type->second.is_string()) {
        if (type->second.as_string() == "str") return {DisplayKind::String, {}};
        if (type->second.as_string() == "chr") return {DisplayKind::Chr, {}};
        if (type->second.as_string() == "bit") return {DisplayKind::Bit, {}};
        if (type->second.as_string() == "null") return {DisplayKind::Null, {}};
        if (type->second.as_string() == "range<int>") return {DisplayKind::Range, {}};
    }
    return {DisplayKind::F64, {}};
}
}

namespace vkf::machine_ir::detail {
std::uint32_t display_width(const DisplayShape& shape) {
    if (shape.kind == DisplayKind::String) return 2;
    if (shape.kind == DisplayKind::Complex) return 2;
    if (shape.kind == DisplayKind::Range) return 3;
    if (shape.kind == DisplayKind::F64 || shape.kind == DisplayKind::Chr ||
        shape.kind == DisplayKind::Bit ||
        shape.kind == DisplayKind::Multiset ||
        shape.kind == DisplayKind::Null) return 1;
    std::uint32_t width = 0;
    for (const auto& child : shape.children) width += display_width(child.second);
    return width;
}
}

namespace vkf::machine_ir::detail {
bool same_layout(const ValueLayout& left, const ValueLayout& right) {
    if (left.width != right.width || left.kind != right.kind ||
        left.shared_element_count != right.shared_element_count ||
        left.concurrent_handle_kind != right.concurrent_handle_kind ||
        left.selectors.size() != right.selectors.size()) return false;
    if (static_cast<bool>(left.dynamic_element) !=
        static_cast<bool>(right.dynamic_element)) return false;
    if (left.dynamic_element &&
        !same_layout(*left.dynamic_element, *right.dynamic_element)) return false;
    if (left.selectors.shares_storage(right.selectors)) return true;
    auto left_field = left.selectors.begin();
    auto right_field = right.selectors.begin();
    for (; left_field != left.selectors.end(); ++left_field, ++right_field) {
        if (left_field->first != right_field->first ||
            left_field->second.offset != right_field->second.offset ||
            left_field->second.width != right_field->second.width ||
            left_field->second.kind != right_field->second.kind ||
            left_field->second.shared_element_count !=
                right_field->second.shared_element_count ||
            left_field->second.concurrent_handle_kind !=
                right_field->second.concurrent_handle_kind) return false;
        if (static_cast<bool>(left_field->second.dynamic_element) !=
            static_cast<bool>(right_field->second.dynamic_element)) return false;
        if (left_field->second.dynamic_element &&
            !same_layout(*left_field->second.dynamic_element,
                         *right_field->second.dynamic_element)) return false;
    }
    return true;
}
}

namespace vkf::machine_ir::detail {
bool same_inference_layout(const ValueLayout& left, const ValueLayout& right) {
    if (left.width != right.width || left.kind != right.kind || left.tuple_leaf != right.tuple_leaf ||
        left.shared_element_count != right.shared_element_count ||
        left.concurrent_handle_kind != right.concurrent_handle_kind ||
        left.selectors.size() != right.selectors.size()) return false;
    if (static_cast<bool>(left.dynamic_element) !=
        static_cast<bool>(right.dynamic_element)) return false;
    if (left.dynamic_element &&
        !same_inference_layout(*left.dynamic_element, *right.dynamic_element)) return false;
    if (left.selectors.shares_storage(right.selectors)) return true;
    auto left_field = left.selectors.begin();
    auto right_field = right.selectors.begin();
    for (; left_field != left.selectors.end(); ++left_field, ++right_field) {
        if (left_field->first != right_field->first ||
            left_field->second.offset != right_field->second.offset ||
            left_field->second.width != right_field->second.width ||
            left_field->second.kind != right_field->second.kind ||
            left_field->second.tuple_leaf != right_field->second.tuple_leaf ||
            left_field->second.shared_element_count !=
                right_field->second.shared_element_count ||
            left_field->second.concurrent_handle_kind !=
                right_field->second.concurrent_handle_kind) return false;
        if (static_cast<bool>(left_field->second.dynamic_element) !=
            static_cast<bool>(right_field->second.dynamic_element)) return false;
        if (left_field->second.dynamic_element &&
            !same_inference_layout(*left_field->second.dynamic_element,
                         *right_field->second.dynamic_element)) return false;
    }
    return true;
}
}

namespace vkf::machine_ir::detail {
std::string describe_layout(const ValueLayout& layout) {
    std::string result = std::to_string(layout.width) + "[";
    bool first = true;
    for (const auto& [name, slice] : layout.selectors) {
        if (name.find('.') != std::string::npos) continue;
        if (!first) result += ",";
        first = false;
        result += name + ":" + std::to_string(slice.width);
    }
    return result + "]";
}
}

namespace vkf::machine_ir::detail {
bool same_signature_layouts(
    const FunctionSignatures& left,
    const FunctionSignatures& right
) {
    if (left.size() != right.size()) return false;
    for (const auto& [name, signature] : left) {
        const auto found = right.find(name);
        if (found == right.end() || signature.parameters.size() != found->second.parameters.size()) {
            return false;
        }
        if (signature.parameter_full_projections !=
            found->second.parameter_full_projections) return false;
        for (std::size_t index = 0; index < signature.parameters.size(); ++index) {
            if (!same_layout(signature.parameters[index], found->second.parameters[index])) return false;
        }
        if (!same_layout(signature.result, found->second.result)) return false;
    }
    return true;
}
}

namespace vkf::machine_ir::detail {
ValueLayout record_field_layout(
    const ValueLayout& record,
    const std::string& name,
    const ValueSlice& slice
) {
    ValueLayout result{slice.width, slice.kind, {}};
    result.dynamic_element = slice.dynamic_element;
    result.shared_element_count = slice.shared_element_count;
    result.concurrent_handle_kind = slice.concurrent_handle_kind;
    result.tuple_leaf = slice.tuple_leaf;
    const std::string prefix = name + ".";
    // All descendants occupy one contiguous range in the ordered selector map.
    // Avoid scanning unrelated fields for every extracted aggregate element.
    for (auto field = record.selectors.lower_bound(prefix);
         field != record.selectors.end() && field->first.rfind(prefix, 0) == 0;
         ++field) {
        const auto& [child, nested] = *field;
        result.selectors[child.substr(prefix.size())] = {
            nested.offset - slice.offset, nested.width, nested.kind,
            nested.dynamic_element, nested.shared_element_count,
            nested.concurrent_handle_kind, nested.tuple_leaf
        };
    }
    return result;
}
}

namespace vkf::machine_ir::detail {
void assign_record_field_layout(
    ValueLayout& record,
    const std::string& name,
    const ValueLayout& field_layout
) {
    if (record.kind == ValueKind::Aggregate) {
        const auto existing = record.selectors.find(name);
        if (existing != record.selectors.end() && same_inference_layout(
                record_field_layout(record, name, existing->second), field_layout)) return;
    }
    std::vector<std::pair<std::string, ValueLayout>> fields;
    if (record.kind == ValueKind::Aggregate) {
        for (const auto& [field_name, slice] : record.selectors) {
            if (field_name.find('.') != std::string::npos) continue;
            fields.push_back({field_name, record_field_layout(record, field_name, slice)});
        }
        std::stable_sort(fields.begin(), fields.end(), [&](const auto& left, const auto& right) {
            return record.selectors.at(left.first).offset < record.selectors.at(right.first).offset;
        });
    }
    const auto existing = std::find_if(fields.begin(), fields.end(), [&](const auto& field) {
        return field.first == name;
    });
    if (existing == fields.end()) fields.push_back({name, field_layout});
    else existing->second = field_layout;
    record.width = 0;
    record.kind = ValueKind::Aggregate;
    record.selectors.clear();
    for (const auto& [field_name, layout] : fields) {
        record.selectors[field_name] = {
            record.width, layout.width, layout.kind, layout.dynamic_element,
            layout.shared_element_count, layout.concurrent_handle_kind, layout.tuple_leaf};
        for (const auto& [child, slice] : layout.selectors) {
            record.selectors[qualified_name(field_name, child)] = {
                record.width + slice.offset, slice.width, slice.kind,
                slice.dynamic_element, slice.shared_element_count,
                slice.concurrent_handle_kind, slice.tuple_leaf
            };
        }
        record.width += layout.width;
    }
}
}

namespace vkf::machine_ir::detail {
bool is_record_layout(const ValueLayout& layout) {
    return layout.kind == ValueKind::Aggregate &&
        std::any_of(layout.selectors.begin(), layout.selectors.end(), [](const auto& field) {
            if (field.first.find('.') != std::string::npos) return false;
            return field.first.empty() || !std::all_of(
                field.first.begin(), field.first.end(), [](unsigned char ch) { return std::isdigit(ch); });
        });
}
}

namespace vkf::machine_ir::detail {
bool is_plain_numeric_record_layout(const ValueLayout& layout) {
    return layout.width>0 && (is_record_layout(layout) || layout.tuple_leaf) && owned_resource_slices(layout).empty() &&
        std::all_of(layout.selectors.begin(),layout.selectors.end(),[](const auto& field){
            return field.second.kind==ValueKind::Numeric || field.second.kind==ValueKind::Complex || field.second.kind==ValueKind::Aggregate;
        });
}
}

namespace vkf::machine_ir::detail {
std::vector<StructuralLayoutMatch> resolve_structural_layout_matches(
    const ValueLayout& root,
    const std::vector<std::string>& paths
) {
    std::vector<StructuralLayoutMatch> matches;
    const auto resolve = [&](const auto& self,
                             const ValueLayout& candidate,
                             std::uint32_t base,
                             const std::vector<std::string>& components,
                             std::size_t index,
                             const std::string& identity) -> void {
        if (index == components.size()) {
            matches.push_back({base, candidate, identity});
            return;
        }
        if (candidate.kind != ValueKind::Aggregate) return;
        if (components[index] != "*") {
            const auto selected = candidate.selectors.find(components[index]);
            if (selected == candidate.selectors.end() ||
                components[index].find('.') != std::string::npos) return;
            self(
                self,
                record_field_layout(candidate, components[index], selected->second),
                base + selected->second.offset,
                components,
                index + 1,
                identity.empty() ? components[index] : identity + "." + components[index]);
            return;
        }
        std::vector<std::pair<std::string, ValueSlice>> children;
        for (const auto& [name, slice] : candidate.selectors) {
            if (name.find('.') == std::string::npos) children.push_back({name, slice});
        }
        std::stable_sort(children.begin(), children.end(), [](const auto& left, const auto& right) {
            if (left.second.offset != right.second.offset)
                return left.second.offset < right.second.offset;
            const auto numeric = [](const std::string& name) {
                return !name.empty() && std::all_of(name.begin(), name.end(),
                    [](unsigned char ch) { return std::isdigit(ch); });
            };
            const bool left_numeric = numeric(left.first), right_numeric = numeric(right.first);
            if (left_numeric && right_numeric)
                return std::stoull(left.first) < std::stoull(right.first);
            if (left_numeric != right_numeric) return left_numeric;
            return left.first < right.first;
        });
        for (const auto& [name, slice] : children) {
            self(
                self,
                record_field_layout(candidate, name, slice),
                base + slice.offset,
                components,
                index + 1,
                identity.empty() ? name : identity + "." + name);
        }
    };
    for (const auto& path : paths) {
        const auto components = split_structural_path(path);
        resolve(resolve, root, 0, components, 0, "");
    }
    std::stable_sort(matches.begin(), matches.end(), [](const auto& left, const auto& right) {
        if (left.offset != right.offset) return left.offset < right.offset;
        return left.layout.width < right.layout.width;
    });
    // Distinct logical rows may have the same physical offset when empty.
    // Only overlapping compatibility paths selecting the same node alias.
    std::set<std::string> selected_nodes;
    matches.erase(std::remove_if(matches.begin(), matches.end(), [&](const auto& match) {
        return !selected_nodes.insert(match.selector_path).second;
    }), matches.end());
    return matches;
}
}

namespace vkf::machine_ir::detail {
ValueLayout structural_result_layout(
    const ValueLayout& argument, const std::vector<std::string>& paths,
    const ValueLayout& result
) {
    const auto matches = resolve_structural_layout_matches(argument, paths);
    const auto replace = [&](const auto& self, const ValueLayout& candidate,
                             std::uint32_t offset) -> ValueLayout {
        for (const auto& match : matches) {
            if (match.offset == offset && same_layout(match.layout, candidate)) return result;
        }
        if (candidate.kind != ValueKind::Aggregate) return candidate;
        std::vector<std::pair<std::string, ValueSlice>> children;
        for (const auto& [name,slice] : candidate.selectors)
            if (name.find('.') == std::string::npos) children.push_back({name,slice});
        std::stable_sort(children.begin(),children.end(),[](const auto& a,const auto& b) {
            return a.second.offset < b.second.offset;
        });
        ValueLayout rebuilt{0,ValueKind::Aggregate,{}};
        for (const auto& [name,slice] : children)
            assign_record_field_layout(rebuilt,name,self(self,
                record_field_layout(candidate,name,slice),offset+slice.offset));
        return rebuilt;
    };
    return replace(replace,argument,0);
}
}

namespace vkf::machine_ir::detail {
std::vector<StructuralLayoutMatch> numeric_structural_layout_matches(
    const ValueLayout& root
) {
    std::vector<StructuralLayoutMatch> matches;
    const auto collect = [&](const auto& self,
                             const ValueLayout& candidate,
                             std::uint32_t base) -> void {
        if (candidate.kind == ValueKind::Numeric && candidate.width == 1) {
            matches.push_back({base, candidate});
            return;
        }
        if (candidate.kind != ValueKind::Aggregate) return;
        std::vector<std::pair<std::string, ValueSlice>> children;
        for (const auto& [name, slice] : candidate.selectors) {
            if (name.find('.') == std::string::npos) children.push_back({name, slice});
        }
        std::stable_sort(children.begin(), children.end(), [](const auto& left, const auto& right) {
            return left.second.offset < right.second.offset;
        });
        for (const auto& [name, slice] : children) {
            self(
                self,
                record_field_layout(candidate, name, slice),
                base + slice.offset);
        }
    };
    collect(collect, root, 0);
    return matches;
}
}

namespace vkf::machine_ir::detail {
namespace {
// A counted primitive vector has no fixed extent. An inline actual with the
// same element ABI cannot narrow that storage contract to its own length.
// Keep this proof separate from numeric widening and non-primitive storage.
bool preserves_counted_primitive_storage(const ValueLayout& current,
                                         const ValueLayout& candidate) {
    if (current.kind != ValueKind::DynamicF64List || current.width != 1 ||
        !current.selectors.empty() || current.tuple_leaf || current.shared_element_count != 0 ||
        current.concurrent_handle_kind != ConcurrentHandleKind::None ||
        candidate.kind != ValueKind::Aggregate || is_record_layout(candidate) ||
        candidate.tuple_leaf || candidate.dynamic_element || candidate.shared_element_count != 0 ||
        candidate.concurrent_handle_kind != ConcurrentHandleKind::None) return false;
    const auto element = current.dynamic_element ? *current.dynamic_element : ValueLayout{};
    if (!element.selectors.empty() || element.dynamic_element || element.tuple_leaf ||
        element.shared_element_count != 0 || element.concurrent_handle_kind != ConcurrentHandleKind::None ||
        !((element.kind == ValueKind::Numeric && element.width == 1) ||
          (element.kind == ValueKind::String && element.width == 2))) return false;
    const auto items = indexed_element_layouts(candidate);
    return same_inference_layout(candidate, indexed_layout(items)) &&
        std::all_of(items.begin(), items.end(), [&](const auto& item) {
            return same_inference_layout(item, element);
        });
}
}

void merge_inferred_layout(
    ValueLayout& current,
    const ValueLayout& candidate,
    bool grow_fixed_aggregates 
) {
    if (same_inference_layout(current, candidate)) return;
    if (preserves_counted_primitive_storage(current, candidate)) return;
    if(current.kind==ValueKind::Aggregate && !is_record_layout(current) && candidate.kind==ValueKind::DynamicF64List) {
        const auto compatible_vector = [&](const auto& self, const ValueLayout& fixed,
                                            const ValueLayout& counted) -> bool {
            if (counted.kind == ValueKind::DynamicF64List) {
                if (fixed.kind != ValueKind::Aggregate || is_record_layout(fixed) || fixed.tuple_leaf)
                    return false;
                const auto children = indexed_element_layouts(fixed);
                const auto element = counted.dynamic_element ? *counted.dynamic_element : ValueLayout{};
                return std::all_of(children.begin(), children.end(), [&](const auto& child) {
                    return self(self, child, element);
                });
            }
            return (fixed.kind == ValueKind::Numeric || fixed.kind == ValueKind::Complex) &&
                (counted.kind == ValueKind::Numeric || counted.kind == ValueKind::Complex) &&
                (same_layout(fixed, counted) ||
                 (fixed.kind == ValueKind::Numeric && counted.kind == ValueKind::Complex));
        };
        if(compatible_vector(compatible_vector,current,candidate)) {
            current=candidate;return;
        }
    }
    if (current.kind == ValueKind::DynamicF64List &&
        candidate.kind == ValueKind::DynamicF64List) {
        if (!current.dynamic_element) {
            current.dynamic_element = candidate.dynamic_element;
        } else if (candidate.dynamic_element) {
            // Inference snapshots share element pointers. Preserve the old
            // subtree so a nested representation change remains observable.
            auto element=std::make_shared<ValueLayout>(*current.dynamic_element);
            merge_inferred_layout(*element,*candidate.dynamic_element,grow_fixed_aggregates);
            current.dynamic_element=std::move(element);
        }
        return;
    }
    if (is_record_layout(candidate)) {
        if (!is_record_layout(current)) {
            current.width = 0;
            current.kind = ValueKind::Aggregate;
            current.selectors.clear();
        }
        std::vector<std::pair<std::string, ValueSlice>> fields;
        for (const auto& [name, slice] : candidate.selectors) {
            if (name.find('.') == std::string::npos) fields.push_back({name, slice});
        }
        std::stable_sort(fields.begin(), fields.end(), [](const auto& left, const auto& right) {
            return left.second.offset < right.second.offset;
        });
        for (const auto& [name, slice] : fields) {
            auto merged_field = record_field_layout(candidate, name, slice);
            const auto existing = current.selectors.find(name);
            if (existing != current.selectors.end()) {
                auto current_field = record_field_layout(current, name, existing->second);
                merge_inferred_layout(
                    current_field, merged_field, grow_fixed_aggregates);
                merged_field = std::move(current_field);
            }
            assign_record_field_layout(current, name, merged_field);
        }
        return;
    }
    if (current.kind == ValueKind::Aggregate && candidate.kind == ValueKind::Aggregate &&
        !is_record_layout(current) && !is_record_layout(candidate)) {
        std::vector<std::pair<std::string, ValueSlice>> current_fields;
        for (const auto& [name, slice] : current.selectors) {
            if (name.find('.') == std::string::npos) {
                current_fields.push_back({name, slice});
            }
        }
        std::stable_sort(
            current_fields.begin(), current_fields.end(),
            [](const auto& left, const auto& right) {
                return left.second.offset < right.second.offset;
            });
        const bool sparse = has_sparse_fixed_placeholder(current);
        for (const auto& [name, current_slice] : current_fields) {
            if (current_slice.kind == ValueKind::Any && current_slice.width == 0) continue;
            const auto supplied = candidate.selectors.find(name);
            if (supplied == candidate.selectors.end()) continue;
            // Earlier fields may have widened and moved this field during the
            // same pass. Snapshot offsets must not be used after reconstruction.
            const auto refreshed=current.selectors.find(name);
            if(refreshed==current.selectors.end())continue;
            auto element = record_field_layout(current, name, refreshed->second);
            const auto supplied_element = record_field_layout(
                candidate, name, supplied->second);
            if (sparse) refine_parameter_from_argument(element, supplied_element);
            else merge_inferred_layout(
                element, supplied_element, grow_fixed_aggregates);
            assign_record_field_layout(current, name, element);
        }
        if (grow_fixed_aggregates) {
            std::vector<std::pair<std::string, ValueSlice>> supplied_fields;
            for (const auto& [name, slice] : candidate.selectors) {
                if (name.find('.') == std::string::npos) {
                    supplied_fields.push_back({name, slice});
                }
            }
            std::stable_sort(
                supplied_fields.begin(), supplied_fields.end(),
                [](const auto& left, const auto& right) {
                    return left.second.offset < right.second.offset;
                });
            for (const auto& [name, supplied_slice] : supplied_fields) {
                if (current.selectors.find(name) != current.selectors.end()) continue;
                assign_record_field_layout(
                    current,
                    name,
                    record_field_layout(candidate, name, supplied_slice));
            }
        }
        return;
    }
    if (current.kind == ValueKind::Any &&
        (current.width == candidate.width ||
         (candidate.kind == ValueKind::Aggregate && candidate.width == 0 &&
          !has_sparse_fixed_placeholder(candidate)))) {
        current = candidate;
        return;
    }
    if (current.width == 1 && current.kind == ValueKind::Numeric &&
        current.selectors.empty() && candidate.kind != ValueKind::Numeric) {
        current = candidate;
        return;
    }
    if (candidate.width > current.width ||
        (candidate.width == current.width && candidate.selectors.size() > current.selectors.size())) {
        current = candidate;
    }
}
}

namespace vkf::machine_ir::detail {
ValueLayout inferred_parameter_layout(
    const vf::JsonValue::Object& function,
    const std::string& parameter,
    std::vector<std::string>* full_projections 
) {
    struct ProjectionNode {
        std::map<std::string, ProjectionNode> children;
        bool full = false;
    };
    const auto projection_path = [&](const auto& self,
                                     const vf::JsonValue::Object& expression,
                                     std::vector<std::string>& path) -> bool {
        const auto kind = expression.find("kind");
        if (kind == expression.end() || !kind->second.is_string()) return false;
        if (kind->second.as_string() == "load") {
            const auto name = expression.find("name");
            return name != expression.end() && name->second.is_string() &&
                name->second.as_string() == parameter;
        }
        if (kind->second.as_string() == "field_access") {
            const auto source = expression.find("object");
            const auto name = expression.find("field");
            if (source == expression.end() || !source->second.is_object() ||
                name == expression.end() || !name->second.is_string() ||
                !self(self, source->second.as_object(), path)) return false;
            path.push_back(name->second.as_string());
            return true;
        }
        if (kind->second.as_string() != "dotted_index") return false;
        const auto base = expression.find("base");
        const auto indices = expression.find("indices");
        if (base == expression.end() || !base->second.is_object() ||
            indices == expression.end() || !indices->second.is_array() ||
            !self(self, base->second.as_object(), path)) return false;
        for (const auto& index : indices->second.as_array()) {
            if (!index.is_object()) return false;
            const auto& index_object = index.as_object();
            const auto index_kind = index_object.find("kind");
            const auto index_value = index_object.find("value");
            if (index_kind == index_object.end() || !index_kind->second.is_string() ||
                index_kind->second.as_string() != "const" ||
                index_value == index_object.end() || !index_value->second.is_number()) return false;
            const double raw = index_value->second.as_number();
            if (raw < 0 || raw != static_cast<double>(static_cast<std::uint32_t>(raw))) return false;
            path.push_back(std::to_string(static_cast<std::uint32_t>(raw)));
        }
        return true;
    };
    ProjectionNode root;
    bool found = false;
    const auto record_projection = [&](const vf::JsonValue::Object& expression, bool full = false) {
        std::vector<std::string> path;
        if (!projection_path(projection_path, expression, path) || (path.empty() && !full)) return;
        if (full && full_projections) {
            std::string joined;
            for (const auto& component : path) {
                joined += (joined.empty() ? "" : ".") + component;
            }
            if (std::find(full_projections->begin(), full_projections->end(), joined) ==
                full_projections->end()) full_projections->push_back(std::move(joined));
        }
        found = true;
        ProjectionNode* node = &root;
        for (const auto& component : path) node = &node->children[component];
        node->full = node->full || full;
    };
    const auto collect = [&](const auto& self, const vf::JsonValue& value) -> void {
        if (value.is_array()) {
            for (const auto& item : value.as_array()) self(self, item);
            return;
        }
        if (!value.is_object()) return;
        const auto& object = value.as_object();
        const auto kind = object.find("kind");
        if (kind != object.end() && kind->second.is_string() &&
            kind->second.as_string() == "call") {
            const auto callee = object.find("callee");
            if (callee != object.end() && callee->second.is_object()) {
                const auto& callee_object = callee->second.as_object();
                const auto callee_kind = callee_object.find("kind");
                const auto callee_field = callee_object.find("field");
                const auto callee_source = callee_object.find("object");
                if (callee_kind != callee_object.end() && callee_kind->second.is_string() &&
                    callee_kind->second.as_string() == "field_access" &&
                    callee_field != callee_object.end() && callee_field->second.is_string() &&
                    callee_field->second.as_string() == "length" &&
                    callee_source != callee_object.end() && callee_source->second.is_object()) {
                    record_projection(callee_source->second.as_object(), true);
                    for (const auto& [name, child] : object) {
                        if (name != "callee") self(self, child);
                    }
                    return;
                }
            }
        }
        // A type query needs the complete nominal representation, including its
        // private identity tag. Empty paths designate the whole parameter rather
        // than a field projection and propagate through ordinary closure captures.
        if (kind != object.end() && kind->second.is_string() &&
            kind->second.as_string() == "runtime_type_of") {
            const auto queried = object.find("value");
            if (queried != object.end() && queried->second.is_object())
                record_projection(queried->second.as_object(), true);
        }
        const bool whole_load = kind != object.end() && kind->second.is_string() &&
            kind->second.as_string() == "load";
        record_projection(object, whole_load);
        std::vector<std::string> static_projection;
        const bool projected = projection_path(projection_path, object, static_projection) &&
            !static_projection.empty();
        for (const auto& [name, child] : object) {
            // A projection observes its selected path. Its base is not also a
            // whole-value demand; independent loads elsewhere still are.
            if (projected && ((kind->second.as_string() == "dotted_index" && name == "base") ||
                              (kind->second.as_string() == "field_access" && name == "object")))
                continue;
            self(self, child);
        }
    };
    collect(collect, field(function, "body", "function"));
    if (!found) return {};
    const auto numeric_name = [](const std::string& name) {
        return !name.empty() && std::all_of(name.begin(), name.end(), [](unsigned char ch) {
            return std::isdigit(ch);
        });
    };
    const auto make_layout = [&](const auto& self, const ProjectionNode& node) -> ValueLayout {
        if (node.full) return {};
        const bool indexed = !node.children.empty() &&
            std::all_of(node.children.begin(), node.children.end(), [&](const auto& child) {
                return numeric_name(child.first);
            });
        if (indexed) {
            std::uint32_t maximum = 0;
            for (const auto& [name, child] : node.children) {
                (void)child;
                maximum = std::max(
                    maximum, static_cast<std::uint32_t>(std::stoul(name)));
            }
            std::vector<ValueLayout> elements(
                maximum + 1, ValueLayout{0, ValueKind::Any, {}});
            for (const auto& [name, child] : node.children) {
                elements[static_cast<std::size_t>(std::stoul(name))] =
                    child.full || !child.children.empty() ? self(self, child) : ValueLayout{};
            }
            return indexed_layout(elements);
        }
        ValueLayout record{0, ValueKind::Aggregate, {}};
        for (const auto& [name, child] : node.children) {
            assign_record_field_layout(
                record, name,
                child.full || !child.children.empty() ? self(self, child) : ValueLayout{});
        }
        return record;
    };
    return make_layout(make_layout, root);
}
}

namespace vkf::machine_ir::detail {
void refine_full_projection_path(
    ValueLayout& current,
    const ValueLayout& candidate,
    const std::vector<std::string>& path,
    std::size_t index 
) {
    if (index == path.size()) {
        if (preserves_counted_primitive_storage(current, candidate)) return;
        // A full demand selects existing backing; it does not make an unresolved
        // caller environment an authoritative replacement for concrete storage.
        // Keep concrete substitutions (including narrower and empty values) exact.
        if (candidate.kind != ValueKind::Any) {
            // Keep the numeric ABI already required by another call when the
            // independent storage shape is unchanged. Different extents retain
            // the existing exact full-demand substitution below.
            const auto compatible_numeric_shape = [&](const auto& self,
                    const ValueLayout& left, const ValueLayout& right) -> bool {
                if (left.tuple_leaf != right.tuple_leaf ||
                    left.shared_element_count != right.shared_element_count ||
                    left.concurrent_handle_kind != right.concurrent_handle_kind) return false;
                const auto numeric = [](const ValueLayout& value) {
                    return value.selectors.empty() &&
                        ((value.kind == ValueKind::Numeric && value.width == 1) ||
                         (value.kind == ValueKind::Complex && value.width == 2));
                };
                if (numeric(left) && numeric(right)) return true;
                if (left.kind != right.kind) return false;
                if (left.kind == ValueKind::DynamicF64List) {
                    return left.dynamic_element && right.dynamic_element &&
                        self(self, *left.dynamic_element, *right.dynamic_element);
                }
                if (left.kind != ValueKind::Aggregate) return same_layout(left, right);
                if (is_record_layout(left) != is_record_layout(right)) return false;
                std::size_t left_children = 0, right_children = 0;
                for (const auto& [name, slice] : right.selectors)
                    if (name.find('.') == std::string::npos) ++right_children;
                for (const auto& [name, slice] : left.selectors) {
                    if (name.find('.') != std::string::npos) continue;
                    ++left_children;
                    const auto found = right.selectors.find(name);
                    if (found == right.selectors.end() || !self(self,
                        record_field_layout(left, name, slice),
                        record_field_layout(right, name, found->second))) return false;
                }
                return left_children == right_children;
            };
            if (compatible_numeric_shape(compatible_numeric_shape, current, candidate))
                merge_inferred_layout(current, candidate);
            else current = candidate;
        }
        return;
    }
    if (candidate.kind != ValueKind::Aggregate) return;
    const auto supplied = candidate.selectors.find(path[index]);
    if (supplied == candidate.selectors.end()) return;
    ValueLayout field_layout;
    if (current.kind == ValueKind::Aggregate) {
        const auto existing = current.selectors.find(path[index]);
        if (existing != current.selectors.end()) {
            field_layout = record_field_layout(current, path[index], existing->second);
        }
    }
    refine_full_projection_path(
        field_layout,
        record_field_layout(candidate, path[index], supplied->second),
        path,
        index + 1);
    assign_record_field_layout(current, path[index], field_layout);
}
}

namespace vkf::machine_ir::detail {
void refine_full_projection_paths(
    ValueLayout& current,
    const ValueLayout& candidate,
    const std::vector<std::string>& paths
) {
    for (const auto& path : paths) {
        refine_full_projection_path(
            current, candidate, split_structural_path(path));
    }
}
}

namespace vkf::machine_ir::detail {
void refine_signature_parameter_full_projection_paths(
    FunctionSignature& signature, std::size_t index, const ValueLayout& candidate,
    const std::vector<std::string>& paths
) {
    if (!has_counted_numeric_matrix_parameter_contract(signature, index) &&
        !has_counted_numeric_vector_parameter_contract(signature, index))
        refine_full_projection_paths(signature.parameters[index], candidate, paths);
    // Partial selectors cannot refine this anonymous counted matrix ABI.
    // Whole-argument evidence is handled independently by the wrapper above.
}
}

namespace vkf::machine_ir::detail {
void merge_full_projection_paths(
    std::vector<std::string>& current,
    const std::vector<std::string>& candidate,
    const std::string& prefix 
) {
    for (const auto& path : candidate) {
        const std::string merged = prefix.empty()
            ? path
            : prefix + (path.empty() ? "" : "." + path);
        if (std::find(current.begin(), current.end(), merged) == current.end()) {
            current.push_back(merged);
        }
    }
    std::sort(current.begin(), current.end());
}
}

namespace vkf::machine_ir::detail {
void refine_callsite_parameter_layouts(
    const vf::JsonValue& value,
    FunctionSignatures& signatures,
    bool module_scope 
) {
    if (value.is_array()) {
        for (const auto& item : value.as_array()) {
            refine_callsite_parameter_layouts(item, signatures, module_scope);
        }
        return;
    }
    if (!value.is_object()) return;
    const auto& object = value.as_object();
    const auto kind = object.find("kind");
    if (kind != object.end() && kind->second.is_string() && kind->second.as_string() == "call") {
        const auto elementwise = object.find("elementwise_math");
        const auto structural = object.find("structural_call");
        const bool is_structural = structural != object.end() &&
            structural->second.is_boolean() && structural->second.as_boolean();
        if (is_structural) {
            const auto& callee = object_of(field(object, "callee", "structural call"), "callee");
            const auto& arguments = array_of(field(object, "args", "structural call"), "call args");
            if (string_field(callee, "kind", "structural callee") == "load" &&
                arguments.size() == 1 && arguments.front().is_object()) {
                const auto target = signatures.find(string_field(callee, "name", "structural callee"));
                if (target != signatures.end() && target->second.parameters.size() == 1) {
                    const auto argument_layout = layout_from_expression_shape(
                        arguments.front().as_object(), signatures);
                    const auto matches = resolve_structural_layout_matches(
                        argument_layout, structural_paths_from_call(object));
                    if (!matches.empty()) {
                        const bool result_tracks_parameter = same_layout(
                            target->second.result, target->second.parameters.front());
                        refine_signature_parameter_from_argument(
                            target->second, 0, matches.front().layout);
                        if (result_tracks_parameter) {
                            target->second.result = target->second.parameters.front();
                        }
                    }
                }
            }
        }
        if (is_structural)
            refine_fixed_multi_structural_parameters(object, signatures,
                [&](const auto& value) { return layout_from_expression_shape(value, signatures); });
        if ((elementwise != object.end() && elementwise->second.is_boolean() &&
             elementwise->second.as_boolean()) ||
            is_structural) {
            for (const auto& [name, child] : object) {
                (void)name;
                refine_callsite_parameter_layouts(child, signatures, module_scope);
            }
            return;
        }
        const auto callee = object.find("callee");
        const auto args = object.find("args");
        if (callee != object.end() && callee->second.is_object() &&
            args != object.end() && args->second.is_array()) {
            const auto& callee_object = callee->second.as_object();
            const auto callee_kind = callee_object.find("kind");
            const auto callee_name = callee_object.find("name");
            if (callee_kind != callee_object.end() && callee_kind->second.is_string() &&
                callee_kind->second.as_string() == "load" &&
                callee_name != callee_object.end() && callee_name->second.is_string()) {
                const auto signature = signatures.find(callee_name->second.as_string());
                if (signature != signatures.end()) {
                    const auto& arguments = args->second.as_array();
                    refine_typed_variadic_positional_element(signature->second,arguments,signatures,
                        [&](const auto& argument){return layout_from_expression_shape(argument,signatures);});
                    for (std::size_t index = 0;
                         index < arguments.size() && index < signature->second.parameters.size() &&
                         (!signature->second.variadic_positional_index || index<*signature->second.variadic_positional_index);
                         ++index) {
                        if (!arguments[index].is_object() ||
                            index >= signature->second.parameter_is_any.size() ||
                            !signature->second.parameter_is_any[index]) continue;
                        const auto& argument = arguments[index].as_object();
                        const auto argument_kind = argument.find("kind");
                        if (argument_kind != argument.end() && argument_kind->second.is_string() &&
                            argument_kind->second.as_string() == "call") {
                            const auto& inner_callee = object_of(
                                field(argument, "callee", "nested call argument"), "nested call callee");
                            if (string_field(inner_callee, "kind", "nested call callee") == "load") {
                                const auto inner = signatures.find(
                                    string_field(inner_callee, "name", "nested call callee"));
                                if (inner != signatures.end() && inner->second.result_is_any) {
                                    merge_inferred_layout(
                                        inner->second.result, signature->second.parameters[index]);
                                }
                            }
                        }
                        ValueLayout candidate;
                        const auto argument_name = argument.find("name");
                        if (module_scope && argument_kind != argument.end() &&
                            argument_kind->second.is_string() &&
                            argument_kind->second.as_string() == "load" &&
                            argument_name != argument.end() && argument_name->second.is_string()) {
                            const auto module_layout = signatures.module_layouts.find(
                                argument_name->second.as_string());
                            candidate = module_layout != signatures.module_layouts.end()
                                ? module_layout->second
                                : layout_from_expression_shape(argument, signatures);
                        } else {
                            candidate = layout_from_expression_shape(argument, signatures);
                        }
                        auto& current = signature->second.parameters[index];
                        if (index < signature->second.parameter_is_declared_num.size() &&
                            signature->second.parameter_is_declared_num[index] &&
                            candidate.kind == ValueKind::Aggregate) {
                            continue;
                        }
                        if (index < signature->second.parameter_full_projections.size()) {
                            refine_signature_parameter_full_projection_paths(
                                signature->second, index, candidate,
                                signature->second.parameter_full_projections[index]);
                        }
                        refine_signature_parameter_from_argument(signature->second, index, candidate);
                        if (index < signature->second.parameter_displays.size()) {
                            const auto candidate_display = shallow_display_shape(argument);
                            if (candidate_display.kind != DisplayKind::F64) {
                                signature->second.parameter_displays[index] = candidate_display;
                            }
                        }
                    }
                    if (signature->second.variadic_named_index) {
                        auto& capture = signature->second.parameters[
                            *signature->second.variadic_named_index];
                        const auto named = object.find("named_args");
                        if (named != object.end() && named->second.is_array()) {
                            for (const auto& named_value : named->second.as_array()) {
                                const auto& named_argument = object_of(
                                    named_value, "variadic named call argument");
                                const std::string name = string_field(
                                    named_argument, "name", "variadic named call argument");
                                if (std::find(
                                        signature->second.parameter_names.begin(),
                                        signature->second.parameter_names.end(), name) !=
                                    signature->second.parameter_names.end()) {
                                    continue;
                                }
                                assign_record_field_layout(
                                    capture,
                                    name,
                                    layout_from_expression_shape(
                                        object_of(
                                            field(named_argument, "value", "variadic named argument"),
                                            "variadic named argument value"),
                                        signatures));
                                auto& capture_display = signature->second.parameter_displays[
                                    *signature->second.variadic_named_index];
                                const auto supplied_display = shallow_display_shape(object_of(
                                    field(named_argument, "value", "variadic named argument"),
                                    "variadic named argument value"));
                                const auto display_field = std::find_if(
                                    capture_display.children.begin(), capture_display.children.end(),
                                    [&](const auto& child) { return child.first == name; });
                                if (display_field == capture_display.children.end()) {
                                    capture_display.children.push_back({name, supplied_display});
                                } else {
                                    display_field->second = supplied_display;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    const bool child_module_scope = module_scope &&
        !(kind != object.end() && kind->second.is_string() &&
          kind->second.as_string() == "function");
    for (const auto& [name, child] : object) {
        (void)name;
        refine_callsite_parameter_layouts(child, signatures, child_module_scope);
    }
}
}
