#include <iostream>
#include <atomic>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <deque>
#include <mutex>
#include <algorithm>
#include <gc_ptr.hpp>

class A;

class C {
 public:
  C() {
    std::cout << "C()" << std::endl;
  }

  ~C() {
    std::cout << "~C()" << std::endl;
  }

  void connectToRoot(void * rootPtr) {
    a0_ptr_.connectToRoot(rootPtr);
    a1_ptr_.connectToRoot(rootPtr);
  }

  void disconnectFromRoot(void * rootPtr) {
    a0_ptr_.disconnectFromRoot(rootPtr);
    a1_ptr_.disconnectFromRoot(rootPtr);
  }

  gc::memory::gc_ptr<A> a0_ptr_;
  gc::memory::gc_ptr<A> a1_ptr_;
  std::vector<int> array;
};

class B {
 public:
  B() {
    c_ptr_.create_object();
    std::cout << "B()" << std::endl;
  }

  ~B() {
    std::cout << "~B()" << std::endl;
  }

  void connectToRoot(void * rootPtr) {
    c_ptr_.connectToRoot(rootPtr);
  }

  void disconnectFromRoot(void * rootPtr) {
    c_ptr_.disconnectFromRoot(rootPtr);
  }

  gc::memory::gc_ptr<C> c_ptr_;
  std::vector<int> array;
};

class A {
 public:
  A() {
    b_ptr_.create_object();
    std::cout << "A()" << std::endl;
  }

  ~A() {
    std::cout << "~A()" << std::endl;
  }

  void connectToRoot(void * rootPtr) {
    b_ptr_.connectToRoot(rootPtr);
  }

  void disconnectFromRoot(void * rootPtr) {
    b_ptr_.disconnectFromRoot(rootPtr);
  }

  std::string getName() {
    return "class A";
  }

  gc::memory::gc_ptr<B> b_ptr_;
};

int main() {
  std::thread thr;
  {
//    root_gc_ptr<A> a0_ptr_{};
//    a0_ptr_.create_object();
    gc::memory::root_gc_ptr<A> a0_ptr_{new A()};
    a0_ptr_->b_ptr_->c_ptr_->a1_ptr_ = a0_ptr_;

    gc::memory::root_gc_ptr<A> a_copy_ptr_{};
    a_copy_ptr_.create_object();
    a_copy_ptr_ = a0_ptr_;

    thr = std::thread {
      [a_copy_ptr_]() {
        std::this_thread::sleep_for(std::chrono::seconds(10));
        std::cout << "Object name " << a_copy_ptr_->getName();
      }
    };

    gc::memory::root_gc_ptr<A> a1_ptr_{};
    a1_ptr_.create_object();
//    gc::memory::root_gc_ptr<A> a1_ptr_{new A()};
    a1_ptr_->b_ptr_ = a0_ptr_->b_ptr_;
    a1_ptr_->b_ptr_->c_ptr_->a0_ptr_  = a1_ptr_;
  }
  thr.join();
  return 0;
}
