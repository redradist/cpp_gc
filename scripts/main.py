import re
import json
import sys

from clang.cindex import *
from ctypes.util import find_library

Config.set_library_file('/usr/lib/llvm-7/lib/libclang.so.1')
# Config.set_library_file('/usr/lib/llvm-9/lib/libclang.so')

import clang.cindex


def get_lexical_parents(cursor):
    parents = []
    if hasattr(cursor, 'lexical_parent'):
        parent_iter = cursor.lexical_parent
        while parent_iter.kind == CursorKind.NAMESPACE or \
              parent_iter.kind == CursorKind.CLASS_DECL:
            parents.append((parent_iter.kind, parent_iter))
            parent_iter = parent_iter.lexical_parent
    return list(reversed(parents))


class ClassDecl:
    def __init__(self, cursor, base=None, additional_info=None):
        self.class_decl = cursor
        self.base_decl = base
        spelling_type = cursor.spelling
        record_type = re.search(r'(const)?\s?(?P<type_name>[_A-Za-z][_A-Za-z0-9]*)', spelling_type)
        if record_type:
            self.class_name = record_type.group('type_name')
        else:
            self.class_name = spelling_type
        self.parents = get_lexical_parents(cursor)
        self.additional_info = additional_info
        print(f'self')

    def __eq__(self, other):
        return self.class_name == other.class_name and self.parents == other.parents

    def __hash__(self):
        hash_sum = hash(self.class_name)
        for item in self.parents:
            hash_sum ^= hash(item[1].spelling)
        return hash_sum

    def __repr__(self):
        text = f"class file={self.class_decl.location.file}, line=({self.class_decl.extent.start.line}:{self.class_decl.extent.start.column}, {self.class_decl.extent.end.line}:{self.class_decl.extent.end.column});"
        return text

    @property
    def file(self):
        return self.class_decl.location.file

    @property
    def lines(self):
        return (self.class_decl.extent.start.line,
                self.class_decl.extent.start.column,
                self.class_decl.extent.end.line,
                self.class_decl.extent.end.column)

    def __hash__(self):
        return hash(self.class_name)

    def __eq__(self, other):
        return self.class_name.__eq__(other.class_name)


class MemberClassUsedGCPtrClassDecl:
    def __init__(self, cursor, class_used_class_used_gc_ptr, class_used_gc_ptr):
        self.member_name = cursor.spelling
        self.class_used_class_used_gc_ptr = class_used_class_used_gc_ptr
        self.class_used_gc_ptr = class_used_gc_ptr
        self.parents = get_lexical_parents(cursor)

    def __eq__(self, other):
        return self.member_name == other.member_name and self.parents == other.parents

    def __hash__(self):
        hash_sum = hash(self.member_name)
        for item in self.parents:
            hash_sum ^= hash(item[1].spelling)
        return hash_sum

    def __repr__(self):
        text = ''
        for item in self.parents:
            if item[0] == CursorKind.NAMESPACE:
                text += f"namespace file={item[1].location.file}, line=({item[1].extent.start.line}:{item[1].extent.start.column}, {item[1].extent.end.line}:{item[1].extent.end.column});"
            elif item[0] == CursorKind.CLASS_DECL:
                text += f"class file={item[1].location.file}, line=({item[1].extent.start.line}:{item[1].extent.start.column}, {item[1].extent.end.line}:{item[1].extent.end.column});"
        return text

    @property
    def file(self):
        return self.class_used_gc_ptr.file

    @property
    def lines(self):
        return self.class_used_gc_ptr.lines


class GCPtrMemberClassDecl:
    def __init__(self, cursor):
        self.member_name = cursor.spelling
        self.parents = get_lexical_parents(cursor)

    def __eq__(self, other):
        return self.member_name == other.member_name and self.parents == other.parents

    def __hash__(self):
        hash_sum = hash(self.member_name)
        for item in self.parents:
            hash_sum ^= hash(item[1].spelling)
        return hash_sum

    def __repr__(self):
        text = ''
        for item in self.parents:
            if item[0] == CursorKind.NAMESPACE:
                text += f"namespace file={item[1].location.file}, line=({item[1].extent.start.line}:{item[1].extent.start.column}, {item[1].extent.end.line}:{item[1].extent.end.column});"
            elif item[0] == CursorKind.CLASS_DECL:
                text += f"class file={item[1].location.file}, line=({item[1].extent.start.line}:{item[1].extent.start.column}, {item[1].extent.end.line}:{item[1].extent.end.column});"
        return text

    @property
    def file(self):
        if len(self.parents) > 0:
            return self.parents[-1][1].location.file

    @property
    def lines(self):
        if len(self.parents) > 0:
            return (self.parents[-1][1].extent.start.line,
                    self.parents[-1][1].extent.start.column,
                    self.parents[-1][1].extent.end.line,
                    self.parents[-1][1].extent.end.column)

is_template_class = 0

def search_item_with(cursor: clang.cindex.Cursor, name):
    type = cursor.type
    cursor_type_spelling = type.spelling
    cursor_spelling = cursor.spelling
    if cursor_spelling == name:
        print(f'Found {name} item, repr(type): {repr(type)}')
        print(f'Found {name} item, cursor_type_spelling: {cursor_type_spelling}')
        print(f'Found {name} item, cursor_spelling: {cursor_spelling}')
        print(f'Found {name} item, repr(cursor): {repr(cursor)}')
        print(f'Found {name} item, str(cursor): {str(cursor)}')
        print(f'Found {name} item, dir(cursor): {dir(cursor)}')
        return True
    elif hasattr(cursor, 'get_children'):
        for child in cursor.get_children():
            is_found = search_item_with(child, name)
            if is_found:
                print('>>>>>>>>>>>>>>>>')
                print(f'Found in {name} item, repr(type): {repr(type)}')
                print(f'Found in {name} item, cursor_type_spelling: {cursor_type_spelling}')
                print(f'Found in {name} item, cursor_spelling: {cursor_spelling}')
                print(f'Found in {name} item, repr(cursor): {repr(cursor)}')
                print(f'Found in {name} item, str(cursor): {str(cursor)}')
                print(f'Found in {name} item, dir(cursor): {dir(cursor)}')
                print('<<<<<<<<<<<<<<<<')
                return True
    return False


def find_all_use_gc_ptr(cursor: clang.cindex.Cursor, all_gc_ptrs, class_inherited_from, cached_class_used_gc_ptr, cached_class_used_class):
    """
    Find all references to the type named 'typename'
    :param cursor: clang.cindex.Cursor
    :return: None
    """
    global is_template_class

    type = cursor.type
    spelling_type = type.spelling
    if cursor.kind.is_declaration():
        type = cursor.type
        cursor_type_spelling = type.spelling
        cursor_spelling = cursor.spelling
        if spelling_type == 'Df<A>':
            print(f'Template Declaration Instance is {dir(cursor)}')
            children = cursor.get_children()
            is_template_class += 1
            for child in cursor.get_children():
                print(f'child is {repr(child)}')
                find_all_use_gc_ptr(child,
                                    all_gc_ptrs,
                                    class_inherited_from,
                                    cached_class_used_gc_ptr,
                                    cached_class_used_class)
            is_template_class -= 1
        if cursor_spelling == 'Df' and cursor.kind == CursorKind.CLASS_TEMPLATE:
            print(f'Template Declaration is {dir(cursor)}')
            is_template_class += 1
            for child in cursor.get_children():
                child_type = child.type
                child_cursor_type_spelling = child_type.spelling
                child_cursor_spelling = child.spelling
                child_kind_cursor = child.kind
                print(f'Template Child is {str(child)}')
                print(f'Template Child Dir is {dir(child)}')
                if child_cursor_spelling == 't2t':
                    print('Found t2t')
            # for child in cursor.get_children():
            #     print(f'child is {repr(child)}')
            #     find_all_use_gc_ptr(child,
            #                         all_gc_ptrs,
            #                         class_inherited_from,
            #                         cached_class_used_gc_ptr,
            #                         cached_class_used_class)
            is_template_class -= 1
        elif cursor.kind == CursorKind.NAMESPACE:
            for child in cursor.get_children():
                find_all_use_gc_ptr(child,
                                    all_gc_ptrs,
                                    class_inherited_from,
                                    cached_class_used_gc_ptr,
                                    cached_class_used_class)
        elif cursor.kind == CursorKind.CLASS_DECL:
            spelling_type = cursor.type.spelling
            if spelling_type == 'CC':
                print("Found class CC")
            bases = get_base_classes(cursor)
            for base in bases:
                if ClassDecl(base) in cached_class_used_gc_ptr:
                    cached_class_used_gc_ptr.add(ClassDecl(cursor, base))
                    class_inherited_from.add(ClassDecl(cursor, base))
                    break
            for child in cursor.get_children():
                find_all_use_gc_ptr(child,
                                    all_gc_ptrs,
                                    class_inherited_from,
                                    cached_class_used_gc_ptr,
                                    cached_class_used_class)
        elif cursor.kind == CursorKind.FIELD_DECL:
            is_gc_ptr = re.search(r'memory::gc_ptr', spelling_type)
            if is_gc_ptr:
                if cursor.lexical_parent is not None:
                    cached_class_used_gc_ptr.add(ClassDecl(cursor.lexical_parent))
                all_gc_ptrs.add(GCPtrMemberClassDecl(cursor))
            elif type.kind == TypeKind.RECORD:
                class_used_gc_ptr = ClassDecl(cursor.type)
                if class_used_gc_ptr in cached_class_used_gc_ptr:
                    all_gc_ptrs.add(GCPtrMemberClassDecl(cursor))
    else:
        for child in cursor.get_children():
            find_all_use_gc_ptr(child,
                                all_gc_ptrs,
                                class_inherited_from,
                                cached_class_used_gc_ptr,
                                cached_class_used_class)


def get_base_classes(cursor):
    bases = []
    if cursor.kind == CursorKind.CLASS_DECL:
        for node in cursor.get_children():
            if node.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER:
                bases.append(node.referenced)
        if len(bases) > 0:
            print("Found bases:")
            for base in bases:
                print(f"Base {base.type.spelling}")
    return bases


# public:
#  // GENERATED CODE FOR GC_PTR
#  // BEGIN GC_PTR
#  void connectToRoot(const void * rootPtr) const {
#    if constexpr (!std::is_pointer<decltype(t2t)>::value &&
#                  !std::is_reference<decltype(t2t)>::value &&
#                  memory::has_use_gc_ptr<decltype(t2t)>::value) {
#      t2t.connectToRoot(rootPtr);
#    }
#  }
#
#  void disconnectFromRoot(const bool isRoot, const void * rootPtr) const {
#    if constexpr (!std::is_pointer<decltype(t2t)>::value &&
#                  !std::is_reference<decltype(t2t)>::value &&
#                  memory::has_use_gc_ptr<decltype(t2t)>::value) {
#      t2t.disconnectFromRoot(isRoot, rootPtr);
#    }
#  }
#  // END GC_PTR


if __name__ == '__main__':
    # json_file = sys.argv[1]
    # print(json_file)
    json_file = '/home/redra/Projects/DeterministicGarbagePointer/example/cmake-build-debug/compile_commands.json'
    with open(json_file, "r") as jsf:
        objects = json.load(jsf)

        for obj in objects:
            index = clang.cindex.Index.create()
            cpp_file = obj['file']
            args = obj['command'].split(' ')
            del args[0]
            args = [arg for arg in args if arg]
            idx = 0
            should_remove = False
            while idx < len(args):
                if args[idx] == '-o' or args[idx] == '-c':
                    del args[idx]
                    should_remove = True
                elif should_remove:
                    del args[idx]
                else:
                    idx += 1
            tu = index.parse(cpp_file,
                             args=args,
                             options=0)
            print('Translation unit: {}'.format(tu.spelling))
            all_gc_ptrs = set()
            class_inherited_from = set()
            cached_class_used_gc_ptr = set()
            cached_class_used_class = dict()
            # search_item_with(tu.cursor, 't2t')
            find_all_use_gc_ptr(tu.cursor, all_gc_ptrs, class_inherited_from, cached_class_used_gc_ptr, cached_class_used_class)
            cached_class_used_class_used_gc_ptr = dict()
            for cl in cached_class_used_gc_ptr:
                if cl.class_name in cached_class_used_class:
                    classes_used_class_used_gc_ptr = cached_class_used_class[cl.class_name]
                    for class_used_class_used_gc_ptr in classes_used_class_used_gc_ptr:
                        all_gc_ptrs.add(MemberClassUsedGCPtrClassDecl(class_used_class_used_gc_ptr.additional_info, class_used_class_used_gc_ptr, cl))
            print(f'results is {all_gc_ptrs}')
            for res in all_gc_ptrs:
                print(f'res.file is {res.file}')
                print(f'res.lines is {res.lines}')
            gc_ptr_locations = dict()
            for res in all_gc_ptrs:
                if str(res.file) not in gc_ptr_locations:
                    gc_ptr_locations[str(res.file)] = set()
                gc_ptr_locations[str(res.file)].add(res)
            for res in class_inherited_from:
                if str(res.file) not in gc_ptr_locations:
                    gc_ptr_locations[str(res.file)] = set()
                gc_ptr_locations[str(res.file)].add(res)
            for file, gc_ptr_objs in gc_ptr_locations.items():
                print(f'file={file}')
                print(f'len(gc_ptr_objs)={len(gc_ptr_objs)}')
                gc_ptr_locations_pre_class = dict()
                sorted_lines = list()
                for obj in gc_ptr_objs:
                    if obj.lines not in gc_ptr_locations_pre_class:
                        gc_ptr_locations_pre_class[obj.lines] = set()
                        sorted_lines.append(obj.lines)
                    gc_ptr_locations_pre_class[obj.lines].add(obj)

                sorted_lines = list(sorted(sorted_lines, key=lambda x: x[2]))
                print(f'sorted_lines is {sorted_lines}')
                lines = []
                new_lines = []
                with open(file, 'r') as f:
                    lines = f.readlines()
                    indx = 0
                    line_iter = iter(sorted_lines)
                    line = next(line_iter)
                    is_generated = False
                    line_offset = dict()
                    while indx < len(lines):
                        cur_line = lines[indx]
                        # if not is_generated and '// GENERATED CODE FOR GC_PTR' in cur_line:
                        #     is_generated = True
                        if line and line[2] == indx+1:
                            column_offset = 0
                            if line[2] in line_offset:
                                column_offset = line_offset[line[2]]
                            if is_generated:
                                new_lines.append(cur_line)
                            else:
                                member_names = []
                                for gc_ptr in gc_ptr_locations_pre_class[line]:
                                    if hasattr(gc_ptr, 'member_name'):
                                        member_names.append(gc_ptr.member_name)
                                base_class_names = []
                                for gc_ptr in gc_ptr_locations_pre_class[line]:
                                    if hasattr(gc_ptr, 'base_decl') and gc_ptr.base_decl is not None:
                                        base_class_names.append(gc_ptr.base_decl.spelling)
                                class_used_class_used_gc_ptr = dict()
                                for gc_ptr in gc_ptr_locations_pre_class[line]:
                                    if hasattr(gc_ptr, 'class_used_class_used_gc_ptr'):
                                        if gc_ptr.class_used_class_used_gc_ptr not in class_used_class_used_gc_ptr:
                                            class_used_class_used_gc_ptr[gc_ptr.class_used_class_used_gc_ptr] = list()
                                        class_used_class_used_gc_ptr[gc_ptr.class_used_class_used_gc_ptr].append(gc_ptr)
                                new_lines.append(cur_line[:line[3]-2-column_offset])
                                if line[2] in line_offset:
                                    line_offset[line[2]] = line_offset[line[2]] + new_lines[-1]
                                else:
                                    line_offset[line[2]] = new_lines[-1]
                                old_len = len(new_lines)
                                connect_lines = []
                                disconnect_lines = []
                                for base_class in base_class_names:
                                    connect_lines.append(f'    {base_class}::connectToRoot(rootPtr);\n')
                                    disconnect_lines.append(f'    {base_class}::disconnectFromRoot(isRoot, rootPtr);\n')
                                for member_name in member_names:
                                    connect_lines.append(f'    {member_name}.connectToRoot(rootPtr);\n')
                                    disconnect_lines.append(f'    {member_name}.disconnectFromRoot(isRoot, rootPtr);\n')
                                new_lines.append("\n")
                                new_lines.append(" public:\n")
                                new_lines.append("  // GENERATED CODE FOR GC_PTR\n")
                                new_lines.append("  // BEGIN GC_PTR\n")
                                new_lines.append("  void connectToRoot(const void * rootPtr) const {\n")
                                for connect_line in connect_lines:
                                    new_lines.append(connect_line)
                                new_lines.append("  }\n")
                                new_lines.append("\n")
                                new_lines.append("  void disconnectFromRoot(const bool isRoot, const void * rootPtr) const {\n")
                                for disconnect_line in disconnect_lines:
                                    new_lines.append(disconnect_line)
                                new_lines.append("  }\n")
                                new_lines.append("  // END GC_PTR\n")
                                new_lines.append(cur_line[line[3]-2-column_offset:])
                                try:
                                    line = next(line_iter)
                                except:
                                    line = None
                            is_generated = False
                        else:
                            new_lines.append(cur_line)
                        indx += 1
                with open(file, 'w') as f:
                    f.writelines(new_lines)
