#include <iostream>
#include <atomic>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <deque>
#include <mutex>
#include <algorithm>
#include <thread>
#include "some_lib.hpp"

//[[gc::Trace]]
class GC_TRACE ASDsdasfasd {
 public:
  int k;
};

class A;

template <typename T, typename Base>
class Derived : public Base {
 public:
  T t;
}
     ;

class ClassWithMemberPointer {
 public:
  A *a0;
};

class GC_TRACE C {
 public:
  C() {
    std::cout << "C()" << std::endl;
  }

  ~C() {
    std::cout << "~C()" << std::endl;
  }

  std::string getName() {
    return "class A";
  }

  A * a0;
  memory::gc_ptr<A> a0_ptr_;
  memory::gc_ptr<A> a1_ptr_;
  std::vector<int> array;
}; class SomeStrangeClass {
  A * a0;
};

class GC_TRACE B {
 public:
  B() {
    std::cout << "B()" << std::endl;
    c_ptr_ = memory::gc_ptr<C>{new C()};
    c_ptr_ = memory::make_gc<C>();
  }

  ~B() {
    std::cout << "~B()" << std::endl;
  }

  std::string getName() {
    return "class A";
  }

  memory::gc_ptr<C> c_ptr_;
  std::vector<int> array;
};

class GC_TRACE A {
 public:
  A() {
    std::cout << "A()" << std::endl;
    b_ptr_ = memory::make_gc<B>();
  }

  ~A() {
    std::cout << "~A()" << std::endl;
  }

  std::string getName() {
    return "class A";
  }

  memory::gc_ptr<B> b_ptr_;
};

class D {
 public:
  Derived<A, A> der0_;
  const A a0;
  A const *a1;
};

namespace strange_namespace {
class StrangeClass : public A {

 private:
  memory::gc_ptr<B> b_ptr_;
};
}

int main() {
//  memory::gc_ptr<std::vector<uint8_t>> dsasdsafsd{new std::vector<uint8_t>()};
//
  std::cout << "" << CD{}.getFile() << std::endl;

  // NOTE(redra): Test 0
  std::thread thr;
  {
    memory::gc_ptr<A> a0_ptr_{new A()};
    a0_ptr_->b_ptr_->c_ptr_->a1_ptr_ = a0_ptr_;

    memory::gc_ptr<A> a_copy_ptr_{};
    a_copy_ptr_ = memory::make_gc<A>();
    a_copy_ptr_ = a0_ptr_;

    thr = std::thread {[a0_ptr_]() {
      std::this_thread::sleep_for(std::chrono::seconds(2));
      std::cout << "Object name is " << a0_ptr_->getName() << std::endl;
    }};
    memory::gc_ptr<A> a1_ptr_{};
    a1_ptr_ = memory::make_gc<A>();
    a1_ptr_->b_ptr_ = a0_ptr_->b_ptr_;
    a1_ptr_->b_ptr_->c_ptr_->a0_ptr_  = a1_ptr_;
  }

  thr.join();


  // NOTE(redra): Test 1
//  Df<A, A> ad;
//  std::thread thr;
//  {
//    memory::gc_ptr<A> a0_ptr_{new A()};
//    a0_ptr_->b_ptr_->c_ptr_->a1_ptr_ = a0_ptr_;
//
//    ad.t2t.b_ptr_ = a0_ptr_->b_ptr_;
//    memory::gc_ptr<A> a_copy_ptr_{};
//    a_copy_ptr_.create_object();
//    a_copy_ptr_ = a0_ptr_;
//
//    asdasd::CC cc;
//    auto c0_ptr_ = a0_ptr_->b_ptr_->c_ptr_;
//    thr = std::thread {[a0_ptr_]() {
//      std::this_thread::sleep_for(std::chrono::seconds(2));
//      std::cout << "Object name is " << a0_ptr_->getName() << std::endl;
//      std::this_thread::sleep_for(std::chrono::seconds(2));
//      a0_ptr_->b_ptr_->c_ptr_ = new C();
//      std::cout << "Object name is " << a0_ptr_->getName() << std::endl;
//    }};
//    memory::gc_ptr<A> a1_ptr_{};
//    a1_ptr_.create_object();
//    a1_ptr_->b_ptr_ = a0_ptr_->b_ptr_;
//    a1_ptr_->b_ptr_->c_ptr_->a0_ptr_  = a1_ptr_;
//  }
//  thr.join();

  // NOTE(redra): Test 2
//  memory::gc_ptr<A> a0_ptr_{new A()};
//  memory::gc_ptr<A> a1_ptr_ = a0_ptr_;
  return 0;
}
