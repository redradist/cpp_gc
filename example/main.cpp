#include <gc_ptr.hpp>
#include <iostream>
#include <atomic>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <deque>
#include <mutex>
#include <algorithm>
#include "some_lib.hpp"

class A;

template <typename T, typename Base>
class Df : public Base {
 public:
  T t2t;
};

class DD {
 public:
  A *a0;
};

class C {
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

  std::string getName() {
    return "class A";
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

  std::string getName() {
    return "class A";
  }

  memory::gc_ptr<B> b_ptr_;
};

class D {
 public:
  Df<A, A> fd;
  const A a0;
  A const *a1;
};

namespace asdasd {
class CC : public A {

 private:
  memory::gc_ptr<B> b_ptr_;
};
}


int main() {
  // NOTE(redra): Test 0
//  std::thread thr;
//  {
//    memory::gc_ptr<A> a0_ptr_{new A()};
//    a0_ptr_->b_ptr_->c_ptr_->a1_ptr_ = a0_ptr_;
//
//    memory::gc_ptr<A> a_copy_ptr_{};
//    a_copy_ptr_.create_object();
//    a_copy_ptr_ = a0_ptr_;
//
//    thr = std::thread {[a0_ptr_]() {
//      std::this_thread::sleep_for(std::chrono::seconds(2));
//      std::cout << "Object name is " << a0_ptr_->getName() << std::endl;
//    }};
//    memory::gc_ptr<A> a1_ptr_{};
//    a1_ptr_.create_object();
//    a1_ptr_->b_ptr_ = a0_ptr_->b_ptr_;
//    a1_ptr_->b_ptr_->c_ptr_->a0_ptr_  = a1_ptr_;
//  }

//  thr.join();

  Df<A, A> ad;
  ad.t2t;
  // NOTE(redra): Test 1
  std::thread thr;
  {
    memory::gc_ptr<A> a0_ptr_{new A()};
    a0_ptr_->b_ptr_->c_ptr_->a1_ptr_ = a0_ptr_;

    ad.t2t.b_ptr_ = a0_ptr_->b_ptr_;
    memory::gc_ptr<A> a_copy_ptr_{};
    a_copy_ptr_.create_object();
    a_copy_ptr_ = a0_ptr_;

    asdasd::CC cc;
    auto c0_ptr_ = a0_ptr_->b_ptr_->c_ptr_;
    thr = std::thread {[a0_ptr_]() {
      std::this_thread::sleep_for(std::chrono::seconds(2));
      std::cout << "Object name is " << a0_ptr_->getName() << std::endl;
      std::this_thread::sleep_for(std::chrono::seconds(2));
      a0_ptr_->b_ptr_->c_ptr_ = new C();
      std::cout << "Object name is " << a0_ptr_->getName() << std::endl;
    }};
    memory::gc_ptr<A> a1_ptr_{};
    a1_ptr_.create_object();
    a1_ptr_->b_ptr_ = a0_ptr_->b_ptr_;
    a1_ptr_->b_ptr_->c_ptr_->a0_ptr_  = a1_ptr_;
  }
  thr.join();

  // NOTE(redra): Test 2
//  memory::gc_ptr<A> a0_ptr_{new A()};
//  memory::gc_ptr<A> a1_ptr_ = a0_ptr_;
  return 0;
}
