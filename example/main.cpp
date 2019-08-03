#include <iostream>
#include <atomic>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <deque>
#include <mutex>
#include <algorithm>
#include <gc_ptr.hpp>
#include <functional>

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

  memory::gc_ptr<A> a0_ptr_;
  memory::gc_ptr<A> a1_ptr_;
  std::vector<int> array;
};

class B {
 public:
  B() {
    std::cout << "B()" << std::endl;
    c_ptr_ = memory::gc_ptr<C>{new C()};
    c_ptr_.create_object();
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

  memory::gc_ptr<C> c_ptr_;
  std::vector<int> array;
};

class A {
 public:
  A() {
    std::cout << "A()" << std::endl;
    b_ptr_.create_object();
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

  memory::gc_ptr<B> b_ptr_;
};

int main() {
  std::thread thr;
  {
    memory::gc_ptr<A> a0_ptr_{new A()};
    a0_ptr_->b_ptr_->c_ptr_->a1_ptr_ = a0_ptr_;

    memory::gc_ptr<A> a_copy_ptr_{};
    a_copy_ptr_.create_object();
    a_copy_ptr_ = a0_ptr_;

    thr = std::thread {[a0_ptr_]() {
      std::this_thread::sleep_for(std::chrono::seconds(2));
      std::cout << "Object name is " << a0_ptr_->getName() << std::endl;
    }};
    memory::gc_ptr<A> a1_ptr_{};
    a1_ptr_.create_object();
    a1_ptr_->b_ptr_ = a0_ptr_->b_ptr_;
    a1_ptr_->b_ptr_->c_ptr_->a0_ptr_  = a1_ptr_;
  }
  thr.join();
  return 0;
}