set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(SCRIPT_PATH ${CMAKE_CURRENT_LIST_DIR})
function(use_gc_ptr TARGET)
    message(STATUS "TARGET is ${TARGET}")
    set(GC_PTR_GENERATOR_SCRIPT ${SCRIPT_PATH}/main.py)
    message(STATUS "GC_PTR_GENERATOR_SCRIPT is ${GC_PTR_GENERATOR_SCRIPT}")
    set(COMPILE_COMMANDS_PATH ${CMAKE_BINARY_DIR}/compile_commands.json)
    message(STATUS "COMPILE_COMMANDS_PATH is ${COMPILE_COMMANDS_PATH}")

    add_custom_target(
        ${TARGET}_gc_ptr_gen
        COMMAND python3 ${GC_PTR_GENERATOR_SCRIPT} ${COMPILE_COMMANDS_PATH}
        COMMAND echo "Generation additional code for memory::gc_ptr finished")
    add_dependencies(${TARGET} ${TARGET}_gc_ptr_gen)
endfunction(use_gc_ptr)