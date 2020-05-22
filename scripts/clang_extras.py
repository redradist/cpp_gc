#!/usr/bin/env python3

import os
import re
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import List, Set, Dict

from clang.cindex import *
from ctypes.util import find_library

lib_path = '/usr/lib'
llvm_lib_dir_regex = re.compile(r'llvm-(?P<ver>\d+([.]?\d+)?)')

llvm_lib_vers = []
for root, dirs, files in os.walk(lib_path):
  for dir in dirs:
    match = llvm_lib_dir_regex.match(dir)
    if match:
        llvm_lib_vers.append(Decimal(match.group('ver')))

max_clang_ver = max(llvm_lib_vers)
print(f'llvm_lib_vers is {llvm_lib_vers}')
max_llvm_lib_ver = max(llvm_lib_ver for llvm_lib_ver in llvm_lib_vers if llvm_lib_ver < Decimal('8.0'))
print(f'max_llvm_lib_ver is {max_llvm_lib_ver}')

if max_llvm_lib_ver is None:
    print('LLVM Toolchain with version less than 8 is not found, please install it from https://apt.llvm.org/ or using apt-get on Ubuntu !!',
          file=sys.stderr)

Config.set_library_file(f'/usr/lib/llvm-{max_llvm_lib_ver}/lib/libclang.so.1')

import clang.cindex


def get_lexical_parents(cursor):
    parents = []
    if hasattr(cursor, 'lexical_parent'):
        parent_iter = cursor.lexical_parent
        while hasattr(parent_iter, 'kind') and \
              (parent_iter.kind == CursorKind.NAMESPACE or \
               parent_iter.kind == CursorKind.CLASS_DECL):
            parents.append((parent_iter.kind, parent_iter))
            parent_iter = parent_iter.lexical_parent
    return list(reversed(parents))


class ClassDecl:
    def __init__(self, cursor):
        self.class_decl = cursor
        spelling_type = cursor.spelling
        record_type = re.search(r'(const)?\s?(?P<type_name>[_A-Za-z][_A-Za-z0-9]*)', spelling_type)
        if record_type:
            self.class_name = record_type.group('type_name')
        else:
            self.class_name = spelling_type
        self.base_decls = ClassDecl.get_base_classes(self.class_decl)
        self.field_decl = ClassDecl.get_field_decls(self.class_decl)
        record_type = re.search(r'(const)?\s?(?P<type_name>[_A-Za-z][_A-Za-z0-9]*)', spelling_type)
        if record_type:
            self.class_name = record_type.group('type_name')
        else:
            self.class_name = spelling_type
        self.parents = get_lexical_parents(cursor)

    def __eq__(self, other):
        return self.class_name == other.class_name and self.parents == other.parents

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        hash_sum = hash(self.class_name)
        for item in self.parents:
            hash_sum ^= hash(item[0].value)
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

    @staticmethod
    def get_base_classes(class_decl):
        bases = []
        if hasattr(class_decl, 'get_children'):
            for child in class_decl.get_children():
                if child.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER:
                    bases.append(child)
        return bases

    @staticmethod
    def get_field_decls(class_decl):
        field_decls = []
        if hasattr(class_decl, 'get_children'):
            for child in class_decl.get_children():
                if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                    field_decls.append(child)
        return field_decls


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


def is_gc_trace_annotation(cursor: clang.cindex.Cursor):
    for child in cursor.get_children():
        if child.kind == CursorKind.ANNOTATE_ATTR and child.spelling == 'gc::Trace':
            return True
    return False

def get_all_classes(cursor: clang.cindex.Cursor):
    """
    Find all references to the type named 'typename'
    :param cursor: clang.cindex.Cursor
    :return: None
    """
    found_classes = set()
    if (cursor.kind == CursorKind.CLASS_DECL or cursor.kind == CursorKind.CLASS_TEMPLATE) and cursor.is_definition() and is_gc_trace_annotation(cursor):
        class_decl = ClassDecl(cursor)
        if class_decl in found_classes:
            found_classes.remove(class_decl)
        found_classes.add(class_decl)

    if hasattr(cursor, 'get_children'):
        for child in cursor.get_children():
            for cl in get_all_classes(child):
                if cl in found_classes:
                    found_classes.remove(cl)
                found_classes.add(cl)

    return found_classes

def esc(code):
    return f'\033[{code}m'

def validate_all_lambdas(cursor: clang.cindex.Cursor):
    """
        Find all references to the type named 'typename'
        :param cursor: clang.cindex.Cursor
        :return: None
        """
    if hasattr(cursor, 'get_children'):
        if cursor.kind == CursorKind.CALL_EXPR and 'std::thread' in cursor.type.spelling:
            validate_all_lambdas.parent_thread_call = True
        for child in cursor.get_children():
            if (cursor.kind == CursorKind.LAMBDA_EXPR) and ('memory::gc_ptr' in child.type.spelling):
                if not hasattr(validate_all_lambdas, 'parent_thread_call') or not validate_all_lambdas.parent_thread_call:
                    print(f"{esc('31;1;4')}error:{esc(0)} memory::gc_ptr in lambda could be used only in std::thread constructor context(file={cursor.location.file.name}:{cursor.location.line}, column={cursor.location.column})", file=sys.stderr)
                    exit(1)
            validate_all_lambdas(child)
        if cursor.kind == CursorKind.CALL_EXPR and 'std::thread' in cursor.type.spelling:
            validate_all_lambdas.parent_thread_call = False


def get_base_classes(cursor):
    bases = []
    if hasattr(cursor, 'get_children'):
        for child in cursor.get_children():
            if child.kind == clang.cindex.CursorKind.CXX_BASE_SPECIFIER:
                bases.append(child)
    return bases


def get_field_decls(cursor):
    field_decls = []
    if hasattr(cursor, 'get_children'):
        for child in cursor.get_children():
            if child.kind == clang.cindex.CursorKind.FIELD_DECL:
                field_decls.append(child)
    return field_decls


def filter_files(classes, base_path):
    project_files = []
    external_files = []
    for cl in classes:
        file_path = os.path.abspath(str(cl.class_decl.location.file))
        common_directory = os.path.commonpath([base_path, file_path])
        if base_path in common_directory:
            project_files.append(file_path)
        else:
            external_files.append(file_path)
    return project_files, external_files


def group_by_file(classes):
    group_classes: Dict = dict()
    for cl in classes:
        file_path = str(cl.class_decl.location.file)
        if file_path not in group_classes:
            group_classes[file_path] = list()
        group_classes[file_path].append(cl)
    return group_classes


def group_by_lines(classes: List[ClassDecl]):
    group_classes: Dict = dict()
    for cl in classes:
        lines = cl.lines
        if lines not in group_classes:
            group_classes[lines] = list()
        group_classes[lines].append(cl)
    return group_classes


def get_compile_file(args):
    is_next_file = False
    for arg in args:
        if arg == '-c':
            is_next_file = True
        elif is_next_file:
            return arg


def get_include_paths(args):
    include_paths = []
    for arg in args:
        if arg.startswith('-I'):
            include_paths.append(os.path.abspath(arg[len('-I'):]))
    return include_paths


def adjust_args(args):
    new_args = [arg for arg in args if arg]
    idx = 0
    should_remove = False
    while idx < len(new_args):
        if new_args[idx] == '-o' or new_args[idx] == '-c':
            del new_args[idx]
            should_remove = True
        elif should_remove:
            del new_args[idx]
        else:
            idx += 1
    return new_args


def substitute_generated_files(command, generated_file_per_real_file):
    indx = 0
    while indx < len(command):
        if command[indx] in generated_file_per_real_file:
            command[indx] = generated_file_per_real_file[command[indx]]
        indx += 1


def is_header_file(file):
    _, file_extension = os.path.splitext(file)
    return file_extension == '.h' or file_extension == '.hpp'


def get_common_path(include_paths):
    common_paths = []
    for path in include_paths:
        cpath = os.path.commonpath([path, file])
        if cpath:
            common_paths.append(cpath)
    return os.path.commonpath(common_paths)


def get_sufixes(include_paths, common_path):
    sufixes = []
    for path in include_paths:
        if path.startswith(common_path):
            sufixes.append(path[len(common_path):])
    longest_sufix = max(sufixes, key=len)
    return sufixes, longest_sufix


def generate_relative_includes(command, relative_path, sufixes):
    indx = 1
    for sufix in sufixes:
        command.insert(indx, f'-I{relative_path+sufix}')
        indx += 1


if __name__ == '__main__':
    # json_file = sys.argv[1]
    print(f'sys.argv = {sys.argv}')
    import subprocess

    command = [f"clang++-{max_clang_ver}"]
    command.extend(sys.argv[1:])

    build_directory = os.getcwd()
    args = command[1:]
    cpp_file = get_compile_file(args)
    include_paths = get_include_paths(args)

    if cpp_file is None:
        print(f'command is {command}')
        exit(subprocess.call(command))

    print(f'build_directory is {build_directory}')
    print(f'args is {args}')
    print(f'cpp_file is {cpp_file}')
    print(f'include_paths is {include_paths}')

    index = clang.cindex.Index.create()

    args = adjust_args(args)
    print(f'adjust_args is {args}')

    tu = index.parse(cpp_file,
                     args=args,
                     options=0)
    all_gc_ptrs = set()
    class_inherited_from = set()
    cached_class_used_gc_ptr = set()
    cached_class_used_class = dict()
    classes = get_all_classes(tu.cursor)
    validate_all_lambdas(tu.cursor)
    project_files, external_files = filter_files(classes, str(Path(build_directory).parent))
    grouped_by_file_classes = group_by_file(classes)

    generated_file_per_real_file = dict()
    for file, classes_per_file in grouped_by_file_classes.items():
        gc_ptr_locations_pre_class = dict()
        grouped_by_lines_classes = group_by_lines(classes_per_file)
        sorted_lines = list(sorted(grouped_by_lines_classes.keys(), key=lambda x: x[2]))
        new_lines = []
        with open(file, 'r') as f:
            lines = f.readlines()
            indx = 0
            line_iter = iter(sorted_lines)
            line = next(line_iter)
            line_offset = dict()
            while indx < len(lines):
                cur_line = lines[indx]
                if line and line[2] == indx + 1:
                    column_offset = 0
                    if line[2] in line_offset:
                        column_offset = line_offset[line[2]]

                    member_names = []
                    classes_per_line = grouped_by_lines_classes[line]
                    for cl in classes_per_line:
                        if cur_line[cl.lines[3]-2] != '}':
                            continue
                        bases = get_base_classes(cl.class_decl)
                        fields = get_field_decls(cl.class_decl)

                        connect_lines = []
                        for base in bases:
                            spelling = base.spelling
                            record_type = re.search(r'(class|struct)?\s?(?P<type_name>[_A-Za-z][_A-Za-z0-9]*)',
                                                    spelling)
                            if record_type:
                                spelling = record_type.group('type_name')
                            connect_lines.append(f"    memory::call_ConnectBaseToRoot<{spelling}>(this, rootPtr);\n")

                        for field in fields:
                            spelling = field.spelling
                            connect_lines.append(f"    memory::call_ConnectFieldToRoot<decltype({spelling})>({spelling}, rootPtr);\n")

                        disconnect_lines = []
                        for base in bases:
                            spelling = base.spelling
                            record_type = re.search(r'(class|struct)?\s?(?P<type_name>[_A-Za-z][_A-Za-z0-9]*)',
                                                    spelling)
                            if record_type:
                                spelling = record_type.group('type_name')
                            disconnect_lines.append(f"    memory::call_DisconnectBaseFromRoot<{spelling}>(this, isRoot, rootPtr);\n")

                        for field in fields:
                            spelling = field.spelling
                            disconnect_lines.append(f"    memory::call_DisconnectFieldFromRoot<decltype({spelling})>({spelling}, isRoot, rootPtr);\n")

                        if len(connect_lines) > 0 or len(disconnect_lines) > 0:
                            new_lines.append("\n")
                            new_lines.append(" public:\n")
                            new_lines.append("  // GENERATED CODE FOR GC_PTR\n")
                            new_lines.append("  // BEGIN GC_PTR\n")
                            if len(connect_lines) > 0:
                                new_lines.append("  void connectToRoot(const void * rootPtr) const {\n")
                                for connect_line in connect_lines:
                                    new_lines.append(connect_line)
                                new_lines.append("  }\n")
                                new_lines.append("\n")
                            if len(disconnect_lines) > 0:
                                new_lines.append("  void disconnectFromRoot(const bool isRoot, const void * rootPtr) const {\n")
                                for disconnect_line in disconnect_lines:
                                    new_lines.append(disconnect_line)
                                new_lines.append("  }\n")
                            new_lines.append("  // END GC_PTR\n")
                            new_lines.append(cur_line[line[3] - 2 - column_offset:])
                            try:
                                line = next(line_iter)
                            except:
                                line = None
                else:
                    new_lines.append(cur_line)
                indx += 1

        abs_file_path = os.path.abspath(file)
        if abs_file_path in project_files:
            prefix_gen_dir = '/generated/internal_src'
            common_directory = os.path.commonpath([build_directory, abs_file_path])
            start_of_file_index = abs_file_path.find(common_directory)
            second_part_of_file = abs_file_path[start_of_file_index + len(common_directory):]
            if is_header_file(abs_file_path):
                common_path = get_common_path(include_paths)
                sufixes, longest_sufix = get_sufixes(include_paths, common_path)
                gen_dir = build_directory + prefix_gen_dir
                generate_relative_includes(command, gen_dir, sufixes)
                prefix_gen_dir += longest_sufix
            generated_file = build_directory + prefix_gen_dir + second_part_of_file
        else:
            header_file_name = Path(abs_file_path).name
            prefix_gen_dir = '/generated/external_include/bits/'
            generated_file = build_directory + prefix_gen_dir + header_file_name
            if header_file_name == 'gc_ptr.hpp':
                continue

        if not os.path.exists(build_directory + prefix_gen_dir):
            os.makedirs(build_directory + prefix_gen_dir)
        generated_file_per_real_file[file] = generated_file
        with open(generated_file, 'w') as f:
            f.writelines(new_lines)

    command.insert(1, f'-I{build_directory}/generated/external_include/')
    substitute_generated_files(command, generated_file_per_real_file)
    print(f'command is {command}')
    exit(subprocess.call(command))
