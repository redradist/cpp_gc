//
// Created by redra on 20.10.19.
//

#ifndef NOMOREGARBADGECOLLECTOR_SOME_LIB_HPP
#define NOMOREGARBADGECOLLECTOR_SOME_LIB_HPP

#include <gc_ptr.hpp>

class CD {
 public:
  CD() {
    std::cout << "CD()" << std::endl;
  }

  ~CD() {
    std::cout << "~CD()" << std::endl;
  }

  std::string getName() {
    return "class CD";
  }

  std::string getFile() {
    return __FILE__;
  }

  std::vector<int> array;
};

#endif //NOMOREGARBADGECOLLECTOR_SOME_LIB_HPP
