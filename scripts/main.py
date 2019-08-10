import re
import json
import sys
from pprint import pprint
from typing import List, Set

from clang.cindex import *

from ctypes.util import find_library

Config.set_library_file('/usr/lib/llvm-7/lib/libclang.so.1')
# Config.set_library_file('/usr/lib/llvm-9/lib/libclang.so')

code_to_analyze_0 = '''
// -------------------------------------------------------------------------------------------------
//
// Copyright (C) 2017, HERE Global B.V.
//
// These coded instructions, statements, and computer programs contain
// unpublished proprietary information of HERE Global B.V., and are copy
// protected by law. They may not be disclosed to third parties or copied
// or duplicated in any form, in whole or in part, without the specific,
// prior written permission of HERE Global B.V.
//
// -------------------------------------------------------------------------------------------------
//
// Maintainer: Traffic Team
//
// Description: Conversions between AlertC and TPEG values.
//
// -------------------------------------------------------------------------------------------------

#include <tmc/AlertC2Tpeg.h>
#include <tmc/TMCDataTypes.h>

namespace smart5
{
namespace traffic
{
namespace
{
// Mapping table used for reverse mapping of TMC event code to corresponding TEC-attributes
#include <tmc/TMCTable2TEC.inc>
}

const Tmc2Tec*
get_tec_info_from_tmc_code( uint16 event_code )
{
    if ( event_code < MIN_INCIDENT_EVENT_CODE || event_code >= G_COUNTOF( tmc2tec ) )
    {
        return nullptr;
    }

    const Tmc2Tec* to_tec = &tmc2tec[ event_code ];
    if ( to_tec->effect_code == 0 && to_tec->main_cause == 0 && to_tec->sub_cause == 0
         && to_tec->lane_restriction == 0 && to_tec->advice_code == 0
         && to_tec->vehicle_restriction == 0 )
    {
        return nullptr;
    }

    return to_tec;
}
}
}

'''

code_to_analyze_1 = '''
namespace MyNamespace {
template<typename T>
struct Person;
}

class Room {
public:
    void add_person(MyNamespace::Person<int> person)
    {
        // do stuff
    }

private:
    MyNamespace::Person<int>* people_in_room;
};


template <class T, int N>
class Bag<T, N> {
};


int main()
{
    MyNamespace::Person<int>* p = new MyNamespace::Person<int>();
    Bag<MyNamespace::Person<int>, 42> bagofpersons;

    return 0;
}
'''

code_to_analyze_2 = '''
namespace memory {

template<typename>
class gc_ptr {

};

};

class B {

};

using namespace memory;

namespace custom {

class S {
class A {
 public:
  A() {
    //b_ptr_.create_object();
  }

  ~A() {
  }

  void connectToRoot(void * rootPtr) {
    //b_ptr_.connectToRoot(rootPtr);
  }

  void disconnectFromRoot(void * rootPtr) {
    //b_ptr_.disconnectFromRoot(rootPtr);
  }

  std::string getName() {
    return "class A";
  }

  memory::gc_ptr<B> b_ptr_;
};
};
};
'''

import clang.cindex


class TypeDecl:
    def __init__(self, cursor):
        self.var_name = cursor.spelling
        self.parents = []
        parent_iter = cursor.lexical_parent
        while parent_iter.kind == CursorKind.NAMESPACE or parent_iter.kind == CursorKind.CLASS_DECL:
            self.parents.append((parent_iter.kind, parent_iter))
            parent_iter = parent_iter.lexical_parent
        self.parents = list(reversed(self.parents))

    def __eq__(self, other):
        return self.var_name == other.var_name and self.parents == other.parents

    def __hash__(self):
        hash_sum = hash(self.var_name)
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


class GCPtrTypeDecl:
    def __init__(self, cursor):
        self.var_name = cursor.spelling
        self.parents = []
        parent_iter = cursor.lexical_parent
        while parent_iter.kind == CursorKind.NAMESPACE or parent_iter.kind == CursorKind.CLASS_DECL:
            self.parents.append((parent_iter.kind, parent_iter))
            parent_iter = parent_iter.lexical_parent
        self.parents = list(reversed(self.parents))

    def __eq__(self, other):
        return self.var_name == other.var_name and self.parents == other.parents

    def __hash__(self):
        hash_sum = hash(self.var_name)
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


def find_all_gc_ptr(cursor: clang.cindex.Cursor, results, cached_types):
    """
    Find all references to the type named 'typename'
    :param cursor: clang.cindex.Cursor
    :return: None
    """
    pprint('cursor is {}'.format(cursor))
    pprint(repr(cursor))
    if cursor.kind.is_declaration():
        if cursor.kind == CursorKind.FIELD_DECL:
            spelling_type = cursor.type.spelling
            is_gc_ptr = re.search(r'memory::gc_ptr', spelling_type)
            if is_gc_ptr:
                print('CursorKind FIELD_DECL: {} ({}) [line={}, col={}]'.format(cursor.spelling,
                                                                                cursor.displayname,
                                                                                cursor.location.line,
                                                                                cursor.location.column))
                results.add(GCPtrTypeDecl(cursor))
                return
            # else:
            #     results.add(TypeDecl(cursor))
            #     return
        else:
            def_node = cursor.get_definition()
            print('Declared Node: {} ({}) [line={}, col={}]'.format(cursor.spelling,
                                                                    cursor.displayname,
                                                                    cursor.location.line,
                                                                    cursor.location.column))
            if def_node and hasattr(def_node, 'kind') and (def_node.kind == CursorKind.NAMESPACE or def_node.kind == CursorKind.CLASS_DECL):
                print('def_node is {}'.format(str(def_node)))
                print('def_node.type is {}'.format(str(def_node.type.kind)))
                for child in def_node.get_children():
                    print('Element has child')
                    find_all_gc_ptr(child, results, cached_types)

    for child in cursor.get_children():
        find_all_gc_ptr(child, results, cached_types)


if __name__ == '__main__':
    json_file = sys.argv[1]
    print(json_file)
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
            results = set()
            find_all_gc_ptr(tu.cursor, results, dict())
            print(f'results is {results}')
            for res in results:
                print(f'res.file is {res.file}')
                print(f'res.lines is {res.lines}')
            gc_ptr_locations = dict()
            for res in results:
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
                        if not is_generated and '// GENERATED CODE FOR GC_PTR' in cur_line:
                            is_generated = True
                        if line and line[2] == indx+1:
                            column_offset = 0
                            if line[2] in line_offset:
                                column_offset = line_offset[line[2]]
                            if is_generated:
                                new_lines.append(cur_line)
                            else:
                                var_names = [gc_ptr.var_name for gc_ptr in gc_ptr_locations_pre_class[line]]
                                new_lines.append(cur_line[:line[3]-2-column_offset])
                                if line[2] in line_offset:
                                    line_offset[line[2]] = line_offset[line[2]] + new_lines[-1]
                                else:
                                    line_offset[line[2]] = new_lines[-1]
                                old_len = len(new_lines)
                                connect_lines = []
                                disconnect_lines = []
                                for car_name in var_names:
                                    connect_lines.append(f'    {car_name}.connectToRoot(rootPtr);\n')
                                    disconnect_lines.append(f'    {car_name}.disconnectFromRoot(isRoot, rootPtr);\n')
                                new_lines.append("\n")
                                new_lines.append(" protected:\n")
                                new_lines.append("  // GENERATED CODE FOR GC_PTR\n")
                                new_lines.append("  template <typename T>\n")
                                new_lines.append("  friend class memory::has_use_gc_ptr;\n")
                                new_lines.append("  template <typename T>\n")
                                new_lines.append("  friend class memory::gc_ptr;\n")
                                new_lines.append("\n")
                                new_lines.append("  void connectToRoot(void * rootPtr) {\n")
                                for connect_line in connect_lines:
                                    new_lines.append(connect_line)
                                new_lines.append("  }\n")
                                new_lines.append("\n")
                                new_lines.append("  void disconnectFromRoot(bool isRoot, void * rootPtr) {\n")
                                for disconnect_line in disconnect_lines:
                                    new_lines.append(disconnect_line)
                                new_lines.append("  }\n")
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
